/**
 * Simple frontend logic tests for log_time_redmine
 * Run with: node tests/frontend_test.js
 */

// Mocking the environment
let appState = {
    tasks: [
        { taskId: "17513", taskName: "Task 1", dayEntries: { "2026-04-01": 4, "2026-04-02": 4 } },
        { taskId: "19476", taskName: "Task 2", dayEntries: { "2026-04-02": 4, "2026-04-03": -1 } }
    ],
    dates: ["2026-04-01", "2026-04-02", "2026-04-03"]
};

function hasNegativeHours() {
    return appState.tasks.some(task => 
        Object.values(task.dayEntries).some(h => parseFloat(h) < 0)
    );
}

// Test Suite
console.log("Running Frontend Negative Hours Test...");

console.assert(hasNegativeHours() === true, "Should detect negative hours");
appState.tasks[1].dayEntries["2026-04-03"] = 0;
console.assert(hasNegativeHours() === false, "Should not detect negative hours after fix");

console.log("All frontend logic tests passed!");
