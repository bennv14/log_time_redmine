let appState = {
    memberName: "",
    role: "",
    effortSum: 0,
    tasks: [],
    dates: getCurrentMonthDates()
};

function getCurrentMonthDates() {
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = today.getMonth();
    const daysInMonth = new Date(yyyy, mm + 1, 0).getDate();
    const dates = [];
    for (let d = 1; d <= daysInMonth; d++) {
        const dd = String(d).padStart(2, '0');
        const mmStr = String(mm + 1).padStart(2, '0');
        dates.push(`${yyyy}-${mmStr}-${dd}`);
    }
    return dates;
}

let _pendingEditIndex = null;
let _lastDeletedTask = null;
let _undoDeleteTimer = null;

const DEFAULT_ACTIVITY_ID = 9;

/** @type {Array<{entry_id: string, issue_id: string, spent_on: string, hours: number, activity_id: number, taskName: string, status: string, error: string|null, httpStatus: number|null}>} */
let syncResultRows = [];
/** @type {Array<{entry_id: string, issue_id: string, spent_on: string, hours: number, status: string, detail: string, requested_at: string}>} */
let requestHistoryRows = [];
let _syncInProgress = false;
let _dragCounter = 0;

function getSyncStats(rows = syncResultRows) {
    let pending = 0;
    let ok = 0;
    let error = 0;
    rows.forEach((row) => {
        if (row.status === 'pending') pending += 1;
        else if (row.status === 'ok') ok += 1;
        else if (row.status === 'error') error += 1;
    });
    return { total: rows.length, pending, ok, error };
}

function updateSyncResultsSummary() {
    const badge = document.getElementById('sync-compact-badge');
    if (!badge) return;
    if (syncResultRows.length === 0) {
        badge.hidden = true;
        badge.innerHTML = '';
        badge.className = '';
        return;
    }
    const stats = getSyncStats();
    const done = stats.pending === 0;
    const ok = stats.error === 0 && stats.total > 0;
    badge.hidden = !done;
    if (!done) return;
    badge.className = `badge ${ok ? 'text-bg-success' : 'text-bg-warning'}`;
    badge.innerHTML = ok
        ? `${getStatusIconSvg('ok')} ${stats.ok}/${stats.total}`
        : `${getStatusIconSvg('warn')} ${stats.ok}/${stats.total} (có lỗi)`;
}

function getStatusIconSvg(type) {
    if (type === 'ok') {
        return '<svg class="status-inline-icon" viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path d="M13.485 1.929a.75.75 0 0 1 .086 1.057l-7.2 8.5a.75.75 0 0 1-1.098.04L2.4 8.654a.75.75 0 1 1 1.06-1.06l2.295 2.295 6.673-7.873a.75.75 0 0 1 1.057-.087Z" fill="currentColor"/></svg>';
    }
    return '<svg class="status-inline-icon" viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path d="M7.25 4a.75.75 0 0 1 1.5 0v4a.75.75 0 0 1-1.5 0V4Zm.75 8.5a1 1 0 1 0 0-2 1 1 0 0 0 0 2Zm.67-11.69 5.86 10.25A1.5 1.5 0 0 1 13.23 13H2.77a1.5 1.5 0 0 1-1.3-2.19L7.33.81a1.5 1.5 0 0 1 2.34 0Z" fill="currentColor"/></svg>';
}

function addRequestHistoryRows(entries) {
    const requestedAt = new Date().toLocaleString('vi-VN');
    entries.forEach((entry) => {
        requestHistoryRows.push({
            entry_id: entry.entry_id,
            issue_id: entry.issue_id,
            spent_on: entry.spent_on,
            hours: entry.hours,
            status: 'pending',
            detail: 'Đang gửi...',
            requested_at: requestedAt
        });
    });
    renderRequestHistory();
}

function updateRequestHistoryRow(entryId, status, detail) {
    for (let i = requestHistoryRows.length - 1; i >= 0; i--) {
        const row = requestHistoryRows[i];
        if (row.entry_id === entryId && row.status === 'pending') {
            row.status = status;
            row.detail = detail || (status === 'ok' ? 'Thành công' : 'Có lỗi');
            break;
        }
    }
    renderRequestHistory();
}

function renderRequestHistory() {
    const tbody = document.getElementById('request-history-body');
    const countEl = document.getElementById('request-history-count');
    if (!tbody || !countEl) return;
    countEl.textContent = String(requestHistoryRows.length);
    if (requestHistoryRows.length === 0) {
        tbody.innerHTML = '<tr id="request-history-empty-row"><td colspan="6" class="text-center text-muted py-4">Chưa có request nào được gửi.</td></tr>';
        return;
    }
    tbody.innerHTML = '';
    requestHistoryRows.slice().reverse().forEach((row) => {
        const tr = document.createElement('tr');
        let statusHtml = '';
        if (row.status === 'pending') {
            statusHtml = '<span class="badge text-bg-secondary"><span class="spinner-border spinner-border-sm me-1" style="width:0.65rem;height:0.65rem;"></span>Đang gửi</span>';
        } else if (row.status === 'ok') {
            statusHtml = '<span class="badge text-bg-success">Thành công</span>';
        } else {
            statusHtml = '<span class="badge text-bg-danger">Thất bại</span>';
        }
        tr.innerHTML = `
            <td class="text-nowrap">${escapeHtml(row.requested_at)}</td>
            <td class="text-nowrap">${escapeHtml(String(row.issue_id))}</td>
            <td class="text-nowrap">${escapeHtml(row.spent_on)}</td>
            <td class="text-end">${Number(row.hours).toFixed(2)}</td>
            <td>${statusHtml}</td>
            <td class="small text-break" style="max-width: 18rem;">${escapeHtml(row.detail || '—')}</td>
        `;
        tbody.appendChild(tr);
    });
}

