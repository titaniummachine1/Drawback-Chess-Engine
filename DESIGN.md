# ♟️ System Design Document: Drawback Chess "Subtractive" AI

## 1. The Core Philosophy: Subtractive Legality

Unlike standard chess bots that calculate legal moves, this bot uses a **Subtractive Model**.

- **The Physics Engine (Fairy-Stockfish):** Generates a list of every "physically possible" move based on a custom variant where King-capture is the goal and moving into check is allowed.
- **The Ingot Brain (AI Mask):** A neural network that generates a **probability mask (0.0 to 1.0)** for every move in the physics list.
- **The Filter:** The bot multiplies the Physics list by the AI Mask. If a move has a low probability of being legal under the current (hidden) drawback, it is pruned from the search.

## 2. The Technical Stack

- **Orchestrator:** Python.
- **Interface:** Playwright (Python library). Intercepts WebSocket JSON packets to find "Ground Truth" (site-highlighted legal moves).
- **Engine:** Fairy-Stockfish using a custom `variants.ini`.
- **Search Algorithm:** MCTS (Monte Carlo Tree Search). Uses Stockfish evals for rollouts and the AI's "Subtractive Mask" for pruning.

## 3. The "Two-Brain" AI Architecture

### Head A: The Physics Head (The Masker)

- **Input:** Current Board (8x8x14) + Drawback Embedding (384D from MiniLM).
- **Output:** Legality Mask (4096-length vector).
- **Goal:** Learn the physical restrictions of ~300+ text-based drawbacks. **Zero hardcoding allowed.**

### Head B: The Detective Head (The Guesser)

- **Input:** Move history of the opponent.
- **Output:** Latent Drawback Vector (pushed into Head A).
- **Goal:** Guess the opponent's drawback.

## 4. Hardware & Efficiency

- **Model:** ResNet-10 backbone (128 filters).
- **Language Encoder:** `all-MiniLM-L6-v2` (22MB).
- **Storage:** Minimal SQLite schema.

## 5. Website Interaction (Playwright)

- **Objective:** Intercept WebSocket packets to find the "Reveal" (Name + Description) and "Truth" (Server legal moves).
- **Interface:** Stealth-enabled browser instances for White and Black.
- **Auto-Learning:** Use the intercepted "Truth" as training targets for the Physics Head.

## 6. Specific Edge Case: King-en-Passant

- **Logic:** Manually inject "Capture King" moves into the `base_moves` list when castling through check is detected.
