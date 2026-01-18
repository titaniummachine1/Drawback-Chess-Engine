# Minimal Database Schema for Drawback Chess Engine

## Philosophy

**Store only what cannot be deduced.** The goal is 500MB instead of 5GB by eliminating redundant data while preserving critical legal move information for drawback training.

## Database Choice: SQLite

Single file, ACID compliant, perfect for minimal storage needs.

## Core Schema (3 tables only)

### 1. `games`

Essential game metadata only.

```sql
CREATE TABLE games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE NOT NULL,
    result TEXT,                              -- 'white_win', 'black_win', 'draw'
    opponent_type TEXT,                        -- 'human', 'engine', 'self_play'
    engine_version TEXT,
    total_moves INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. `positions`

Minimal position data with legal moves.

```sql
CREATE TABLE positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL,
    move_number INTEGER NOT NULL,
    fen TEXT NOT NULL,                        -- Position state
    legal_moves TEXT NOT NULL,                 -- JSON: list of legal UCI moves
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (game_id) REFERENCES games (id),
    UNIQUE(game_id, move_number)
);
```

### 3. `drawbacks`

Only store drawback data when detected.

```sql
CREATE TABLE drawbacks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL,
    position_id INTEGER NOT NULL,
    drawback_type TEXT NOT NULL,               -- 'fork', 'pin', 'skewer', etc.
    severity REAL DEFAULT 0.0,                 -- 0.0 to 1.0
    legal_moves_response TEXT NOT NULL,       -- JSON: legal moves available when drawback detected
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (game_id) REFERENCES games (id),
    FOREIGN KEY (position_id) REFERENCES positions (id)
);
```

## Data Storage Format

### Legal Moves JSON Structure

```json
["e2e4", "d2d4", "g1f3", "b1c3"]
```

### Drawback Response JSON Structure

```json
{
  "drawback_type": "fork",
  "severity": 0.8,
  "legal_moves": ["g1f3", "b1c3", "h2h3"],
  "affected_pieces": ["king", "queen"],
  "threat_squares": ["f6", "e5"]
}
```

## What We DON'T Store (deducible or unnecessary)

- ❌ Individual move analysis (time, depth, confidence)
- ❌ Sensor raw data (can be regenerated)
- ❌ Alternative move rankings
- ❌ Position evaluations (can be recalculated)
- ❌ Castling rights (in FEN)
- ❌ En passant info (in FEN)
- ❌ Halfmove/fullmove counters (in FEN)
- ❌ Engine search statistics
- ❌ Training samples (generate on demand)

## Storage Optimization

### Estimated Size Reduction

- **Full schema**: ~5KB per position
- **Minimal schema**: ~200 bytes per position
- **Reduction**: 96% smaller storage

### Compression

- SQLite built-in compression
- Legal moves as simple JSON arrays
- No nested objects or complex structures

## Query Examples

### Get all positions with legal moves

```sql
SELECT p.fen, p.legal_moves, g.result
FROM positions p
JOIN games g ON p.game_id = g.id
WHERE g.result = 'white_win';
```

### Get drawback training data

```sql
SELECT p.fen, p.legal_moves, d.drawback_type, d.severity, d.legal_moves_response
FROM positions p
JOIN drawbacks d ON p.id = d.position_id
WHERE d.severity > 0.5;
```

### Generate training data on demand

```sql
-- This query generates what we used to store permanently
SELECT
    p.fen as position,
    p.legal_moves as legal_moves,
    CASE WHEN d.id IS NOT NULL THEN 1 ELSE 0 END as has_drawback,
    COALESCE(d.drawback_type, '') as drawback_type,
    COALESCE(d.severity, 0.0) as drawback_severity
FROM positions p
LEFT JOIN drawbacks d ON p.id = d.position_id
WHERE p.game_id = ?;
```

## Index Strategy

```sql
CREATE INDEX idx_positions_game_id ON positions(game_id);
CREATE INDEX idx_drawbacks_position_id ON drawbacks(position_id);
CREATE INDEX idx_games_result ON games(result);
```

## Benefits

1. **Size**: 500MB vs 5GB (10x reduction)
2. **Speed**: Faster queries with less data
3. **Simplicity**: Easy to understand and maintain
4. **Flexibility**: Can regenerate complex data when needed
5. **Focus**: Only stores what matters for drawback training

## Usage Pattern

1. **During Game**: Store FEN + legal moves for each position
2. **When Drawback Detected**: Store drawback type, severity, and legal moves available
3. **Training Time**: Generate complex training data from minimal stored data
4. **Analysis**: Reconstruct game state as needed from FEN

This approach gives you the essential legal move information while keeping storage minimal and efficient.
