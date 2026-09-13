# taskrail

Agent-agnostic backlog tool: a deterministic CLI that owns the backlog files, plus skills that
execute tasks by kind. See [DESIGN.md](DESIGN.md).

Work in progress — not yet released.

## Development

```bash
uv run pytest                       # all tests
uv run pytest tests/test_validate.py -k cycle   # a single test
uv run taskrail --root <repo> validate
```
