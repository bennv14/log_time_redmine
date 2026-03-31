part of 'csv_bloc.dart';

enum CsvStatus { initial, loading, loaded, error }

class CsvState {
  final CsvStatus status;
  final ParsedData? data;
  final List<TaskEntry>? tasks;
  final String? errorMessage;

  const CsvState({
    this.status = CsvStatus.initial,
    this.data,
    this.tasks,
    this.errorMessage,
  });

  CsvState copyWith({
    CsvStatus? status,
    ParsedData? data,
    List<TaskEntry>? tasks,
    String? errorMessage,
  }) {
    return CsvState(
      status: status ?? this.status,
      data: data ?? this.data,
      tasks: tasks ?? this.tasks,
      errorMessage: errorMessage ?? this.errorMessage,
    );
  }
}
