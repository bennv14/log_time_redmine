import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:two_dimensional_scrollables/two_dimensional_scrollables.dart';
import '../bloc/csv_bloc.dart';
import '../models/csv_model.dart';
import '../../time_entry/models/time_entry_request.dart';
import '../../time_entry/repositories/time_entry_repository.dart';

DateTime? _parseDateString(String dateStr) {
  final parts = dateStr.trim().split(RegExp(r'[/\-]'));
  final now = DateTime.now();
  
  if (parts.length == 1) {
    final day = int.tryParse(parts[0]);
    if (day != null) {
      return DateTime(now.year, now.month, day);
    }
  }
  
  if (parts.length == 3) {
    if (parts[0].length == 4) {
      // yyyy/MM/dd
      return DateTime.tryParse(
          '${parts[0]}-${parts[1].padLeft(2, '0')}-${parts[2].padLeft(2, '0')}');
    }
    if (parts[2].length == 4) {
      // MM/dd/yyyy
      return DateTime.tryParse(
          '${parts[2]}-${parts[0].padLeft(2, '0')}-${parts[1].padLeft(2, '0')}');
    }
  }
  if (parts.length == 2) {
    // MM/dd
    return DateTime.tryParse(
        '${now.year}-${parts[0].padLeft(2, '0')}-${parts[1].padLeft(2, '0')}');
  }
  return null;
}

String _formatDate(DateTime d) =>
    '${d.year}/${d.month.toString().padLeft(2, '0')}/${d.day.toString().padLeft(2, '0')}';

class CsvScreen extends StatelessWidget {
  const CsvScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (_) => CsvBloc(),
      child: const _CsvView(),
    );
  }
}

class _CsvView extends StatelessWidget {
  const _CsvView();

  Future<void> _showApiKeyDialog(BuildContext context, List<TaskEntry> tasks) async {
    final apiKeyController = TextEditingController();
    bool isLoading = false;

    await showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setState) {
            return AlertDialog(
              title: const Text('Enter Redmine API Key'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text('Please enter your API key to send time entries.'),
                  const SizedBox(height: 16),
                  TextField(
                    controller: apiKeyController,
                    decoration: const InputDecoration(
                      labelText: 'API Key',
                      border: OutlineInputBorder(),
                    ),
                    obscureText: true,
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: isLoading ? null : () => Navigator.pop(ctx),
                  child: const Text('Cancel'),
                ),
                FilledButton(
                  onPressed: isLoading
                      ? null
                      : () async {
                          final apiKey = apiKeyController.text.trim();
                          if (apiKey.isEmpty) return;

                          setState(() => isLoading = true);

                          try {
                            final repository = TimeEntryRepository();
                            final requests = <TimeEntryRequest>[];

                            for (final task in tasks) {
                              final issueId = int.tryParse(task.taskId);
                              if (issueId == null) continue;

                              for (final entry in task.dayEntries) {
                                final dateStr = entry.date.replaceAll('/', '-');
                                
                                requests.add(
                                  TimeEntryRequest(
                                    issueId: issueId,
                                    spentOn: dateStr,
                                    hours: entry.hours,
                                    activityId: 9, // Default to 9 (Development)
                                    comments: task.taskName,
                                  ),
                                );
                              }
                            }

                            if (requests.isEmpty) {
                              throw Exception('No valid time entries to send.');
                            }

                            await repository.createMultipleTimeEntries(
                              requests: requests,
                              apiKey: apiKey,
                            );

                            if (ctx.mounted) {
                              Navigator.pop(ctx);
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(
                                  content: Text('Time entries sent successfully!'),
                                  backgroundColor: Colors.green,
                                ),
                              );
                            }
                          } catch (e) {
                            setState(() => isLoading = false);
                            if (ctx.mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(
                                  content: Text('Error: $e'),
                                  backgroundColor: Colors.red,
                                ),
                              );
                            }
                          }
                        },
                  child: isLoading
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Text('Send'),
                ),
              ],
            );
          }
        );
      },
    );
    apiKeyController.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F7FA),
      appBar: AppBar(
        title: const Text('Time Log Viewer'),
        backgroundColor: const Color(0xFF2C3E50),
        foregroundColor: Colors.white,
        elevation: 0,
        actions: [
          BlocBuilder<CsvBloc, CsvState>(
            builder: (context, state) {
              final isLoading = state.status == CsvStatus.loading;
              final isLoaded = state.status == CsvStatus.loaded;
              
              return Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (isLoaded) ...[
                    FilledButton.icon(
                      onPressed: () => _showApiKeyDialog(context, state.tasks ?? []),
                      icon: const Icon(Icons.send, size: 18),
                      label: const Text('Send API'),
                      style: FilledButton.styleFrom(
                        backgroundColor: const Color(0xFF27AE60),
                      ),
                    ),
                    const SizedBox(width: 8),
                  ],
                  Padding(
                    padding: const EdgeInsets.only(right: 12),
                    child: FilledButton.icon(
                      onPressed: isLoading
                          ? null
                          : () => context
                              .read<CsvBloc>()
                              .add(CsvEvent.pickFile()),
                      icon: isLoading
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                color: Colors.white,
                              ),
                            )
                          : const Icon(Icons.upload_file, size: 18),
                      label: const Text('Import CSV'),
                      style: FilledButton.styleFrom(
                        backgroundColor: const Color(0xFF2980B9),
                      ),
                    ),
                  ),
                ],
              );
            },
          ),
        ],
      ),
      body: BlocBuilder<CsvBloc, CsvState>(
        builder: (context, state) {
          return switch (state.status) {
            CsvStatus.loading => const Center(child: CircularProgressIndicator()),
            CsvStatus.error => _ErrorView(message: state.errorMessage ?? ''),
            CsvStatus.loaded => _ContentView(
                data: state.data!,
                tasks: state.tasks ?? [],
              ),
            CsvStatus.initial => const _EmptyView(),
          };
        },
      ),
    );
  }
}