function updateSummaryMetrics() {
    const entriesEl = document.getElementById('sync-entries-count');
    const missingEl = document.getElementById('summary-missing-issue');
    if (!entriesEl || !missingEl) return;
    const syncEntries = collectSyncEntries();
    const missingIssueCount = appState.tasks.filter((task) => !String(task.taskId || '').trim()).length;
    entriesEl.innerText = String(syncEntries.length);
    missingEl.innerText = String(missingIssueCount);
}

function setSyncOverlayVisible(isVisible) {
    const overlay = document.getElementById('sync-overlay');
    if (!overlay) return;
    overlay.classList.toggle('show', isVisible);
    overlay.setAttribute('aria-hidden', isVisible ? 'false' : 'true');
    if (!isVisible) {
        setSyncOverlayPhase('loading');
    }
}

function setRequestHistoryOverlayVisible(isVisible) {
    const overlay = document.getElementById('request-history-overlay');
    if (!overlay) return;
    overlay.classList.toggle('show', isVisible);
    overlay.setAttribute('aria-hidden', isVisible ? 'false' : 'true');
}

/**
 * @param {'loading' | 'done'} phase
 * @param {{ hasError?: boolean }} [opts]
 */
function setSyncOverlayPhase(phase, opts) {
    const spinner = document.getElementById('sync-overlay-spinner');
    const textEl = document.getElementById('sync-overlay-text');
    const btnClose = document.getElementById('btn-sync-overlay-close');
    const actions = document.getElementById('sync-overlay-actions');
    const btnRetry = document.getElementById('btn-sync-overlay-retry-failed');
    if (!textEl) return;
    if (phase === 'loading') {
        if (spinner) {
            spinner.hidden = false;
        }
        textEl.textContent = 'Đang đồng bộ dữ liệu...';
        if (btnClose) {
            btnClose.disabled = true;
        }
        if (actions) actions.hidden = true;
        if (btnRetry) btnRetry.disabled = true;
        return;
    }
    if (spinner) {
        spinner.hidden = true;
    }
    const stats = getSyncStats();
    const summary = `Thành công ${stats.ok}/${stats.total}`;
    textEl.textContent = opts && opts.hasError
        ? `${summary}. Có lỗi.`
        : `${summary}. Hoàn tất.`;
    if (btnClose) {
        btnClose.disabled = false;
    }
    if (actions) actions.hidden = false;
    if (btnRetry) {
        btnRetry.disabled = stats.error === 0 || _syncInProgress;
    }
}

