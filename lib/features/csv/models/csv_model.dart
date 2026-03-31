class DayEntry {
  final String date;
  final double hours;

  const DayEntry({required this.date, required this.hours});
}

class TaskEntry {
  final String taskId;
  final String taskName;
  final String taskUrl;
  final List<DayEntry> dayEntries;

  const TaskEntry({
    required this.taskId,
    required this.taskName,
    required this.taskUrl,
    required this.dayEntries,
  });

  double get totalHours =>
      dayEntries.fold(0.0, (sum, entry) => sum + entry.hours);
}

class ParsedData {
  final String memberName;
  final String role;
  final double effortSum;
  final List<TaskEntry> tasks;

  const ParsedData({
    required this.memberName,
    required this.role,
    required this.effortSum,
    required this.tasks,
  });
}
