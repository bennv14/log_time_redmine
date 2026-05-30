/**
 * Simple frontend logic tests for log_time_redmine
 * Run with: node tests/frontend_test.js
 */

// Mocking the environment
const appState = {
    tasks: [
        { taskId: "17513", taskName: "Task 1", dayEntries: { "2026-04-01": 4, "2026-04-02": 4 } },
        { taskId: "19476", taskName: "Task 2", dayEntries: { "2026-04-02": 4, "2026-04-03": 4 } }
    ],
    dates: ["2026-04-01", "2026-04-02", "2026-04-03"]
};

// Functions to test (copied/adapted from app.js for isolation)
function makeDiffKey(issueId, spentOn) {
    return `${String(issueId || '').trim()}__${String(spentOn || '').trim()}`;
}

function getTaskSnapshotsForIssueDate(issueId, spentOn) {
    const snapshots = [];
    appState.tasks.forEach((task, taskIndex) => {
        if (String(task.taskId || '').trim() !== String(issueId)) return;
        snapshots.push({
            taskIndex,
            hours: parseFloat(task.dayEntries[spentOn] || 0) || 0
        });
    });
    return snapshots;
}

// Test Suite
console.log("Running Frontend Logic Tests...");

// Test makeDiffKey
const key = makeDiffKey("123", "2026-04-01");
console.assert(key === "123__2026-04-01", "makeDiffKey failed");

// Test getTaskSnapshotsForIssueDate
const snapshots = getTaskSnapshotsForIssueDate("17513", "2026-04-01");
console.assert(snapshots.length === 1, "Should find 1 snapshot for 17513 on 4/1");
console.assert(snapshots[0].taskIndex === 0, "Snapshot index should be 0");
console.assert(snapshots[0].hours === 4, "Snapshot hours should be 4");

const snapshots2 = getTaskSnapshotsForIssueDate("17513", "2026-04-03");
console.assert(snapshots2.length === 1, "Should find snapshot even if hours are 0");
console.assert(snapshots2[0].hours === 0, "Should have 0 hours for 4/3");

const snapshots3 = getTaskSnapshotsForIssueDate("99999", "2026-04-01");
console.assert(snapshots3.length === 0, "Should find no snapshots for unknown task");

console.log("All frontend logic tests passed!");