function generateEntryId() {
    if (window.crypto && typeof window.crypto.randomUUID === 'function') {
        return window.crypto.randomUUID();
    }
    return `entry_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

document.addEventListener('DOMContentLoaded', () => {
    const csvFileInput = document.getElementById('csv-file');
    const btnUpload = document.getElementById('btn-upload');
    const syncForm = document.getElementById('sync-form');
    const btnAddTask = document.getElementById('btn-add-task');
    const undoBtn = document.getElementById('btn-undo-delete');
    const apiKeyInput = document.getElementById('api-key');
    const btnToggleApiKey = document.getElementById('btn-toggle-api-key');
    const btnClearApiKey = document.getElementById('btn-clear-api-key');
    const btnOpenRequestHistory = document.getElementById('btn-open-request-history');

    btnUpload.addEventListener('click', () => csvFileInput.click());
    document.getElementById('csv-file-name').addEventListener('click', () => csvFileInput.click());
    csvFileInput.addEventListener('change', () => {
        const file = csvFileInput.files[0];
        if (file) {
            setCsvFileNameDisplay(file.name);
            uploadCsvFile(file);
        }
    });
    initCsvDragAndDrop();
    syncForm.addEventListener('submit', handleSync);
    const btnRetryFailed = document.getElementById('btn-retry-failed');
    if (btnRetryFailed) {
        btnRetryFailed.addEventListener('click', handleRetryFailed);
    }
    if (btnAddTask) {
        btnAddTask.addEventListener('click', handleAddTask);
    }
    if (undoBtn) {
        undoBtn.addEventListener('click', handleUndoDeleteTask);
    }
    const btnSyncOverlayClose = document.getElementById('btn-sync-overlay-close');
    if (btnSyncOverlayClose) {
        btnSyncOverlayClose.addEventListener('click', () => {
            setSyncOverlayVisible(false);
        });
    }
    const btnOverlayRetry = document.getElementById('btn-sync-overlay-retry-failed');
    if (btnOverlayRetry) {
        btnOverlayRetry.addEventListener('click', handleRetryFailed);
    }
    const btnRequestHistoryRetry = document.getElementById('btn-request-history-retry-failed');
    if (btnRequestHistoryRetry) {
        btnRequestHistoryRetry.addEventListener('click', handleRetryFailed);
    }
    const btnRequestHistoryClose = document.getElementById('btn-request-history-close');
    if (btnRequestHistoryClose) {
        btnRequestHistoryClose.addEventListener('click', () => {
            setRequestHistoryOverlayVisible(false);
        });
    }
    if (btnOpenRequestHistory) {
        btnOpenRequestHistory.addEventListener('click', () => {
            renderRequestHistory();
            setRequestHistoryOverlayVisible(true);
        });
    }
    const requestHistoryOverlay = document.getElementById('request-history-overlay');
    if (requestHistoryOverlay) {
        requestHistoryOverlay.addEventListener('click', (event) => {
            if (event.target === requestHistoryOverlay) {
                setRequestHistoryOverlayVisible(false);
            }
        });
    }
    document.addEventListener('keydown', (event) => {
        if (event.key !== 'Escape') return;
        const historyOverlay = document.getElementById('request-history-overlay');
        if (historyOverlay && historyOverlay.classList.contains('show')) {
            setRequestHistoryOverlayVisible(false);
        }
    });

    if (btnToggleApiKey && apiKeyInput) {
        btnToggleApiKey.addEventListener('click', () => {
            const isPassword = apiKeyInput.type === 'password';
            apiKeyInput.type = isPassword ? 'text' : 'password';
            btnToggleApiKey.innerHTML = isPassword ? '<i class="bi bi-eye-slash"></i>' : '<i class="bi bi-eye"></i>';
            apiKeyInput.focus();
            apiKeyInput.setSelectionRange(apiKeyInput.value.length, apiKeyInput.value.length);
        });
    }

    if (btnClearApiKey && apiKeyInput) {
        btnClearApiKey.addEventListener('click', () => {
            apiKeyInput.value = '';
            apiKeyInput.focus();
        });
    }

    updateCurrentMonthLabel();

    // Render initial app state
    renderApp();
    updateSyncActionButtons();
    updateSyncResultsSummary();
    renderRequestHistory();

    // Add task confirm modal
    document.getElementById('btn-confirm-add-task').addEventListener('click', () => {
        const newId = document.getElementById('add-task-id').value.trim();
        const newName = document.getElementById('add-task-name').value.trim();
        if (!newId || !newName) {
            showToast('Lỗi', 'Vui lòng nhập đầy đủ thông tin.', 'warning');
            return;
        }
        appState.tasks.push({
            taskId: newId,
            taskName: newName,
            taskUrl: `#`,
            totalHours: 0,
            dayEntries: {}
        });
        if (appState.dates.length === 0) {
            appState.dates = getCurrentMonthDates();
        }
        bootstrap.Modal.getInstance(document.getElementById('addTaskModal')).hide();
        renderApp();
        showToast('Thành công', 'Đã thêm công việc mới.', 'success');
    });

    document.getElementById('addTaskModal').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            document.getElementById('btn-confirm-add-task').click();
        }
    });

    document.getElementById('addTaskModal').addEventListener('show.bs.modal', () => {
        document.getElementById('add-task-id').value = '';
        document.getElementById('add-task-name').value = '';
    });

    document.getElementById('addTaskModal').addEventListener('shown.bs.modal', () => {
        document.getElementById('add-task-id').focus();
    });

    // Edit save modal
    document.getElementById('btn-save-edit').addEventListener('click', () => {
        if (_pendingEditIndex !== null) {
            const newId = document.getElementById('edit-task-id').value.trim();
            const newName = document.getElementById('edit-task-name').value.trim();
            if (!newId || !newName) {
                showToast('Lỗi', 'Vui lòng nhập đầy đủ thông tin.', 'warning');
                return;
            }
            appState.tasks[_pendingEditIndex].taskId = newId;
            appState.tasks[_pendingEditIndex].taskName = newName;
            _pendingEditIndex = null;
            bootstrap.Modal.getInstance(document.getElementById('editTaskModal')).hide();
            renderApp();
        }
    });

    // Add column hover effect
    const tableContainer = document.getElementById('table-container');
    if (tableContainer) {
        tableContainer.addEventListener('mouseover', (e) => {
            const td = e.target.closest('td, th');
            if (!td) return;
            const table = td.closest('table');
            if (!table) return;
            
            const colIdx = td.cellIndex;
            const rows = table.rows;
            for (let i = 0; i < rows.length; i++) {
                if (rows[i].cells[colIdx]) {
                    rows[i].cells[colIdx].classList.add('col-hover');
                }
            }
        });
        
        tableContainer.addEventListener('mouseout', (e) => {
            const td = e.target.closest('td, th');
            if (!td) return;
            const table = td.closest('table');
            if (!table) return;
            
            const colIdx = td.cellIndex;
            const rows = table.rows;
            for (let i = 0; i < rows.length; i++) {
                if (rows[i].cells[colIdx]) {
                    rows[i].cells[colIdx].classList.remove('col-hover');
                }
            }
        });
    }
});

function handleAddTask() {
    new bootstrap.Modal(document.getElementById('addTaskModal')).show();
}

