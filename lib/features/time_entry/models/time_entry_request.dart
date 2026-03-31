class TimeEntryRequest {
  final int issueId;
  final String spentOn;
  final double hours;
  final int activityId;
  final String comments;

  TimeEntryRequest({
    required this.issueId,
    required this.spentOn,
    required this.hours,
    required this.activityId,
    this.comments = '',
  });

  Map<String, dynamic> toJson() {
    return {
      'time_entry': {
        'issue_id': issueId,
        'spent_on': spentOn,
        'hours': hours,
        'activity_id': activityId,
        'comments': comments,
      }
    };
  }
}
