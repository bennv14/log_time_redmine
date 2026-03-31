import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:url_launcher/url_launcher.dart';
import '../bloc/csv_bloc.dart';
import '../models/csv_model.dart';

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
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: BlocBuilder<CsvBloc, CsvState>(
              buildWhen: (prev, curr) =>
                  prev.status != curr.status &&
                  (curr.status == CsvStatus.loading ||
                      prev.status == CsvStatus.loading),
              builder: (context, state) {
                final isLoading = state.status == CsvStatus.loading;
                return FilledButton.icon(
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
                );
              },
            ),
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

class _ContentView extends StatelessWidget {
  final ParsedData data;
  final List<TaskEntry> tasks;

  const _ContentView({required this.data, required this.tasks});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _SummaryBar(data: data),
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: tasks.length,
            itemBuilder: (context, index) => _TaskCard(
              task: tasks[index],
              taskIndex: index,
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

class _TaskCard extends StatefulWidget {
  final TaskEntry task;
  final int taskIndex;

  const _TaskCard({required this.task, required this.taskIndex});

  @override
  State<_TaskCard> createState() => _TaskCardState();
}

class _TaskCardState extends State<_TaskCard> {
  bool _expanded = true;

  Future<void> _showEditTaskDialog() async {
    final bloc = context.read<CsvBloc>();
    final task = widget.task;

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

              bloc.add(CsvEvent.editTask(widget.taskIndex, updatedTask));
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

  Future<void> _showAddOrEditDialog([int? dayIndex]) async {
    final bloc = context.read<CsvBloc>();
    final existing =
        dayIndex != null ? widget.task.dayEntries[dayIndex] : null;

    DateTime? selectedDate;
    if (existing != null) {
      selectedDate = _parseDateString(existing.date);
    }

    final hoursController = TextEditingController(
      text: existing != null
          ? existing.hours.toStringAsFixed(
              existing.hours == existing.hours.truncateToDouble() ? 0 : 1)
          : '',
    );

    String _formatDate(DateTime d) =>
        '${d.year}/${d.month.toString().padLeft(2, '0')}/${d.day.toString().padLeft(2, '0')}';

    await showDialog<void>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          title: Text(dayIndex != null ? 'Edit Day Entry' : 'Add Day Entry'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              InkWell(
                onTap: () async {
                  final picked = await showDatePicker(
                    context: ctx,
                    initialDate: selectedDate ?? DateTime.now(),
                    firstDate: DateTime(2020),
                    lastDate: DateTime(2030),
                  );
                  if (picked != null) {
                    setDialogState(() => selectedDate = picked);
                  }
                },
                borderRadius: BorderRadius.circular(4),
                child: InputDecorator(
                  decoration: const InputDecoration(
                    labelText: 'Date',
                    border: OutlineInputBorder(),
                    suffixIcon: Icon(Icons.calendar_today, size: 18),
                  ),
                  child: Text(
                    selectedDate != null
                        ? _formatDate(selectedDate!)
                        : (existing?.date.isNotEmpty == true
                            ? existing!.date
                            : 'Select a date'),
                    style: TextStyle(
                      fontSize: 15,
                      color: selectedDate != null || existing?.date.isNotEmpty == true
                          ? null
                          : Colors.grey.shade500,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: hoursController,
                decoration: const InputDecoration(
                  labelText: 'Hours',
                  hintText: 'e.g. 8',
                  border: OutlineInputBorder(),
                  suffixIcon: Icon(Icons.access_time, size: 18),
                ),
                keyboardType:
                    const TextInputType.numberWithOptions(decimal: true),
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
                if (selectedDate == null) return;
                final hours =
                    double.tryParse(hoursController.text.trim()) ?? 0;
                if (hours <= 0) return;
                final entry = DayEntry(
                    date: _formatDate(selectedDate!), hours: hours);
                if (dayIndex != null) {
                  bloc.add(CsvEvent.editDayEntry(
                      widget.taskIndex, dayIndex, entry));
                } else {
                  bloc.add(CsvEvent.addDayEntry(widget.taskIndex, entry));
                }
                Navigator.pop(ctx);
              },
              child: const Text('Save'),
            ),
          ],
        ),
      ),
    );

    hoursController.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final task = widget.task;
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: Colors.grey.shade200),
      ),
      child: Column(
        children: [
          _buildHeader(task),
          if (_expanded) _buildDayList(task),
        ],
      ),
    );
  }

  Widget _buildHeader(TaskEntry task) {
    return InkWell(
      onTap: () => setState(() => _expanded = !_expanded),
      borderRadius: BorderRadius.circular(12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(
                color: const Color(0xFF2980B9).withAlpha(26),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Text(
                task.taskId.isNotEmpty ? '#${task.taskId}' : '-',
                style: const TextStyle(
                  color: Color(0xFF2980B9),
                  fontWeight: FontWeight.bold,
                  fontSize: 13,
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    task.taskName,
                    style: const TextStyle(
                      fontWeight: FontWeight.w600,
                      fontSize: 15,
                    ),
                  ),
                  if (task.taskUrl.isNotEmpty)
                    GestureDetector(
                      onTap: () => _openUrl(task.taskUrl),
                      child: Text(
                        task.taskUrl,
                        style: const TextStyle(
                          color: Color(0xFF2980B9),
                          fontSize: 12,
                          decoration: TextDecoration.underline,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: const Color(0xFF27AE60).withAlpha(26),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Text(
                '${task.totalHours.toStringAsFixed(0)}h',
                style: const TextStyle(
                  color: Color(0xFF27AE60),
                  fontWeight: FontWeight.bold,
                  fontSize: 14,
                ),
              ),
            ),
            const SizedBox(width: 8),
            Icon(
              _expanded ? Icons.expand_less : Icons.expand_more,
              color: Colors.grey.shade500,
            ),
            IconButton(
              onPressed: _showEditTaskDialog,
              icon: const Icon(Icons.edit_outlined),
              iconSize: 20,
              color: Colors.grey.shade600,
              tooltip: 'Edit task',
              splashRadius: 20,
            ),
            IconButton(
              onPressed: () => context
                  .read<CsvBloc>()
                  .add(CsvEvent.deleteTask(widget.taskIndex)),
              icon: const Icon(Icons.delete_outline),
              iconSize: 20,
              color: Colors.red.shade400,
              tooltip: 'Delete task',
              splashRadius: 20,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDayList(TaskEntry task) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.grey.shade50,
        borderRadius: const BorderRadius.only(
          bottomLeft: Radius.circular(12),
          bottomRight: Radius.circular(12),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Divider(height: 1),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                ...task.dayEntries.asMap().entries.map(
                      (e) => _DayChip(
                        entry: e.value,
                        onEdit: () => _showAddOrEditDialog(e.key),
                        onDelete: () => context.read<CsvBloc>().add(
                            CsvEvent.deleteDayEntry(widget.taskIndex, e.key)),
                      ),
                    ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
            child: TextButton.icon(
              onPressed: () => _showAddOrEditDialog(),
              icon: const Icon(Icons.add, size: 16),
              label: const Text('Add Day Entry'),
              style: TextButton.styleFrom(
                foregroundColor: const Color(0xFF2980B9),
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              ),
            ),
          ),
        ],
      ),
    );
  }

  /// Parses date strings in multiple formats:
  /// - yyyy/MM/dd or yyyy-MM-dd
  /// - MM/dd or MM-dd (no year → uses current year)
  /// - MM/dd/yyyy (month first, year last)
  static DateTime? _parseDateString(String dateStr) {
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

  Future<void> _openUrl(String url) async {
    final uri = Uri.tryParse(url);
    if (uri != null && await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }
}

class _DayChip extends StatelessWidget {
  final DayEntry entry;
  final VoidCallback? onEdit;
  final VoidCallback? onDelete;

  const _DayChip({
    required this.entry,
    this.onEdit,
    this.onDelete,
  });

  /// Shows only MM/dd if the entry's year matches the current year,
  /// otherwise shows the full date string.
  String _displayDate(String dateStr) {
    final parts = dateStr.split(RegExp(r'[/\-]'));
    final currentYear = DateTime.now().year;
    if (parts.length == 3 && parts[0].length == 4) {
      final year = int.tryParse(parts[0]);
      if (year == currentYear) {
        final month = int.tryParse(parts[1]) ?? parts[1];
        final day = int.tryParse(parts[2]) ?? parts[2];
        return '$month/$day';
      }
    }
    return dateStr;
  }

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(8),
      child: InkWell(
        onTap: onEdit,
        borderRadius: BorderRadius.circular(8),
        hoverColor: const Color(0xFF2980B9).withAlpha(15),
        child: Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: const Color(0xFF2980B9).withAlpha(80)),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Padding(
                padding: const EdgeInsets.only(
                    left: 10, top: 6, bottom: 6, right: 4),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.edit_outlined,
                      size: 12,
                      color: Colors.grey.shade400,
                    ),
                    const SizedBox(width: 5),
                    Text(
                      _displayDate(entry.date),
                      style: TextStyle(
                        fontSize: 13,
                        color: Colors.grey.shade700,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                        color: const Color(0xFF2980B9).withAlpha(26),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        '${entry.hours.toStringAsFixed(entry.hours == entry.hours.truncateToDouble() ? 0 : 1)}h',
                        style: const TextStyle(
                          fontSize: 13,
                          color: Color(0xFF2980B9),
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                width: 1,
                height: 30,
                color: Colors.grey.shade200,
              ),
              SizedBox(
                width: 30,
                height: 34,
                child: IconButton(
                  padding: EdgeInsets.zero,
                  iconSize: 14,
                  onPressed: onDelete,
                  icon: const Icon(Icons.delete_outline),
                  color: Colors.red.shade300,
                  tooltip: 'Delete',
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