class _EmptyView extends StatelessWidget {
  const _EmptyView();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.table_chart_outlined,
              size: 80, color: Colors.grey.shade400),
          const SizedBox(height: 20),
          Text(
            'Import a CSV file to view time logs',
            style: TextStyle(
              fontSize: 18,
              color: Colors.grey.shade600,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 24),
          FilledButton.icon(
            onPressed: () =>
                context.read<CsvBloc>().add(CsvEvent.pickFile()),
            icon: const Icon(Icons.upload_file),
            label: const Text('Import CSV'),
            style: FilledButton.styleFrom(
              backgroundColor: const Color(0xFF2980B9),
              padding:
                  const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
            ),
          ),
        ],
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  final String message;
  const _ErrorView({required this.message});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.error_outline, color: Colors.red, size: 48),
          const SizedBox(height: 12),
          Text(message, style: const TextStyle(color: Colors.red)),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: () =>
                context.read<CsvBloc>().add(CsvEvent.pickFile()),
            child: const Text('Try Again'),
          ),
        ],
      ),
    );
  }
}

class _ContentView extends StatefulWidget {
  final ParsedData data;
  final List<TaskEntry> tasks;

  const _ContentView({required this.data, required this.tasks});

  @override
  State<_ContentView> createState() => _ContentViewState();
}

class _ContentViewState extends State<_ContentView> {
  late List<DateTime> _columns;
  
  int? _editingRow;
  int? _editingColumn;
  final TextEditingController _editingController = TextEditingController();
  final FocusNode _editingFocusNode = FocusNode();

  @override
  void initState() {
    super.initState();
    _calculateColumns();
    _editingFocusNode.addListener(_onFocusChange);
  }

