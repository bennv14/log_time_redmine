import 'package:csv/csv.dart';
import '../models/csv_model.dart';

class CsvParser {
  static ParsedData? parse(String csvContent) {
    final rows = const CsvToListConverter(eol: '\n').convert(csvContent);
    if (rows.isEmpty) return null;

    String memberName = '';
    String role = '';
    double effortSum = 0;
    List<String> dates = [];
    List<TaskEntry> tasks = [];

    int headerRowIndex = -1;

    for (int i = 0; i < rows.length; i++) {
      final row = rows[i];
      if (row.length < 2) continue;

      final col1 = row[1].toString().trim();

      if (col1 == 'Member:' && row.length > 2) {
        memberName = row[2].toString().trim();
      } else if (col1 == 'Role:' && row.length > 2) {
        role = row[2].toString().trim();
      } else if (col1 == 'Effort Sum:' && row.length > 2) {
        effortSum = double.tryParse(row[2].toString().trim()) ?? 0;
      } else if (col1 == 'No') {
        headerRowIndex = i;
        for (int j = 5; j < row.length; j++) {
          final dateVal = row[j].toString().trim();
          if (dateVal.isNotEmpty) {
            dates.add(_formatDateWithCurrentYear(dateVal));
          }
        }
      }
    }

    if (headerRowIndex == -1 || dates.isEmpty) return null;

    // Task rows start 2 rows after the header row (skip day-of-week row)
    for (int i = headerRowIndex + 2; i < rows.length; i++) {
      final row = rows[i];
      if (row.length < 5) continue;

      final col1 = row[1].toString().trim();
      if (col1 == 'SUM' || col1.isEmpty) continue;

      final taskName = row[2].toString().trim();
      final taskUrl = row[3].toString().trim();

      final taskId = _extractTaskIdFromUrl(taskUrl);

      final List<DayEntry> dayEntries = [];
      for (int j = 0; j < dates.length; j++) {
        final colIndex = j + 5;
        if (colIndex >= row.length) break;
        final hoursVal = double.tryParse(row[colIndex].toString().trim()) ?? 0;
        if (hoursVal > 0) {
          dayEntries.add(DayEntry(date: dates[j], hours: hoursVal));
        }
      }

      dayEntries.sort((a, b) => compareDates(a.date, b.date));

      tasks.add(TaskEntry(
        taskId: taskId,
        taskName: taskName,
        taskUrl: taskUrl,
        dayEntries: dayEntries,
      ));
    }

    return ParsedData(
      memberName: memberName,
      role: role,
      effortSum: effortSum,
      tasks: tasks,
    );
  }

  /// Formats a date string to ensure it has a year (defaults to current year)
  /// e.g. "12" -> "YYYY/MM/12", "12/05" -> "YYYY/12/05" (where 12 is MM, 05 is DD)
  static String _formatDateWithCurrentYear(String dateStr) {
    final parts = dateStr.split(RegExp(r'[/\-]'));
    final now = DateTime.now();

    if (parts.length == 1) {
      final day = int.tryParse(parts[0]);
      if (day != null) {
        return '${now.year}/${now.month.toString().padLeft(2, '0')}/${day.toString().padLeft(2, '0')}';
      }
    } else if (parts.length == 2) {
      // parts[0] is MM, parts[1] is DD
      return '${now.year}/${parts[0].padLeft(2, '0')}/${parts[1].padLeft(2, '0')}';
    }

    return dateStr;
  }

  /// Extracts task ID from URL, e.g. "https://redmine.example.com/issues/17513" → "17513"
  /// Falls back to "" if no numeric ID is found at the end of the URL
  static String _extractTaskIdFromUrl(String url) {
    final match = RegExp(r'/(\d+)$').firstMatch(url);
    return match?.group(1) ?? '';
  }

  static int compareDates(String dateA, String dateB) {
    // Try to parse as DateTime
    DateTime? parseDate(String dateStr) {
      final parts = dateStr.trim().split(RegExp(r'[/\-]'));
      final now = DateTime.now();
      
      if (parts.length == 1) {
        final day = int.tryParse(parts[0]);
        if (day != null) {
          return DateTime(now.year, now.month, day);
        }
      } else if (parts.length == 3) {
        if (parts[0].length == 4) {
          return DateTime.tryParse(
              '${parts[0]}-${parts[1].padLeft(2, '0')}-${parts[2].padLeft(2, '0')}');
        }
        if (parts[2].length == 4) {
          return DateTime.tryParse(
              '${parts[2]}-${parts[0].padLeft(2, '0')}-${parts[1].padLeft(2, '0')}');
        }
      } else if (parts.length == 2) {
        // parts[0] is MM, parts[1] is DD
        return DateTime.tryParse(
            '${now.year}-${parts[0].padLeft(2, '0')}-${parts[1].padLeft(2, '0')}');
      }
      return null;
    }

    final dtA = parseDate(dateA);
    final dtB = parseDate(dateB);
    if (dtA != null && dtB != null) {
      return dtA.compareTo(dtB);
    }

    // Fallback to int comparison
    final aInt = int.tryParse(dateA);
    final bInt = int.tryParse(dateB);
    if (aInt != null && bInt != null) {
      return aInt.compareTo(bInt);
    }

    // Fallback to string comparison
    return dateA.compareTo(dateB);
  }
}
