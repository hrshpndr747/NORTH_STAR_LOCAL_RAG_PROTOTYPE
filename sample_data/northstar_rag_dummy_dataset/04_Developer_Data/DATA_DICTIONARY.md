# Developer Data Dictionary

## Confluence page metadata

- `source_id`: stable synthetic source identifier used by the evaluation set.
- `version`: human-readable page version and effective date.
- `review_date`: fictional next review date.
- `labels`: suggested Confluence labels.

## Spreadsheet fields

- `ticket_id`: fictional service ticket identifier.
- `priority`: P1 through P4.
- `resolution_hours`: generated elapsed hours.
- `sla_target_hours`: formula-derived target based on priority.
- `within_sla`: formula-derived Yes/No result.

## SQLite fields

- `service_requests`: 100 dummy records for safe SQL-agent testing.
- `open_service_requests`: read-only view excluding Closed and Resolved status.

All data is fictional and contains no real personal or company information.
