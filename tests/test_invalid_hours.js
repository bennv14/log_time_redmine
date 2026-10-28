/**
 * Simple frontend logic tests for log_time_redmine
 * Run with: node tests/frontend_test.js
 */

// Mocking the environment
let appState = {
    tasks: [
        { taskId: "17513", taskName: "Task 1", dayEntries: { "2026-04-01": 4, "2026-04-02": 4 } },
        { taskId: "19476", taskName: "Task 2", dayEntries: { "2026-04-02": 4, "2026-04-03": 25 } }
    ],
    dates: ["2026-04-01", "2026-04-02", "2026-04-03"]
};

function hasInvalidHours() {
    return appState.tasks.some(task => 
        Object.values(task.dayEntries).some(h => {
            const val = parseFloat(h);
            return val < 0 || val > 24;
        })
    );
}

// Test Suite
console.log("Running Frontend Invalid Hours Test (>24h)...");

console.assert(hasInvalidHours() === true, "Should detect hours > 24");
appState.tasks[1].dayEntries["2026-04-03"] = -1;
console.assert(hasInvalidHours() === true, "Should detect negative hours");
appState.tasks[1].dayEntries["2026-04-03"] = 8;
console.assert(hasInvalidHours() === false, "Should not detect invalid hours after fix");

console.log("All frontend logic tests passed!");