  @override
  void didUpdateWidget(covariant _ContentView oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.tasks != oldWidget.tasks) {
      _calculateColumns();
    }
  }

  @override
  void dispose() {
    _editingController.dispose();
    _editingFocusNode.removeListener(_onFocusChange);
    _editingFocusNode.dispose();
    super.dispose();
  }

  void _onFocusChange() {
    if (!_editingFocusNode.hasFocus) {
      _saveEditingCell();
    }
  }

  void _startEditing(int row, int column, String initialValue) {
    setState(() {
      _editingRow = row;
      _editingColumn = column;
      _editingController.text = initialValue;
    });
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _editingFocusNode.requestFocus();
      _editingController.selection = TextSelection(
        baseOffset: 0,
        extentOffset: _editingController.text.length,
      );
    });
  }

  void _saveEditingCell() {
    if (_editingRow == null || _editingColumn == null) return;
    
    final row = _editingRow!;
    final column = _editingColumn!;
    final text = _editingController.text.trim();
    
    // Grab bloc before async/setState
    final bloc = context.read<CsvBloc>();
    
    setState(() {
      _editingRow = null;
      _editingColumn = null;
    });

    final taskIndex = row - 1;
    final task = widget.tasks[taskIndex];
    final date = _columns[column - 1];
    
    final entryIndex = task.dayEntries.indexWhere((e) {
      final d = _parseDateString(e.date);
      return d != null && d.year == date.year && d.month == date.month && d.day == date.day;
    });

    if (text.isEmpty) {
      if (entryIndex >= 0) {
        bloc.add(CsvEvent.deleteDayEntry(taskIndex, entryIndex));
      }
    } else {
      final hours = double.tryParse(text);
      if (hours != null) {
        final entry = DayEntry(date: _formatDate(date), hours: hours);
        if (entryIndex >= 0) {
          bloc.add(CsvEvent.editDayEntry(taskIndex, entryIndex, entry));
        } else {
          bloc.add(CsvEvent.addDayEntry(taskIndex, entry));
        }
      }
    }
  }

  void _calculateColumns() {
    final monthCounts = <String, int>{};
    final allDates = <DateTime>{};

    for (final task in widget.tasks) {
      for (final entry in task.dayEntries) {
        final date = _parseDateString(entry.date);
        if (date != null) {
          final d = DateTime(date.year, date.month, date.day);
          allDates.add(d);
          final monthKey = '${date.year}-${date.month}';
          monthCounts[monthKey] = (monthCounts[monthKey] ?? 0) + 1;
        }
      }
    }

    int targetYear;
    int targetMonth;

    if (monthCounts.isEmpty) {
      final now = DateTime.now();
      targetYear = now.year;
      targetMonth = now.month;
    } else {
      final maxMonthKey = monthCounts.entries
          .reduce((a, b) => a.value > b.value ? a : b)
          .key;
      final parts = maxMonthKey.split('-');
      targetYear = int.parse(parts[0]);
      targetMonth = int.parse(parts[1]);
    }

    final daysInMonth = DateTime(targetYear, targetMonth + 1, 0).day;
    final columnDates = <DateTime>{};
    for (int i = 1; i <= daysInMonth; i++) {
      columnDates.add(DateTime(targetYear, targetMonth, i));
    }

    columnDates.addAll(allDates);
    _columns = columnDates.toList()..sort();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _SummaryBar(data: widget.data),
        Expanded(
          child: ScrollConfiguration(
            behavior: ScrollConfiguration.of(context).copyWith(
              dragDevices: {
                PointerDeviceKind.touch,
                PointerDeviceKind.mouse,
                PointerDeviceKind.trackpad,
              },
            ),
            child: TableView.builder(
              horizontalDetails: const ScrollableDetails(
                direction: AxisDirection.right,
                physics: ClampingScrollPhysics(),
              ),
              verticalDetails: const ScrollableDetails(
                direction: AxisDirection.down,
                physics: ClampingScrollPhysics(),
              ),
            columnCount: _columns.length + 1,
            rowCount: widget.tasks.length + 2,
            pinnedColumnCount: 1,
            pinnedRowCount: 1,
            columnBuilder: (int column) {
              if (column == 0) return const TableSpan(extent: FixedTableSpanExtent(320));
              return const TableSpan(extent: FixedTableSpanExtent(50));
            },
            rowBuilder: (int row) {
              if (row == 0) return const TableSpan(extent: FixedTableSpanExtent(50));
              if (row == widget.tasks.length + 1) return const TableSpan(extent: FixedTableSpanExtent(60));
              return const TableSpan(extent: FixedTableSpanExtent(70));
            },
            cellBuilder: (BuildContext context, TableVicinity vicinity) {
              if (vicinity.row == 0 && vicinity.column == 0) {
                return TableViewCell(
                  child: Container(
                    color: Colors.grey.shade200,
                    alignment: Alignment.center,
                    child: const Text('Task Details', style: TextStyle(fontWeight: FontWeight.bold)),
                  ),
                );
              }
              if (vicinity.row == 0) {
                final date = _columns[vicinity.column - 1];
                final isWeekend = date.weekday == DateTime.saturday || date.weekday == DateTime.sunday;
                final weekdayStr = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][date.weekday - 1];
                return TableViewCell(
                  child: Container(
                    color: isWeekend ? Colors.red.shade50 : Colors.grey.shade200,
                    alignment: Alignment.center,
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text('${date.day}/${date.month}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                        Text(weekdayStr, style: TextStyle(fontSize: 11, color: isWeekend ? Colors.red : Colors.grey.shade700)),
                      ],
                    ),
                  ),
                );
              }
              
              if (vicinity.row == widget.tasks.length + 1) {
                if (vicinity.column == 0) {
                  return TableViewCell(
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        border: Border(
                          right: BorderSide(color: Colors.grey.shade300, width: 1),
                          bottom: BorderSide(color: Colors.grey.shade300, width: 0.5),
                        ),
                      ),
                      child: TextButton.icon(
                        onPressed: () {
                          final newTask = TaskEntry(
                            taskId: '',
                            taskName: 'New Task',
                            taskUrl: '',
                            dayEntries: const [],
                          );
                          context.read<CsvBloc>().add(CsvEvent.addTask(newTask));
                        },
                        icon: const Icon(Icons.add, size: 18),
                        label: const Text('Add Task'),
                        style: TextButton.styleFrom(
                          foregroundColor: const Color(0xFF2980B9),
                        ),
                      ),
                    ),
                  );
                }
                return TableViewCell(
                  child: Container(
                    decoration: BoxDecoration(
                      color: Colors.white,
                      border: Border(
                        right: BorderSide(color: Colors.grey.shade300, width: 0.5),
                        bottom: BorderSide(color: Colors.grey.shade300, width: 0.5),
                      ),
                    ),
                  ),
                );
              }
              
              final taskIndex = vicinity.row - 1;
              final task = widget.tasks[taskIndex];
              
              if (vicinity.column == 0) {
                return TableViewCell(
                  child: _TaskInfoCell(task: task, taskIndex: taskIndex),
                );
              }
              
              final date = _columns[vicinity.column - 1];
              
              // Find if task has entry for this date
              final entryIndex = task.dayEntries.indexWhere((e) {
                final d = _parseDateString(e.date);
                return d != null && d.year == date.year && d.month == date.month && d.day == date.day;
              });
              
              final entry = entryIndex >= 0 ? task.dayEntries[entryIndex] : null;
              final isWeekend = date.weekday == DateTime.saturday || date.weekday == DateTime.sunday;
              
              final isEditing = _editingRow == vicinity.row && _editingColumn == vicinity.column;
              
              return TableViewCell(
                child: isEditing
                    ? Container(
                        decoration: BoxDecoration(
                          color: Colors.white,
                          border: Border.all(color: Colors.blue, width: 2),
                        ),
                        alignment: Alignment.center,
                        child: TextField(
                          controller: _editingController,
                          focusNode: _editingFocusNode,
                          textAlign: TextAlign.center,
                          keyboardType: const TextInputType.numberWithOptions(decimal: true),
                          inputFormatters: [
                            FilteringTextInputFormatter.allow(RegExp(r'^\d*\.?\d*$')),
                          ],
                          style: const TextStyle(
                            color: Color(0xFF2980B9),
                            fontWeight: FontWeight.bold,
                            fontSize: 13,
                          ),
                          decoration: const InputDecoration(
                            border: InputBorder.none,
                            contentPadding: EdgeInsets.zero,
                            isDense: true,
                          ),
                          onSubmitted: (_) => _saveEditingCell(),
                        ),
                      )
                    : InkWell(
                        onTap: () {
                          final initialValue = entry != null
                              ? entry.hours.toStringAsFixed(entry.hours == entry.hours.truncateToDouble() ? 0 : 1)
                              : '';
                          _startEditing(vicinity.row, vicinity.column, initialValue);
                        },
                        child: Container(
                          decoration: BoxDecoration(
                            color: isWeekend ? Colors.red.shade50.withAlpha(100) : Colors.white,
                            border: Border.all(color: Colors.grey.shade300, width: 0.5),
                          ),
                          alignment: Alignment.center,
                          child: entry != null
                              ? Text(
                                  entry.hours.toStringAsFixed(entry.hours == entry.hours.truncateToDouble() ? 0 : 1),
                                  style: const TextStyle(
                                    color: Color(0xFF2980B9),
                                    fontWeight: FontWeight.bold,
                                    fontSize: 13,
                                  ),
                                )
                              : const SizedBox(),
                        ),
                      ),
              );
            },
          ),
          ),
        ),
      ],
    );
  }
}