function setCsvFileNameDisplay(fileName) {
    const nameBox = document.getElementById('csv-file-name');
    if (!nameBox) return;
    const icon = nameBox.querySelector('i');
    if (icon) {
        icon.className = 'bi bi-file-earmark-text me-1 text-indigo';
    }
    nameBox.style.color = '';
    const textEl = document.getElementById('csv-file-name-text');
    if (textEl) {
        textEl.textContent = fileName;
    }
}

function isCsvFile(file) {
    if (!file) return false;
    const lowerName = String(file.name || '').toLowerCase();
    if (lowerName.endsWith('.csv')) return true;
    return file.type === 'text/csv' || file.type === 'application/vnd.ms-excel';
}

async function uploadCsvFile(file) {
    if (!file) return;
    if (!isCsvFile(file)) {
        showToast('Lỗi', 'Chỉ chấp nhận tệp CSV.', 'warning');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    const btn = document.getElementById('btn-upload');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Đang xử lý CSV...';

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Tải tệp thất bại');
        
        appState = data;
        warnIfCsvOutsideCurrentMonth(appState.dates || []);
        renderApp();
        showToast('Thành công', 'Đã tải dữ liệu CSV thành công.', 'success');
    } catch (error) {
        showToast('Lỗi', error.message, 'danger');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-upload me-1"></i>Chọn CSV';
        const fileInput = document.getElementById('csv-file');
        if (fileInput) {
            fileInput.value = '';
        }
    }
}

function initCsvDragAndDrop() {
    const body = document.body;
    if (!body) return;
    const dragEvents = ['dragenter', 'dragover', 'dragleave', 'drop'];
    dragEvents.forEach((eventName) => {
        body.addEventListener(eventName, (event) => {
            event.preventDefault();
            event.stopPropagation();
        });
    });

    body.addEventListener('dragenter', (event) => {
        const hasFiles = event.dataTransfer && Array.from(event.dataTransfer.types || []).includes('Files');
        if (!hasFiles) return;
        _dragCounter += 1;
        body.classList.add('dragover-csv');
    });

    body.addEventListener('dragover', (event) => {
        const hasFiles = event.dataTransfer && Array.from(event.dataTransfer.types || []).includes('Files');
        if (!hasFiles) return;
        body.classList.add('dragover-csv');
    });

    body.addEventListener('dragleave', (event) => {
        const hasFiles = event.dataTransfer && Array.from(event.dataTransfer.types || []).includes('Files');
        if (!hasFiles) return;
        _dragCounter = Math.max(0, _dragCounter - 1);
        if (_dragCounter === 0) {
            body.classList.remove('dragover-csv');
        }
    });

    body.addEventListener('drop', async (event) => {
        body.classList.remove('dragover-csv');
        _dragCounter = 0;
        const files = event.dataTransfer ? event.dataTransfer.files : null;
        if (!files || files.length === 0) return;
        if (files.length > 1) {
            showToast('Lỗi', 'Chỉ hỗ trợ import 1 tệp CSV mỗi lần.', 'warning');
            return;
        }
        const file = files[0];
        if (!isCsvFile(file)) {
            showToast('Lỗi', 'Chỉ chấp nhận tệp CSV.', 'warning');
            return;
        }
        setCsvFileNameDisplay(file.name);
        await uploadCsvFile(file);
    });
}

function updateTotals() {
    let totalHours = 0;
    appState.tasks.forEach((task, index) => {
        let taskTotal = 0;
        appState.dates.forEach(date => {
            taskTotal += parseFloat(task.dayEntries[date] || 0);
        });
        task.totalHours = taskTotal;
        totalHours += taskTotal;
        
        const totalCell = document.getElementById(`total-${index}`);
        if (totalCell) {
            totalCell.innerText = taskTotal > 0 ? taskTotal.toFixed(2) : '—';
        }
    });
    appState.effortSum = totalHours;
    document.getElementById('summary-hours').innerText = totalHours.toFixed(2);
}

function renderApp() {
    const hasTasks = appState.tasks.length > 0;
    const summaryBar = document.getElementById('summary-bar');
    summaryBar.style.display = hasTasks ? '' : 'none';
    summaryBar.classList.toggle('is-visible', hasTasks);
    updateSyncActionButtons();
    updateWorkflowSteps();

    if (hasTasks) {
        document.getElementById('summary-name').innerText = appState.memberName || 'Không có';
        document.getElementById('summary-role').innerText = appState.role || 'Không có';
        updateTotals();
    }

    updateSummaryMetrics();
    renderTable();
}

