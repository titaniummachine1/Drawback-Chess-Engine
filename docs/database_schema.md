# Database Schema Design

## Overview

This database is designed to store comprehensive game data for the Drawback Chess Engine, including:

- Complete game histories
- All legal moves for each position
- Training data for AI improvement

## Database Choice: SQLite + JSON Hybrid

**Primary Storage**: SQLite for structured data and relationships
**Sensor Data**: JSON blobs for flexible sensor information storage

**Rationale**:

- SQLite provides ACID compliance and efficient querying
- JSON allows flexible sensor data structure evolution
- Single file database for easy deployment
- Excellent performance for read-heavy training workloads

## Schema Design

### Tables

#### 1. `games`

Stores high-level game information.

```sql
CREATE TABLE games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE NOT NULL,                    -- Unique game identifier
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    result TEXT,                                   -- 'white_win', 'black_win', 'draw'
    time_control TEXT,                             -- Time control format
    engine_version TEXT,                          -- Engine version used
    opponent_type TEXT,                           -- 'human', 'engine', 'self_play'
    opponent_info TEXT,                           -- JSON: opponent details
    total_moves INTEGER,
    total_time_seconds REAL,
    drawback_analysis TEXT,                       -- JSON: overall drawback summary
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 2. `positions`

Stores each position encountered during games.

```sql
CREATE TABLE positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL,
    move_number INTEGER NOT NULL,                 -- Ply number (1, 2, 3...)
    fen TEXT NOT NULL,                           -- FEN notation
    turn TEXT NOT NULL,                          -- 'white' or 'black'
    castling_rights TEXT,                        -- JSON: {K, Q, k, q}
    en_passant_square TEXT,
    halfmove_clock INTEGER,
    fullmove_number INTEGER,
    position_hash TEXT,                          -- Zobrist hash for deduplication
    evaluation REAL,                             -- Engine evaluation if available
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (game_id) REFERENCES games (id),
    UNIQUE(game_id, move_number)
);
```

#### 3. `legal_moves`

Stores all legal moves for each position.

```sql
CREATE TABLE legal_moves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    position_id INTEGER NOT NULL,
    move_uci TEXT NOT NULL,                      -- UCI notation (e.g., "e2e4")
    move_san TEXT,                               -- Standard algebraic notation
    piece_type TEXT,                             -- Piece being moved
    from_square TEXT NOT NULL,
    to_square TEXT NOT NULL,
    is_capture BOOLEAN DEFAULT FALSE,
    is_promotion BOOLEAN DEFAULT FALSE,
    promotion_piece TEXT,
    is_castling BOOLEAN DEFAULT FALSE,
    is_en_passant BOOLEAN DEFAULT FALSE,
    move_priority REAL DEFAULT 0.0,             -- Engine priority/score
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (position_id) REFERENCES positions (id),
    UNIQUE(position_id, move_uci)
);
```

#### 4. `moves`

Stores the actual moves played in games.

```sql
CREATE TABLE moves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL,
    position_id INTEGER NOT NULL,
    move_number INTEGER NOT NULL,
    move_uci TEXT NOT NULL,
    move_san TEXT,
    time_spent_seconds REAL,                    -- Time taken for this move
    engine_search_depth INTEGER,                 -- Search depth used
    engine_nodes_searched INTEGER,              -- Nodes searched
    engine_confidence REAL,                     -- Confidence in move selection
    was_best_move BOOLEAN DEFAULT FALSE,        -- Was this the engine's top choice?
    alternative_moves TEXT,                     -- JSON: Top N alternative moves
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (game_id) REFERENCES games (id),
    FOREIGN KEY (position_id) REFERENCES positions (id),
    UNIQUE(game_id, move_number)
);
```

#### 5. `sensor_readings`

Stores sensor data for drawback detection.

```sql
CREATE TABLE sensor_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL,
    position_id INTEGER NOT NULL,
    move_id INTEGER,
    sensor_type TEXT NOT NULL,                  -- 'drawback_detector', 'position_evaluator', etc.
    sensor_version TEXT NOT NULL,               -- Version of sensor implementation
    raw_data TEXT NOT NULL,                     -- JSON: Raw sensor output
    processed_data TEXT,                        -- JSON: Processed/interpreted data
    confidence_score REAL,                      -- Sensor confidence (0-1)
    processing_time_ms REAL,                    -- Time to process sensor data
    drawback_detected BOOLEAN DEFAULT FALSE,
    drawback_type TEXT,                         -- Type of drawback detected
    drawback_severity REAL DEFAULT 0.0,         -- Severity score (0-1)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (game_id) REFERENCES games (id),
    FOREIGN KEY (position_id) REFERENCES positions (id),
    FOREIGN KEY (move_id) REFERENCES moves (id)
);
```

#### 6. `training_samples`

Prepared training data for ML model.

```sql
CREATE TABLE training_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL,
    position_id INTEGER NOT NULL,
    input_encoding TEXT NOT NULL,               -- JSON: Encoded position tensor
    target_value REAL,                          -- Game outcome value
    target_policy TEXT NOT NULL,                -- JSON: Move probability distribution
    legal_moves_mask TEXT NOT NULL,             -- JSON: Boolean mask for legal moves
    sensor_features TEXT,                       -- JSON: Sensor-derived features
    sample_weight REAL DEFAULT 1.0,            -- Weight for training
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (game_id) REFERENCES games (id),
    FOREIGN KEY (position_id) REFERENCES positions (id)
);
```

#### 7. `drawback_patterns`

Learned drawback patterns and their effectiveness.

```sql
CREATE TABLE drawback_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_name TEXT NOT NULL,
    pattern_type TEXT NOT NULL,                 -- 'tactical', 'positional', 'timing'
    pattern_signature TEXT NOT NULL,            -- JSON: Pattern signature
    detection_rules TEXT NOT NULL,              -- JSON: Rules for detection
    effectiveness_score REAL DEFAULT 0.0,       -- Historical effectiveness
    usage_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(pattern_name)
);
```

## Indexes

```sql
-- Performance indexes
CREATE INDEX idx_positions_game_id ON positions(game_id);
CREATE INDEX idx_positions_fen ON positions(fen);
CREATE INDEX idx_positions_hash ON positions(position_hash);
CREATE INDEX idx_legal_moves_position_id ON legal_moves(position_id);
CREATE INDEX idx_moves_game_id ON moves(game_id);
CREATE INDEX idx_sensor_readings_game_id ON sensor_readings(game_id);
CREATE INDEX idx_sensor_readings_position_id ON sensor_readings(position_id);
CREATE INDEX idx_training_samples_game_id ON training_samples(game_id);
CREATE INDEX idx_games_started_at ON games(started_at);
CREATE INDEX idx_games_result ON games(result);
```

## Data Storage Strategy

### JSON Schema Examples

#### Sensor Data Structure

```json
{
    "drawback_detector": {
        "version": "1.2.0",
        "raw_output": {
            "attention_map": [[0.1, 0.2, ...], ...],
            "risk_scores": {"e2": 0.8, "f2": 0.6, ...},
            "tactical_threats": ["fork", "pin", "skewer"],
            "positional_weaknesses": ["backward_pawn", "weak_square"]
        },
        "processed": {
            "primary_drawback": "fork_threat",
            "severity": 0.75,
            "affected_pieces": ["king", "queen"],
            "recommended_defense": "move_king_to_safety"
        },
        "confidence": 0.82,
        "processing_time_ms": 12.5
    }
}
```

#### Training Sample Structure

```json
{
    "input_encoding": {
        "board_tensor": [[[0,0,1,0,...], ...], ...],  // 8x8x12 tensor
        "additional_features": [0.1, 0.2, 0.3, ...]
    },
    "target_policy": {
        "move_probabilities": {
            "e2e4": 0.35,
            "d2d4": 0.25,
            "g1f3": 0.20,
            ...
        }
    },
    "legal_moves_mask": {
        "e2e4": true,
        "d2d4": true,
        "f2f4": false,
        ...
    },
    "sensor_features": {
        "drawback_score": 0.3,
        "tactical_complexity": 0.7,
        "position_stability": 0.8,
        ...
    }
}
```

## Query Patterns

### Common Training Queries

```sql
-- Get all positions from winning games
SELECT p.*, m.move_uci, s.raw_data as sensor_data
FROM positions p
JOIN games g ON p.game_id = g.id
LEFT JOIN moves m ON p.id = m.position_id
LEFT JOIN sensor_readings s ON p.id = s.position_id
WHERE g.result = 'white_win' AND p.turn = 'white';

-- Get positions with specific drawback patterns
SELECT p.*, s.processed_data
FROM positions p
JOIN sensor_readings s ON p.id = s.position_id
WHERE s.drawback_detected = true
  AND s.drawback_type = 'fork_threat'
  AND s.confidence_score > 0.8;

-- Extract training samples for specific time period
SELECT * FROM training_samples
WHERE created_at >= '2024-01-01'
  AND sample_weight > 0.5
ORDER BY RANDOM()
LIMIT 10000;
```

## Storage Optimization

### Compression

- Use SQLite's built-in compression for JSON columns
- Consider external storage for very large sensor datasets
- Implement data archiving for old games

### Partitioning Strategy

- Partition by date ranges for large datasets
- Consider sharding by game UUID for distributed setups

### Backup Strategy

- Regular SQLite backups
- Export critical training data to compressed JSON
- Version control for schema changes
