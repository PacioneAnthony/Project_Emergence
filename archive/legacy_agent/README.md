# Legacy agent prototype

This directory preserves the pre-J0 cognitive prototype and its tests. It is not part of the active hardware or learning path.

- `main.py` and `sleep.py` are the former wake/sleep entry points.
- `core/` and `sensory/` contain their supporting modules.
- `docs/` records the former ZeroMQ/text-protocol architecture.
- `tests/` are retained for historical reference and excluded from the active pytest suite.

The active physical protocol is EMG1 in `peripheral/brain_stem/` and `j0/`.