function renderTable() {
    const thead = document.getElementById('table-header');
    const tbody = document.getElementById('table-body');
    
    // Clear existing
    thead.innerHTML = '';
    tbody.innerHTML = '';

    // Render Headers
    let headerHtml = `<th class="sticky-col first-col">Issue ID</th>
                      <th class="sticky-col second-col">Tên</th>
                      <th class="sticky-col third-col text-center">Tổng giờ</th>`;

    const todayIso = new Date().toISOString().slice(0, 10);
    appState.dates.forEach(date => {
        const d = new Date(date + 'T00:00:00');
        const dayOfWeek = d.getDay();
        const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;
        const isToday = date === todayIso;
        const dayNames = ['CN', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7'];
        const label = `${dayNames[dayOfWeek]}<br><span style="font-weight:400;font-size:0.7rem">${date.slice(5)}</span>`;
        headerHtml += `<th class="text-center min-w-100${isWeekend ? ' weekend-col' : ''}${isToday ? ' today-col' : ''}">${label}</th>`;
    });
    headerHtml += `<th class="action-col text-center">Thao tác</th>`;
    thead.innerHTML = headerHtml;

    // Render Rows
    if (appState.tasks.length === 0) {
        const tr = document.createElement('tr');
        const colSpan = 4 + appState.dates.length;
        tr.innerHTML = `<td colspan="${colSpan}" class="empty-state-td">
            <div class="empty-state">
                <i class="bi bi-inbox empty-state-icon"></i>
                <h5 class="empty-state-title">Chưa có dữ liệu</h5>
                <p class="empty-state-desc">Vui lòng tải lên tệp CSV timesheet hoặc thêm công việc thủ công để bắt đầu log time.</p>
                <button class="btn btn-indigo" onclick="document.getElementById('csv-file').click()">
                    <i class="bi bi-upload me-2"></i>Tải tệp CSV ngay
                </button>
            </div>
        </td>`;
        tbody.appendChild(tr);
    } else {
        const dayTotals = {};
        appState.dates.forEach((d) => { dayTotals[d] = 0; });
        appState.tasks.forEach((task, taskIndex) => {
            const tr = document.createElement('tr');
            
            const hasIssueId = String(task.taskId || '').trim().length > 0;
            const issueCell = hasIssueId
                ? `<a href="${escapeAttr(task.taskUrl || '#')}" target="_blank" rel="noopener noreferrer">${escapeHtml(String(task.taskId))}</a>`
                : `<span class="badge text-bg-warning">Thiếu ID</span>`;
            let rowHtml = `
                <td class="sticky-col first-col">${issueCell}</td>
                <td class="sticky-col second-col" title="${escapeAttr(task.taskName || '')}">${escapeHtml(task.taskName || '')}</td>
                <td class="sticky-col third-col text-center fw-bold" id="total-${taskIndex}">
                    ${task.totalHours > 0 ? task.totalHours.toFixed(2) : '—'}
                </td>
            `;

            tr.innerHTML = rowHtml;

            // Add input cells for dates
            appState.dates.forEach(date => {
                const d = new Date(date + 'T00:00:00');
                const isWeekend = d.getDay() === 0 || d.getDay() === 6;
                const td = document.createElement('td');
                td.className = `text-center p-1${isWeekend ? ' weekend-col' : ''}`;
                const val = task.dayEntries[date] || 0;
                const hoursNum = parseFloat(val || 0) || 0;
                if (hoursNum > 0) dayTotals[date] += hoursNum;
                
                const input = document.createElement('input');
                input.type = 'number';
                input.step = '0.5';
                input.min = '0';
                input.max = '24';
                input.placeholder = ' ';
                input.value = val > 0 ? val : '';
                
                input.dataset.row = String(taskIndex);
                input.dataset.col = String(3 + appState.dates.indexOf(date));

                input.addEventListener('focus', () => {
                    setGridFocusStyle(input);
                });
                input.addEventListener('blur', () => {
                    window.setTimeout(() => {
                        if (!document.activeElement || document.activeElement.tagName !== 'INPUT') {
                            clearGridFocusStyle();
                        }
                    }, 0);
                });

                input.addEventListener('keydown', (e) => {
                    handleGridInputKeydown(e, input);
                });

                input.addEventListener('change', (e) => {
                    let newVal = parseFloat(e.target.value) || 0;
                    if (newVal < 0) newVal = 0;
                    if (newVal > 24) newVal = 24;
                    newVal = Math.round(newVal * 2) / 2;
                    e.target.value = newVal > 0 ? String(newVal) : '';
                    appState.tasks[taskIndex].dayEntries[date] = newVal;
                    updateTotals(); // Re-render to update totals without rebuilding the table
                    updateSummaryMetrics();
                });

                td.appendChild(input);
                tr.appendChild(td);
            });

            // Action column
            const tdAction = document.createElement('td');
            tdAction.className = 'action-col text-center';

            const btnEdit = document.createElement('button');
            btnEdit.type = 'button';
            btnEdit.className = 'btn-icon btn-edit me-1';
            btnEdit.title = 'Chỉnh sửa';
            btnEdit.innerHTML = '<i class="bi bi-pencil"></i>';
            btnEdit.onclick = () => handleEditTask(taskIndex);

            const btnDel = document.createElement('button');
            btnDel.type = 'button';
            btnDel.className = 'btn-icon btn-delete';
            btnDel.title = 'Xóa';
            btnDel.innerHTML = '<i class="bi bi-trash3"></i>';
            btnDel.onclick = () => handleDeleteTask(taskIndex);

            tdAction.appendChild(btnEdit);
            tdAction.appendChild(btnDel);
            tr.appendChild(tdAction);

            tbody.appendChild(tr);
        });

        // Day totals row
        const totalTr = document.createElement('tr');
        totalTr.className = 'day-total-row';
        let totalRowHtml = `
            <td class="sticky-col first-col">Tổng ngày</td>
            <td class="sticky-col second-col"></td>
            <td class="sticky-col third-col text-center fw-bold">${appState.effortSum > 0 ? appState.effortSum.toFixed(2) : '—'}</td>
        `;
        totalTr.innerHTML = totalRowHtml;
        appState.dates.forEach((date) => {
            const d = new Date(date + 'T00:00:00');
            const isWeekend = d.getDay() === 0 || d.getDay() === 6;
            const td = document.createElement('td');
            td.className = `text-center${isWeekend ? ' weekend-col' : ''}`;
            const v = dayTotals[date] || 0;
            td.textContent = v > 0 ? v.toFixed(2) : '—';
            totalTr.appendChild(td);
        });
        const tdAction = document.createElement('td');
        tdAction.className = 'action-col text-center';
        tdAction.textContent = '—';
        totalTr.appendChild(tdAction);
        tbody.appendChild(totalTr);
    }
}

function collectSyncEntries() {
    const out = [];
    appState.tasks.forEach(task => {
        if (!task.taskId) return;
        appState.dates.forEach(date => {
            const hours = parseFloat(task.dayEntries[date] || 0);
            if (hours > 0) {
                out.push({
                    entry_id: generateEntryId(),
                    issue_id: String(task.taskId),
                    spent_on: date,
                    hours,
                    activity_id: DEFAULT_ACTIVITY_ID,
                    taskName: task.taskName || ''
                });
            }
        });
    });
    return out;
}

function toApiEntries(rows) {
    return rows.map(e => ({
        entry_id: e.entry_id,
        issue_id: e.issue_id,
        spent_on: e.spent_on,
        hours: e.hours,
        activity_id: e.activity_id
    }));
}

function updateSyncActionButtons() {
    const btnSync = document.getElementById('btn-sync');
    const btnRetry = document.getElementById('btn-retry-failed');
    const btnOverlayRetry = document.getElementById('btn-sync-overlay-retry-failed');
    const btnRequestHistoryRetry = document.getElementById('btn-request-history-retry-failed');
    if (!btnSync) return;
    const hasTasks = appState.tasks.length > 0;
    const hasFailed = syncResultRows.some(r => r.status === 'error');
    if (btnRetry) {
        btnRetry.disabled = !hasFailed || _syncInProgress;
    }
    if (btnOverlayRetry) {
        btnOverlayRetry.disabled = !hasFailed || _syncInProgress;
    }
    if (btnRequestHistoryRetry) {
        btnRequestHistoryRetry.disabled = !hasFailed || _syncInProgress;
    }
    if (!hasTasks) {
        btnSync.disabled = true;
    } else {
        btnSync.disabled = _syncInProgress || collectSyncEntries().length === 0;
    }
    updateWorkflowSteps();
}

function renderSyncResults() {
    const overlayResults = document.getElementById('sync-overlay-results');
    const overlayTbody = document.getElementById('sync-overlay-results-tbody');
    if (syncResultRows.length === 0) {
        if (overlayResults) {
            overlayResults.hidden = true;
        }
        updateSyncResultsSummary();
        return;
    }
    if (overlayTbody) {
        overlayTbody.innerHTML = '';
    }
    if (overlayResults) {
        overlayResults.hidden = false;
    }
    syncResultRows.forEach(row => {
        const overlayTr = document.createElement('tr');
        let statusHtml = '';
        if (row.status === 'pending') {
            statusHtml = '<span class="badge text-bg-secondary"><span class="spinner-border spinner-border-sm me-1" style="width:0.65rem;height:0.65rem;"></span>Đang gửi</span>';
        } else if (row.status === 'ok') {
            statusHtml = '<span class="badge text-bg-success">Thành công</span>';
        } else {
            statusHtml = '<span class="badge text-bg-danger">Thất bại</span>';
        }
        const detail = row.error
            ? (row.httpStatus != null ? `[${row.httpStatus}] ` : '') + escapeHtml(String(row.error).slice(0, 500))
            : (row.status === 'ok' ? '—' : '');
        overlayTr.innerHTML = `
            <td class="text-nowrap">${escapeHtml(String(row.issue_id))}</td>
            <td class="text-nowrap">${escapeHtml(row.spent_on)}</td>
            <td class="text-end">${Number(row.hours).toFixed(2)}</td>
            <td>${statusHtml}</td>
            <td class="small text-break" style="max-width: 18rem;">${detail || '—'}</td>
        `;
        if (overlayTbody) {
            overlayTbody.appendChild(overlayTr);
        }
    });
    updateSyncResultsSummary();
    updateSyncOverlayProgress();
    updateSyncActionButtons();
    updateWorkflowSteps();
}

function escapeHtml(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}

function escapeAttr(s) {
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/</g, '&lt;');
}