class _SummaryBar extends StatelessWidget {
  final ParsedData data;
  const _SummaryBar({required this.data});

  @override
  Widget build(BuildContext context) {
    return Container(
      color: const Color(0xFF2C3E50),
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
      child: Wrap(
        spacing: 24,
        runSpacing: 8,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          _SummaryChip(icon: Icons.person, label: data.memberName),
          _SummaryChip(icon: Icons.work_outline, label: data.role),
          _SummaryChip(
            icon: Icons.access_time,
            label: '${data.effortSum.toStringAsFixed(0)}h total',
            highlight: true,
          ),
          _SummaryChip(
            icon: Icons.task_alt,
            label: '${data.tasks.length} tasks',
          ),
        ],
      ),
    );
  }
}

class _SummaryChip extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool highlight;

  const _SummaryChip({
    required this.icon,
    required this.label,
    this.highlight = false,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon,
            size: 16,
            color: highlight ? const Color(0xFFF39C12) : Colors.white70),
        const SizedBox(width: 6),
        Text(
          label,
          style: TextStyle(
            color: highlight ? const Color(0xFFF39C12) : Colors.white,
            fontWeight: highlight ? FontWeight.bold : FontWeight.normal,
            fontSize: 14,
          ),
        ),
      ],
    );
  }
}

