# Format of `notes`

Plain text, no markdown. One headline line, then bullets, separated by
newlines, each bullet starting with `• `:

```
<Headline: verdict + impact, ≤ 80 chars>
• <Key fact with the actual value or count, ≤ 80 chars>
• <Key fact or "so what", ≤ 80 chars>
• Action: <one concrete recommendation, ≤ 80 chars>
```

- **Length:** at most 320 characters in total and at most 3 bullets under
  the headline. For **Pass** and **Not Applicable**, use the headline plus at
  most one bullet, ≤ 140 characters in total, unless a calibration requires listing items (e.g. SCALE-008's crash dumps): then ≤ 200.
- **Not Applicable headline:** `Not applicable: <one reason>` (e.g. `Not applicable: no local
  Hugging Face`), never a chain of colons.
- **Self-contained:** carry the decisive values (e.g. `backend.xmx=2g`,
  `4 OOM crashes in 30 days`) so a reader needs nothing else. Do **not**
  include file paths or JSON key dumps; those belong in `evidence_found`.
- **Impact first:** lead with what it means, not how you found it. One idea
  per bullet, fragments rather than sentences, no filler.
- **Cross-references:** a final bullet such as `• See SEC-004 (root cause)`
  when items are causally linked.
- **Needs Review:** the `Action:` bullet must say what to verify and with
  whom, naming a team so the deck can suggest an owner (e.g. `Action: confirm with infra team`,
  `security team`, `platform team`).

Good:

```
Backend heap too small for workload
• backend.xmx=2g on 64GB host
• 4 OOM crashes in 30 days
• Action: raise to 8g+; see PERF-003
```

Bad: method-first prose with file paths, e.g. "In <config file> the backend.xmx key is set to 2g,
and then in the crash dump we found OutOfMemoryError ...".
