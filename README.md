# car_deepagent

Car-related Deep Agent project.

## Overview

Work in progress. More details coming soon.

## Getting Started

```bash
git clone git@github.com:Nioolek/car_deepagent.git
cd car_deepagent
uv sync --extra dev
# ensure .env exists (from .env.example); do not commit .env
```

## Streaming smoke test

With a valid `.env` in the repository root, stream an end-to-end run:

```bash
uv run python scripts/smoke_astream.py --mode single
uv run python scripts/smoke_astream.py --mode multi
uv run python scripts/smoke_astream.py --mode profile
```

`single` analyzes one interview, `multi` compares two interviews, and `profile`
cross-checks one interview against user profile `U001`. Each run prints
LangGraph message and update events as they arrive and uses a stable
mode-specific `thread_id`. Successful document analysis should include `[^...]`
footnote citations and create summary-tree files under
`workspace/cache/summary_trees/`.

## License

TBD
