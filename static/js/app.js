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

document.addEventListener('DOMContentLoaded', () => {
    const csvFileInput = document.getElementById('csv-file');
    const btnUpload = document.getElementById('btn-upload');
    const syncForm = document.getElementById('sync-form');
    const btnAddTask = document.getElementById('btn-add-task');

    btnUpload.addEventListener('click', () => csvFileInput.click());
    document.getElementById('csv-file-name').addEventListener('click', () => csvFileInput.click());
    csvFileInput.addEventListener('change', () => {
        const file = csvFileInput.files[0];
        if (file) {
            const nameBox = document.getElementById('csv-file-name');
            nameBox.querySelector('i').className = 'bi bi-file-earmark-text me-1 text-indigo';
            nameBox.style.color = '';
            document.getElementById('csv-file-name-text').textContent = file.name;
            handleUpload();
        }
    });
    syncForm.addEventListener('submit', handleSync);
    if (btnAddTask) {
        btnAddTask.addEventListener('click', handleAddTask);
    }

    // Render table with current month dates on initial load
    renderTable();

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

async function handleUpload() {
    const fileInput = document.getElementById('csv-file');
    const file = fileInput.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    const btn = document.getElementById('btn-upload');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Đang xử lý...';

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Tải tệp thất bại');
        
        appState = data;
        renderApp();
        showToast('Thành công', 'Đã tải dữ liệu CSV thành công.', 'success');
    } catch (error) {
        showToast('Lỗi', error.message, 'danger');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-upload me-1"></i>Tải lên';
        fileInput.value = '';
    }
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
            totalCell.innerText = taskTotal.toFixed(2);
        }
    });
    appState.effortSum = totalHours;
    document.getElementById('summary-hours').innerText = totalHours.toFixed(2);
}

function renderApp() {
    const hasTasks = appState.tasks.length > 0;
    document.getElementById('summary-bar').style.display = hasTasks ? '' : 'none';
    document.getElementById('btn-sync').disabled = !hasTasks;

    if (hasTasks) {
        document.getElementById('summary-name').innerText = appState.memberName || 'Không có';
        document.getElementById('summary-role').innerText = appState.role || 'Không có';
        document.getElementById('summary-tasks').innerText = appState.tasks.length;
        updateTotals();
    }

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

    appState.dates.forEach(date => {
        const d = new Date(date + 'T00:00:00');
        const dayOfWeek = d.getDay();
        const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;
        const dayNames = ['CN', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7'];
        const label = `${dayNames[dayOfWeek]}<br><span style="font-weight:400;font-size:0.7rem">${date.slice(5)}</span>`;
        headerHtml += `<th class="text-center min-w-100${isWeekend ? ' weekend-col' : ''}">${label}</th>`;
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
        appState.tasks.forEach((task, taskIndex) => {
            const tr = document.createElement('tr');
            
            let rowHtml = `
                <td class="sticky-col first-col">
                    <a href="${task.taskUrl}" target="_blank">${task.taskId || 'Không có'}</a>
                </td>
                <td class="sticky-col second-col">
                    ${task.taskName}
                </td>
                <td class="sticky-col third-col text-center fw-bold" id="total-${taskIndex}">
                    ${task.totalHours.toFixed(2)}
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
                
                const input = document.createElement('input');
                input.type = 'number';
                input.step = '0.5';
                input.min = '0';
                input.max = '24';
                input.placeholder = ' ';
                input.value = val > 0 ? val : '';
                
                input.addEventListener('change', (e) => {
                    let newVal = parseFloat(e.target.value) || 0;
                    appState.tasks[taskIndex].dayEntries[date] = newVal;
                    updateTotals(); // Re-render to update totals without rebuilding the table
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
            btnDel.onclick = () => handleDeleteConfirm(taskIndex);

            tdAction.appendChild(btnEdit);
            tdAction.appendChild(btnDel);
            tr.appendChild(tdAction);

            tbody.appendChild(tr);
        });
    }
}

async function handleSync(e) {
    e.preventDefault();
    const apiKey = document.getElementById('api-key').value;
    if (!apiKey) {
        showToast('Lỗi', 'Vui lòng nhập khóa API', 'warning');
        return;
    }

    // Prepare entries
    const entries = [];
    appState.tasks.forEach(task => {
        if (!task.taskId) return; // Skip if no valid Redmine Issue ID
        
        appState.dates.forEach(date => {
            const hours = parseFloat(task.dayEntries[date] || 0);
            if (hours > 0) {
                entries.push({
                    issue_id: task.taskId,
                    spent_on: date,
                    hours: hours,
                    activity_id: 2
                });
            }
        });
    });

    if (entries.length === 0) {
        showToast('Thông báo', 'Không có dữ liệu giờ làm việc để đồng bộ.', 'info');
        return;
    }

    const btn = document.getElementById('btn-sync');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Đang gửi...';

    try {
        const response = await fetch('/api/sync', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                apiKey: apiKey,
                entries: entries
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast('Thành công', `Đã đồng bộ ${data.success_count} bản ghi.`, 'success');
        } else {
            let msg = `Thành công: ${data.success_count || 0}. Lỗi: ${data.errors ? data.errors.length : 1}`;
            showToast('Đồng bộ có lỗi', msg, 'warning');
            console.error(data.errors);
        }
    } catch (error) {
        showToast('Lỗi', error.message, 'danger');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-arrow-repeat me-1"></i>Đồng bộ';
    }
}

function handleDeleteConfirm(taskIndex) {
    appState.tasks.splice(taskIndex, 1);
    renderApp();
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
