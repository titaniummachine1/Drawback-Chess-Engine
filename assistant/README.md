# Drawback Chess Assistant Workspace

This folder hosts tooling that interacts with the live Drawback Chess website. It stays separate from `src/`, which remains focused on training and engine research.

## Goals

1. Capture and replay site interactions (selectors, overlays, UI helpers).
2. Run browser automation for on-board assistance.
3. Keep any Stockfish/eval visualization logic in one place.

## Layout

```
assistant/
├── README.md              # This file
├── data/                  # JSON + assets describing the website surface
├── selector_store.py      # Utility for persisting DOM selectors safely
└── main.py                # CLI entry point for assistant tooling
```

Add new modules here instead of `src/` whenever the code is intended to attach to the official Drawback Chess frontend.
