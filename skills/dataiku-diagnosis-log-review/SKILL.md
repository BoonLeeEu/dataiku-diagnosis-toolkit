---
name: "dataiku-diagnosis-log-review"
description: "Read the major logs of a Dataiku DSS diagnosis bundle for errors and warnings, work out root causes (or what to check next, and where), give step-by-step mitigations, and write one workbook: an Overview sheet plus one sheet per log. Use when the user asks to analyse, triage or find the cause of errors, warnings, crashes or restarts in a Dataiku diagnosis bundle's logs, or asks for a log review of one."
---

# Dataiku diagnosis log review

Given a Dataiku DSS diagnosis bundle directory, scan its major logs for errors and warnings, explain each finding, say
what to do about it, and write the result to a workbook: an `Overview` sheet summarising every log (with a link from
each finding to its row) and one sheet per log.

This skill holds judgment only: what a finding most likely means and what to do. **How to read the bundle is the
reader's job.** Load the `dataiku-diagnosis-reader` skill first (if skills can't be loaded, read its `SKILL.md` and its
`logs.md` and `limitations.md` references). Do not copy a log format, path or key into this skill; if you
need one the reader lacks, say so in your final summary.

## Reference files (in this skill's `references/` directory)

- `error-catalogue.md` — **read in full before judging any finding.** Known signatures, the cause each points to,
  when the confidence may be Confirmed or only Likely, what to check next, and the mitigation steps.
- `workbook-layout.md` — the findings JSON `write_log_workbook` takes and the sheets it writes.

## 0. Inputs and tools

- Ask for the bundle path and where to save the workbook, nothing else up front. Never write into the plugin
  directory or the bundle. Name the file `<bundle name>_log_review.xlsx`. Keep it, and every intermediate file, outside
  this repository: a workbook holds excerpts from a customer's logs.
- The workbook is written by the review generator's `write_log_workbook` tool (a deferred MCP tool; load its schema
  with ToolSearch before calling it). If the tool is unavailable, say so, give the findings as a table in the
  chat, and stop; do not hand-build the workbook.
- Supply absolute paths to the tool.

## 1. Scan

1. Run the reader's `scripts/orient.sh <bundle>` and note the node type, product version and which logs exist.
2. Run the reader's `scripts/logscan.py <bundle> > <stem>_logscan.json` with `python3 -I`. It streams every log
   (about 20 seconds) and groups errors and warnings by pattern with counts, windows, a `first_seen_at` pointer and a
   masked excerpt. It prints no unmasked log text, and you must not add any: never `cat`, `grep` or `head` a log
   yourself to enrich a finding. If a finding needs more context than its excerpt, point the reader at
   `first_seen_at` in `check_next`.
3. Run the reader's `scripts/facts.py <bundle>` when a judgment depends on settings (heap size, host memory, cgroup
   limits, the node's role). Quote its values; do not re-derive them.

## 2. Judge each finding

For every finding of every log, in this order of effort: FATAL and ERROR first, then WARN.

1. **Match** it to a catalogue entry by signature. A finding matching no entry is judged from its pattern and
   excerpt alone.
2. **Set the confidence** by the entry's own rule, never higher:
   - `Confirmed`: the log text or the facts state the cause outright.
   - `Likely`: the cause is the usual one for this signature and nothing contradicts it, but a check would settle it.
   - `Unknown`: you cannot name a cause. Then `check_next` is mandatory: what to look at, and where (a log, the
     `first_seen_at` line, a setting, a time window).
3. **Write** `root_cause` (one or two sentences, the mechanism, not a restatement of the pattern), `check_next` (one
   action per item, naming the log or setting), and `mitigation` (ordered steps a customer admin can follow, root
   cause before symptoms). Say when a step restarts DSS or needs a maintenance window. Never invent a setting name,
   command or path: if the catalogue and the facts don't give it, write the step as "check the Dataiku documentation
   for <topic> in version <product version>" and keep the confidence at Likely or below.
4. **Correlate across logs.** Lines within a few minutes of each other in different logs are often one incident (a
   process exiting in the process-manager log, a kernel OOM kill, a JVM crash dump, a gap in the backend log). Say so in
   `root_cause` and cite the other finding's id. Kernel messages carry seconds since boot, not wall-clock time, so never
   claim a kernel line and another log "match" on time alone; say what ties them (a process id, a project, a count).
5. **Rank noise honestly.** A finding that is routine noise (the catalogue says which) gets `Confirmed` with the
   mitigation "No action needed" and a note on when it would stop being noise. Do not hide it: absence of noise on the
   workbook reads as absence of logging.

State the window next to any count you quote: a rotated log covers anything from an hour to days.

## 3. Write the workbook

1. Build the findings JSON from `workbook-layout.md`: keep each finding's `id`, `level`, `pattern`, `count`, `first`,
   `last`, `first_seen_at` and `excerpt` **exactly as logscan returned them**, and add `root_cause`, `confidence`,
   `check_next`, `mitigation` and `notes`. Include every scanned log: one with no findings stays in (it gets a sheet that
   says so); one the bundle lacks is passed with `present: false` and its `searched` list.
2. Call `write_log_workbook`. If it refuses a finding because text still looks unmasked, do not edit the text to get
   past the check: drop that finding's excerpt, say so in `notes`, and tell the user the scan's masking missed
   something (name the log and finding id).
3. The tool re-reads the saved file and checks that every Overview link lands on its finding. If it fails, report the
   message; do not patch the file by hand.

## 4. Report back

Give the workbook path, then in at most a short paragraph: how many findings per confidence, the three to five that
matter most (what, where, the first step to take), and which are still Unknown and what would settle each. Always add:

- Masking is best effort. A person must read the excerpts before the workbook leaves the machine.
- The bundle holds no job, scenario-run or audit logs (see the reader's `limitations.md` reference), so errors there
  are not covered; nothing in this workbook shows them absent.
- A log missing from the bundle, or compressed rotations that were skipped (`gz_files_skipped`), narrow what "no
  findings" means; name them.
- A finding judged from a window that ends before an incident cannot confirm or rule it out.

## Secrets

Follow the reader's "Handling secrets" section. Never copy a secret, user name, address or licence file name into any
field; the scan masks them and the tool refuses the common leaks, but you are the last check on `root_cause`,
`check_next`, `mitigation` and `notes`, which you write yourself. Name a user, host or project by the placeholder the
excerpt shows (`<user>`, `<host>`, `<project>`), never by guessing the value.