/**
 * @param {ReturnType<typeof toApiEntries>} apiEntries
 */
async function runSseStream(apiEntries, apiKey) {
    const response = await fetch('/api/sync/stream', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream'
        },
        body: JSON.stringify({ apiKey, entries: apiEntries })
    });

    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.error || `HTTP ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split('\n\n');
        buffer = blocks.pop() || '';
        for (const block of blocks) {
            for (const line of block.split('\n')) {
                if (line.startsWith('data: ')) {
                    const payload = JSON.parse(line.slice(6));
                    if (payload.type === 'result') {
                        const row = syncResultRows.find(x => x.entry_id === payload.entry_id);
                        if (row) {
                            row.status = payload.ok ? 'ok' : 'error';
                            row.error = payload.error || null;
                            row.httpStatus = payload.status_code != null ? payload.status_code : null;
                        }
                        const detail = payload.ok
                            ? 'Thành công'
                            : (payload.status_code != null ? `[${payload.status_code}] ` : '') + (payload.error || 'Có lỗi');
                        updateRequestHistoryRow(payload.entry_id, payload.ok ? 'ok' : 'error', detail);
                        renderSyncResults();
                    } else if (payload.type === 'done') {
                        const ok = (payload.failed || 0) === 0;
                        if (ok) {
                            showToast('Hoàn tất', `Đã xử lý ${payload.total} bản ghi.`, 'success');
                        } else {
                            showToast('Hoàn tất (có lỗi)', `Thành công: ${payload.success}, thất bại: ${payload.failed}.`, 'warning');
                        }
                    }
                }
            }
        }
    }
}

async function handleSync(e) {
    e.preventDefault();
    const apiKey = document.getElementById('api-key').value;
    if (!apiKey) {
        showToast('Lỗi', 'Vui lòng nhập khóa API', 'warning');
        return;
    }

    const collected = collectSyncEntries();
    const missingIssueCount = appState.tasks.filter((task) => !String(task.taskId || '').trim()).length;
    if (missingIssueCount > 0) {
        showToast('Lưu ý', `${missingIssueCount} task thiếu Issue ID sẽ bị bỏ qua khi đồng bộ.`, 'warning');
    }
    if (collected.length === 0) {
        showToast('Thông báo', 'Không có dữ liệu giờ làm việc để đồng bộ.', 'info');
        return;
    }

    syncResultRows = collected.map(r => ({
        ...r,
        status: 'pending',
        error: null,
        httpStatus: null
    }));
    addRequestHistoryRows(collected);
    renderSyncResults();

    setSyncOverlayPhase('loading');
    _syncInProgress = true;
    setSyncOverlayVisible(true);
    updateSyncOverlayProgress();
    updateSyncActionButtons();

    let syncOverlayError = null;
    try {
        await runSseStream(toApiEntries(collected), apiKey);
    } catch (error) {
        syncOverlayError = error;
        showToast('Lỗi', error.message, 'danger');
    } finally {
        _syncInProgress = false;
        setSyncOverlayPhase('done', { hasError: !!syncOverlayError });
        updateSyncActionButtons();
        updateWorkflowSteps();
    }
}

async function handleRetryFailed() {
    const apiKey = document.getElementById('api-key').value;
    if (!apiKey) {
        showToast('Lỗi', 'Vui lòng nhập khóa API', 'warning');
        return;
    }
    const failed = syncResultRows.filter(r => r.status === 'error');
    if (failed.length === 0) {
        showToast('Thông báo', 'Không có bản ghi thất bại.', 'info');
        return;
    }

    failed.forEach(r => {
        r.status = 'pending';
        r.error = null;
        r.httpStatus = null;
    });
    addRequestHistoryRows(failed);
    renderSyncResults();

    const btnRetry = document.getElementById('btn-retry-failed');
    setSyncOverlayPhase('loading');
    _syncInProgress = true;
    setSyncOverlayVisible(true);
    updateSyncOverlayProgress();
    updateSyncActionButtons();
    if (btnRetry) btnRetry.disabled = true;

    let syncOverlayError = null;
    try {
        await runSseStream(toApiEntries(failed), apiKey);
    } catch (error) {
        syncOverlayError = error;
        showToast('Lỗi', error.message, 'danger');
    } finally {
        _syncInProgress = false;
        setSyncOverlayPhase('done', { hasError: !!syncOverlayError });
        updateSyncActionButtons();
        updateWorkflowSteps();
    }
}

function handleDeleteTask(taskIndex) {
    const task = appState.tasks[taskIndex];
    if (!task) return;
    _lastDeletedTask = {
        task: { ...task, dayEntries: { ...task.dayEntries } },
        index: taskIndex
    };
    appState.tasks.splice(taskIndex, 1);
    renderApp();
    showUndoDeleteBanner(task);
}

function showUndoDeleteBanner(task) {
    const banner = document.getElementById('undo-delete-banner');
    const text = document.getElementById('undo-delete-text');
    if (!banner || !text || !_lastDeletedTask) return;
    const taskName = task.taskName || task.taskId || 'công việc';
    text.innerText = `Đã xóa "${taskName}".`;
    banner.hidden = false;
    if (_undoDeleteTimer) {
        window.clearTimeout(_undoDeleteTimer);
    }
    _undoDeleteTimer = window.setTimeout(() => {
        hideUndoDeleteBanner();
        _lastDeletedTask = null;
    }, 8000);
}

function hideUndoDeleteBanner() {
    const banner = document.getElementById('undo-delete-banner');
    if (!banner) return;
    banner.hidden = true;
}

function handleUndoDeleteTask() {
    if (!_lastDeletedTask) return;
    const safeIndex = Math.min(_lastDeletedTask.index, appState.tasks.length);
    appState.tasks.splice(safeIndex, 0, _lastDeletedTask.task);
    if (_undoDeleteTimer) {
        window.clearTimeout(_undoDeleteTimer);
        _undoDeleteTimer = null;
    }
    hideUndoDeleteBanner();
    _lastDeletedTask = null;
    renderApp();
}

function setGridFocusStyle(inputEl) {
    clearGridFocusStyle();
    const td = inputEl.closest('td');
    if (!td) return;
    const tr = td.closest('tr');
    if (tr) tr.classList.add('row-focus');
    const table = td.closest('table');
    if (!table) return;
    const colIdx = td.cellIndex;
    const rows = table.rows;
    for (let i = 0; i < rows.length; i++) {
        if (rows[i].cells[colIdx]) rows[i].cells[colIdx].classList.add('col-focus');
    }
}

function clearGridFocusStyle() {
    document.querySelectorAll('#matrix-table tr.row-focus').forEach((row) => row.classList.remove('row-focus'));
    document.querySelectorAll('#matrix-table .col-focus').forEach((cell) => cell.classList.remove('col-focus'));
}

function handleGridInputKeydown(event, inputEl) {
    const row = Number(inputEl.dataset.row);
    const col = Number(inputEl.dataset.col);
    const rowDelta = event.key === 'Enter' ? (event.shiftKey ? -1 : 1) : 0;
    const colDelta = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0;
    if (event.key === 'Tab') {
        event.preventDefault();
        const minCol = 3;
        const maxCol = 3 + Math.max(0, appState.dates.length - 1);
        const dir = event.shiftKey ? -1 : 1;
        let nextRow = row;
        let nextCol = col + dir;
        if (nextCol > maxCol) {
            nextRow = row + 1;
            nextCol = minCol;
        } else if (nextCol < minCol) {
            nextRow = row - 1;
            nextCol = maxCol;
        }
        focusGridInputByPosition(nextRow, nextCol);
        return;
    }
    if (rowDelta === 0 && colDelta === 0) return;
    event.preventDefault();
    focusGridInputByPosition(row + rowDelta, col + colDelta);
}

function focusGridInputByPosition(row, col) {
    const selector = `#matrix-table input[data-row="${row}"][data-col="${col}"]`;
    const nextInput = document.querySelector(selector);
    if (!nextInput) return;
    nextInput.focus();
    nextInput.select();
}

