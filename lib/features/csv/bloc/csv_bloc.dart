import 'dart:convert';
import 'package:equatable/equatable.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../models/csv_model.dart';
import '../utils/csv_parser.dart';

part 'csv_event.dart';
part 'csv_state.dart';

class CsvBloc extends Bloc<CsvEvent, CsvState> {
  CsvBloc() : super(const CsvState()) {
    on<_PickFileEvent>(_onPickFileRequested);
    on<_AddTaskEvent>(_onAddTask);
    on<_DeleteTaskEvent>(_onDeleteTask);
    on<_EditTaskEvent>(_onEditTask);
    on<_DeleteDayEntryEvent>(_onDeleteDayEntry);
    on<_AddDayEntryEvent>(_onAddDayEntry);
    on<_EditDayEntryEvent>(_onEditDayEntry);
  }

  Future<void> _onPickFileRequested(
    _PickFileEvent event,
    Emitter<CsvState> emit,
  ) async {
    emit(state.copyWith(status: CsvStatus.loading));

    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['csv'],
        withData: true,
      );

      if (result == null || result.files.isEmpty) {
        emit(state.copyWith(status: CsvStatus.initial));
        return;
      }

      final bytes = result.files.first.bytes;
      if (bytes == null) {
        emit(state.copyWith(
          status: CsvStatus.error,
          errorMessage: 'Cannot read file content.',
        ));
        return;
      }

      final content = utf8.decode(bytes);
      final parsed = CsvParser.parse(content);

      if (parsed == null) {
        emit(state.copyWith(
          status: CsvStatus.error,
          errorMessage: 'Cannot parse CSV. Please check file format.',
        ));
      } else {
        emit(state.copyWith(
          status: CsvStatus.loaded,
          data: parsed,
          tasks: List.of(parsed.tasks),
        ));
      }
    } catch (e) {
      emit(state.copyWith(
        status: CsvStatus.error,
        errorMessage: 'Error: $e',
      ));
    }
  }

  void _onAddTask(
    _AddTaskEvent event,
    Emitter<CsvState> emit,
  ) {
    final tasks = List<TaskEntry>.of(state.tasks ?? [])..add(event.task);
    emit(state.copyWith(tasks: tasks));
  }

  void _onDeleteTask(
    _DeleteTaskEvent event,
    Emitter<CsvState> emit,
  ) {
    final tasks = List<TaskEntry>.of(state.tasks ?? [])
      ..removeAt(event.taskIndex);
    emit(state.copyWith(tasks: tasks));
  }

  void _onEditTask(
    _EditTaskEvent event,
    Emitter<CsvState> emit,
  ) {
    final tasks = List<TaskEntry>.of(state.tasks ?? []);
    tasks[event.taskIndex] = event.task;
    emit(state.copyWith(tasks: tasks));
  }

  void _onDeleteDayEntry(
    _DeleteDayEntryEvent event,
    Emitter<CsvState> emit,
  ) {
    final tasks = List<TaskEntry>.of(state.tasks ?? []);
    final task = tasks[event.taskIndex];
    final dayEntries = List<DayEntry>.of(task.dayEntries)
      ..removeAt(event.dayIndex);
    tasks[event.taskIndex] = TaskEntry(
      taskId: task.taskId,
      taskName: task.taskName,
      taskUrl: task.taskUrl,
      dayEntries: dayEntries,
    );
    emit(state.copyWith(tasks: tasks));
  }

  void _onAddDayEntry(
    _AddDayEntryEvent event,
    Emitter<CsvState> emit,
  ) {
    final tasks = List<TaskEntry>.of(state.tasks ?? []);
    final task = tasks[event.taskIndex];
    final dayEntries = List<DayEntry>.of(task.dayEntries)..add(event.entry);
    dayEntries.sort((a, b) => CsvParser.compareDates(a.date, b.date));
    tasks[event.taskIndex] = TaskEntry(
      taskId: task.taskId,
      taskName: task.taskName,
      taskUrl: task.taskUrl,
      dayEntries: dayEntries,
    );
    emit(state.copyWith(tasks: tasks));
  }

  void _onEditDayEntry(
    _EditDayEntryEvent event,
    Emitter<CsvState> emit,
  ) {
    final tasks = List<TaskEntry>.of(state.tasks ?? []);
    final task = tasks[event.taskIndex];
    final dayEntries = List<DayEntry>.of(task.dayEntries);
    dayEntries[event.dayIndex] = event.entry;
    dayEntries.sort((a, b) => CsvParser.compareDates(a.date, b.date));
    tasks[event.taskIndex] = TaskEntry(
      taskId: task.taskId,
      taskName: task.taskName,
      taskUrl: task.taskUrl,
      dayEntries: dayEntries,
    );
    emit(state.copyWith(tasks: tasks));
  }
}
