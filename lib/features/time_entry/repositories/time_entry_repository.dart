import 'package:dio/dio.dart';

import '../models/time_entry_request.dart';

class TimeEntryRepository {
  final Dio _dio;
  final String _baseUrl = 'https://redmine.jprep.jp/redmine';

  TimeEntryRepository({Dio? dio}) : _dio = dio ?? Dio();

  Future<void> createTimeEntry({
    required TimeEntryRequest request,
    required String apiKey,
  }) async {
    try {
      final response = await _dio.post(
        '$_baseUrl/time_entries.json',
        data: request.toJson(),
        options: Options(
          headers: {
            'Content-Type': 'application/json',
            'X-Redmine-API-Key': apiKey,
          },
        ),
      );

      if (response.statusCode != 201) {
        throw Exception(
          'Failed to create time entry. Status code: ${response.statusCode}',
        );
      }
    } on DioException catch (e) {
      throw Exception('Failed to create time entry: ${e.message}');
    } catch (e) {
      throw Exception('An unexpected error occurred: $e');
    }
  }

  Future<void> createMultipleTimeEntries({
    required List<TimeEntryRequest> requests,
    required String apiKey,
  }) async {
    final List<String> errors = [];

    for (int i = 0; i < requests.length; i++) {
      final request = requests[i];
      try {
        await createTimeEntry(request: request, apiKey: apiKey);
      } catch (e) {
        errors.add('Issue ${request.issueId}: $e');
      }
    }

    if (errors.isNotEmpty) {
      throw Exception('Failed to create some time entries:\n${errors.join('\n')}');
    }
  }
}