function updateSyncOverlayProgress() {
    const textEl = document.getElementById('sync-overlay-text');
    if (!textEl) return;
    if (!_syncInProgress || syncResultRows.length === 0) return;
    const stats = getSyncStats();
    const completed = stats.ok + stats.error;
    textEl.textContent = `Đang đồng bộ dữ liệu... (${completed}/${stats.total})`;
}

function updateCurrentMonthLabel() {
    const el = document.getElementById('current-month-label');
    if (!el) return;
    const now = new Date();
    const mm = String(now.getMonth() + 1).padStart(2, '0');
    el.textContent = `${mm}/${now.getFullYear()}`;
}

function warnIfCsvOutsideCurrentMonth(dates) {
    if (!Array.isArray(dates) || dates.length === 0) return;
    const now = new Date();
    const currentYm = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
    const hasOther = dates.some((d) => String(d || '').slice(0, 7) !== currentYm);
    if (hasOther) {
        showToast('Lưu ý', 'CSV có ngày không thuộc tháng hiện tại. Vui lòng kiểm tra lại trước khi đồng bộ.', 'warning');
    }
}

function updateWorkflowSteps() {
    const s1 = document.getElementById('step-1');
    const s2 = document.getElementById('step-2');
    const s3 = document.getElementById('step-3');
    if (!s1 || !s2 || !s3) return;
    const hasTasks = appState.tasks.length > 0;
    s1.classList.toggle('is-active', !hasTasks);
    s2.classList.toggle('is-active', hasTasks && !_syncInProgress);
    s3.classList.toggle('is-active', _syncInProgress);
    s1.classList.toggle('is-done', hasTasks);
    s2.classList.toggle('is-done', syncResultRows.length > 0);
}

function handleEditTask(taskIndex) {
    _pendingEditIndex = taskIndex;
    const task = appState.tasks[taskIndex];
    document.getElementById('edit-task-id').value = task.taskId || '';
    document.getElementById('edit-task-name').value = task.taskName || '';
    new bootstrap.Modal(document.getElementById('editTaskModal')).show();
}

function showToast(title, message, type = 'primary') {
    const toastEl = document.getElementById('liveToast');
    const toastTitle = document.getElementById('toast-title');
    const toastMessage = document.getElementById('toast-message');
    
    toastTitle.innerText = title;
    toastMessage.innerText = message;
    
    // Remove old color classes
    toastEl.classList.remove('text-bg-primary', 'text-bg-success', 'text-bg-danger', 'text-bg-warning', 'text-bg-info');
    toastEl.classList.add(`text-bg-${type}`);
    
    const toast = new bootstrap.Toast(toastEl);
    toast.show();
}
