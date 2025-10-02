_load_dotenv_if_present()

CLIENT_ID = os.environ.get("PLANNING_CENTER_CLIENT_ID")
SECRET    = os.environ.get("PLANNING_CENTER_SECRET")
DATE=2025-09-30 EVENT_ID=701347 CLIENT_ID="$PLANNING_CENTER_CLIENT_ID" SECRET="$PLANNING_CENTER_SECRET"; \
NEXT="$(jq -nr --arg d "$DATE" '($d+"T00:00:00Z")|strptime("%Y-%m-%dT%H:%M:%SZ")|mktime+86400|strftime("%Y-%m-%d")')" ; \
EVENT_JSON="$(curl -s -u "$CLIENT_ID:$SECRET" "https://api.planningcenteronline.com/check-ins/v2/events/$EVENT_ID")" ; \
PERIOD_JSON="$(curl -s -u "$CLIENT_ID:$SECRET" "https://api.planningcenteronline.com/check-ins/v2/events/$EVENT_ID/event_periods?where[starts_at][gte]=$DATE&where[starts_at][lt]=$NEXT&order=starts_at&per_page=100")" ; \
PERIOD_ID="$(jq -r '.data[0].id // empty' <<<"$PERIOD_JSON")" ; \
TIMES_JSON="$(
  if [ -n "$PERIOD_ID" ]; then
    curl -s -u "$CLIENT_ID:$SECRET" \
      "https://api.planningcenteronline.com/check-ins/v2/events/$EVENT_ID/event_periods/$PERIOD_ID/event_times?per_page=100&include=headcounts,headcounts.attendance_type"
  else
    printf '{"data":[],"included":[]}'
  fi
)"; \
jq -n --arg date "$DATE" --argjson event "$EVENT_JSON" --argjson period "$PERIOD_JSON" --argjson times "$TIMES_JSON" '
  def headcounts:
    ($times.included // []) | map(select(.type=="Headcount") | {
      id,
      total: (.attributes.total // 0),
      event_time_id: (.relationships.event_time.data.id // null),
      attendance_type_id: (.relationships.attendance_type.data.id // null)
    });
  def att_types:
    ($times.included // []) | map(select(.type=="AttendanceType") | {key: .id, value: (.attributes.name // "")}) | from_entries;
  def times_full:
    ($times.data // []) | map({ id, attributes, headcounts: (headcounts | map(select(.event_time_id == .id))) });
  def totals_by_service:
    times_full | map({ event_time_id: .id, starts_at: (.attributes.starts_at // ""), total: (.headcounts | map(.total) | add // 0) });
  def totals_by_type:
    (headcounts | group_by(.attendance_type_id) | map({
      attendance_type_id: (.[0].attendance_type_id),
      name: (att_types[.[0].attendance_type_id] // ""),
      total: (map(.total) | add // 0)
    }));
  if ($period.data | length) == 0 then
    { event: ($event.data // {}), date: $date, error: "No event_period (session) found for \($date)." }
  else
    {
      event: ($event.data // {}),
      date: $date,
      event_period: ($period.data[0] // null),
      event_times: times_full,
      totals: {
        by_service_time: totals_by_service,
        by_attendance_type: totals_by_type,
        "TOTAL ATTENDANCE": (headcounts | map(.total) | add // 0)
      }
    }
  end

