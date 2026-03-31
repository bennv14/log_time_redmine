part of 'csv_bloc.dart';

abstract class CsvEvent extends Equatable {
  const CsvEvent();

  const factory CsvEvent.pickFile() = _PickFileEvent;
  const factory CsvEvent.addTask(TaskEntry task) = _AddTaskEvent;
  const factory CsvEvent.deleteTask(int taskIndex) = _DeleteTaskEvent;
  const factory CsvEvent.editTask(int taskIndex, TaskEntry task) = _EditTaskEvent;
  const factory CsvEvent.deleteDayEntry(int taskIndex, int dayIndex) =
      _DeleteDayEntryEvent;
  const factory CsvEvent.addDayEntry(int taskIndex, DayEntry entry) =
      _AddDayEntryEvent;
  const factory CsvEvent.editDayEntry(int taskIndex, int dayIndex, DayEntry entry) =
      _EditDayEntryEvent;
}

class _PickFileEvent extends CsvEvent {
  const _PickFileEvent();

  @override
  List<Object?> get props => [];
}

class _AddTaskEvent extends CsvEvent {
  const _AddTaskEvent(this.task);

  final TaskEntry task;

  @override
  List<Object?> get props => [task];
}

class _DeleteTaskEvent extends CsvEvent {
  const _DeleteTaskEvent(this.taskIndex);

  final int taskIndex;

  @override
  List<Object?> get props => [taskIndex];
}

class _EditTaskEvent extends CsvEvent {
  const _EditTaskEvent(this.taskIndex, this.task);

  final int taskIndex;
  final TaskEntry task;

  @override
  List<Object?> get props => [taskIndex, task];
}

class _DeleteDayEntryEvent extends CsvEvent {
  const _DeleteDayEntryEvent(this.taskIndex, this.dayIndex);

  final int taskIndex;
  final int dayIndex;

  @override
  List<Object?> get props => [taskIndex, dayIndex];
}

class _AddDayEntryEvent extends CsvEvent {
  const _AddDayEntryEvent(this.taskIndex, this.entry);

  final int taskIndex;
  final DayEntry entry;

  @override
  List<Object?> get props => [taskIndex, entry];
}

class _EditDayEntryEvent extends CsvEvent {
  const _EditDayEntryEvent(this.taskIndex, this.dayIndex, this.entry);

  final int taskIndex;
  final int dayIndex;
  final DayEntry entry;

  @override
  List<Object?> get props => [taskIndex, dayIndex, entry];
}