class _TaskInfoCell extends StatelessWidget {
  final TaskEntry task;
  final int taskIndex;

  const _TaskInfoCell({required this.task, required this.taskIndex});

  Future<void> _showEditTaskDialog(BuildContext context) async {
    final bloc = context.read<CsvBloc>();
    
    final idController = TextEditingController(text: task.taskId);
    final nameController = TextEditingController(text: task.taskName);
    final urlController = TextEditingController(text: task.taskUrl);

    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Edit Task'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: idController,
              decoration: const InputDecoration(
                labelText: 'Task ID',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: nameController,
              decoration: const InputDecoration(
                labelText: 'Task Name',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: urlController,
              decoration: const InputDecoration(
                labelText: 'Task URL',
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              final newName = nameController.text.trim();
              if (newName.isEmpty) return;

              final updatedTask = TaskEntry(
                taskId: idController.text.trim(),
                taskName: newName,
                taskUrl: urlController.text.trim(),
                dayEntries: task.dayEntries,
              );

              bloc.add(CsvEvent.editTask(taskIndex, updatedTask));
              Navigator.pop(ctx);
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );

    idController.dispose();
    nameController.dispose();
    urlController.dispose();
  }

  Future<void> _openUrl(String url) async {
    final uri = Uri.tryParse(url);
    if (uri != null && await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border(
          right: BorderSide(color: Colors.grey.shade300, width: 1),
          bottom: BorderSide(color: Colors.grey.shade300, width: 0.5),
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 50,
            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
            decoration: BoxDecoration(
              color: const Color(0xFF2980B9).withAlpha(26),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              task.taskId.isNotEmpty ? '#${task.taskId}' : '-',
              style: const TextStyle(
                color: Color(0xFF2980B9),
                fontWeight: FontWeight.bold,
                fontSize: 11,
              ),
              textAlign: TextAlign.center,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  task.taskName,
                  style: const TextStyle(
                    fontWeight: FontWeight.w600,
                    fontSize: 13,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                if (task.taskUrl.isNotEmpty)
                  GestureDetector(
                    onTap: () => _openUrl(task.taskUrl),
                    child: Text(
                      task.taskUrl,
                      style: const TextStyle(
                        color: Color(0xFF2980B9),
                        fontSize: 11,
                        decoration: TextDecoration.underline,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(width: 4),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
            decoration: BoxDecoration(
              color: const Color(0xFF27AE60).withAlpha(26),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
              '${task.totalHours.toStringAsFixed(0)}h',
              style: const TextStyle(
                color: Color(0xFF27AE60),
                fontWeight: FontWeight.bold,
                fontSize: 12,
              ),
            ),
          ),
          const SizedBox(width: 4),
          Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              SizedBox(
                width: 24,
                height: 24,
                child: IconButton(
                  padding: EdgeInsets.zero,
                  onPressed: () => _showEditTaskDialog(context),
                  icon: const Icon(Icons.edit_outlined),
                  iconSize: 16,
                  color: Colors.grey.shade600,
                  tooltip: 'Edit task',
                ),
              ),
              SizedBox(
                width: 24,
                height: 24,
                child: IconButton(
                  padding: EdgeInsets.zero,
                  onPressed: () => context
                      .read<CsvBloc>()
                      .add(CsvEvent.deleteTask(taskIndex)),
                  icon: const Icon(Icons.delete_outline),
                  iconSize: 16,
                  color: Colors.red.shade400,
                  tooltip: 'Delete task',
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}


