# Workbook layout and findings JSON

`write_log_workbook(output_path, bundle, reviewer, logs, node_version, diagnosis_generated)` writes the workbook. All
of the layout below is computed by the tool; you supply the findings.

## The `logs` argument

One entry per log the scan covered, in the order to show them (logscan's order is fine):

```json
{
  "id": "backend",
  "label": "<label from logscan>",
  "present": true,
  "files": [{"first": "2026/08/13-12:01:08", "last": "2026/08/13-14:31:51"}],
  "totals": {"WARN": 1596, "ERROR": 298, "FATAL": 0},
  "note": "optional line shown on the log's sheet and the Overview",
  "findings": [ ...see below... ]
}
```

A log the bundle lacks: `{"id": "<id>", "label": "<label>", "present": false, "searched": ["<paths logscan looked in>"]}`.
It is listed on the Overview as "Not in bundle" and gets no sheet. Copy `files`, `totals`, `searched` and `label` from
logscan's output.

## A finding

| Field | From | Rule |
|---|---|---|
| `id`, `level`, `pattern`, `count`, `first`, `last`, `first_seen_at`, `excerpt` | logscan, unchanged | `level` is `WARN`, `ERROR` or `FATAL`; `count` a whole number >= 1 |
| `root_cause` | you | Required for `Confirmed` and `Likely`. Optional for `Unknown` |
| `confidence` | you | `Confirmed`, `Likely` or `Unknown` |
| `check_next` | you | A list. Required for `Unknown`: what to look at, and where |
| `mitigation` | you | A list of steps. Required for `Confirmed` and `Likely`. The tool numbers them; do not |
| `notes` | you | Optional: why the confidence is what it is, related finding ids |

A finding is refused (and nothing is written) when its level or confidence is unknown, a `Confirmed`/`Likely` finding
lacks a root cause or mitigation, an `Unknown` one lacks `check_next`, an id repeats, or any text holds an email
address, IP address, credential or licence file name.

## Sheets

- **Overview** (first sheet). Metadata (bundle, node and version, diagnosis date, report date, reviewer). Then
  **Logs scanned**: one row per log with its sheet link, scan result (`Findings`, `Clean` or `Not in bundle`), fatal,
  error and warning totals, and window. Then **Findings**: every finding of every log, FATAL first and by count within
  a level. Columns: Log, Finding, Level, Pattern, Count, Confidence, Likely root cause, Next step, and a `Go to details`
  link to the finding's row on the log's sheet.
- **One sheet per scanned log**, named after the log's label (at most 31 characters). A summary line (window, files,
  totals), then a table with the columns ID, Level, Pattern, Count, First seen, Last seen, Where first seen,
  Masked excerpt, Root cause, Confidence, Check next, and where, Mitigation steps and Notes. A `Back to Overview` link sits at the top. A log with
  no findings has a sheet that says "No errors or warnings found".

The Overview's "Next step" is the first mitigation step for a Confirmed or Likely finding and the checks for an Unknown
one.
