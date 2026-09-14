# Output policy

This document governs wordstat's user-facing behaviour. Changing it is the maintainer's decision.

## Output

- Plain text by default: one `key: value` line per statistic, in a fixed order, `words` first.
- A new statistic is opt-in through a flag, so the default output stays stable.
- A machine-readable format is allowed only behind an explicit flag, and never changes the plain
  text output.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | success |
| 2 | usage error, reported by argparse |
