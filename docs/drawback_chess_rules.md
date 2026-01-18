# Drawback Chess Rules

## Overview

Drawback Chess is a chess variant where each player has a hidden drawback that affects their legal moves. You cannot see your opponent's drawback, and they cannot see yours. The drawbacks are enforced by the game engine.

## Key Differences from Standard Chess

### Hidden Drawbacks

- Each player has a secret drawback that limits their legal moves
- Drawbacks are not visible to the opponent
- The game engine highlights your legal moves when you interact with pieces
- You cannot make illegal moves - the engine prevents them

### Win Conditions

**Checkmate and stalemate do not exist.** Instead, you win by:

1. **Capturing the opponent's king**
2. **Opponent having no legal moves** (due to their drawback)

### King Safety Rules

- It is **legal** to ignore apparent threats to your king
- It is **legal** to move into check
- It is **legal** to move a piece that's pinned to your king
- Kings may be captured en passant

### Special Castling Rule

If your king castles out of or through check:

- On your opponent's next move, they can capture the king
- Capture is possible by playing any move to:
  - The square the king left (home square)
  - The square the king moved through
  - The square the rook landed on

### Drawback Balance

- Not all drawbacks are equal in difficulty
- Some drawbacks are significantly harder than others
- **Scoring system:**
  - If you have a harder drawback and win → More points
  - If you have a harder drawback and lose → Fewer points lost
  - The stronger player tends to get more significant drawbacks

## Common Drawback Types

### Movement Restrictions

- **No Castling**: Cannot castle at all
- **Knight Immobility**: Knights cannot move
- **Bishop Movement Limit**: Bishops limited to 3 squares per move
- **Rook Restriction**: Rooks cannot move to certain files/ranks

### Capture Restrictions

- **Queen Capture Ban**: Queen cannot capture pieces
- **Pawn Immunity**: Pawns cannot be captured
- **Minor Piece Ban**: Cannot capture bishops or knights

### Special Rules

- **En Passant Forbidden**: En passant captures are illegal
- **Promotion Blocked**: Pawns cannot promote
- **King Mobility Limit**: King limited to adjacent squares only

## Gameplay Implications

### Strategy Differences

- **Material advantage is less important** when opponent has severe drawbacks
- **King safety is not a priority** - kings can be sacrificed
- **Positional play focuses on exploiting opponent's hidden weakness**
- **Pattern recognition** becomes crucial for identifying opponent's drawback

### Detective Element

- Watch opponent's move patterns to guess their drawback
- Some moves are impossible with certain drawbacks
- Use process of elimination to narrow down possibilities
- Bluff by making moves that suggest you have a different drawback

### Endgame Changes

- Traditional endgame theory doesn't apply
- King captures are common and legal
- "Zugzwang" (having no legal moves) is a win condition
- Material down positions can be winning with the right drawback

## Interface Features

### Move Highlighting

- Legal moves are highlighted when you click/pick up pieces
- Only your legal moves (considering your drawback) are shown
- Illegal moves are prevented by the game engine

### Tooltips

- Mouse over highlighted terms for more information:
  - `lose` - How losing conditions work
  - `piece` - Piece movement rules
  - `adjacent` - Square distance definitions
  - `distance` - How distance is calculated
  - `value` - Piece point values
  - `rim` - Edge of the board definitions

## AI Training Considerations

### For the Physics Engine Head

- Must learn which moves are illegal for each drawback type
- Training data includes perfect legal move information
- Uses `legality_mask` as target for supervised learning

### For the Detective Head

- Must learn to identify drawbacks from move patterns
- Training data includes move histories and revealed drawbacks
- Uses `active_drawback_id` as target for classification

### Data Collection Strategy

- Record games without knowing opponent's legal moves
- Capture drawback reveal at game end
- Retroactively reconstruct perfect legal move data
- Create unified training format for both heads

## Scoring and Ranking

### Point System

- Base points for win/loss
- Multiplier based on drawback difficulty difference
- Stronger players get more significant drawbacks (handicap system)

### Ranking Implications

- Players are ranked by performance with various drawbacks
- Adaptive drawback assignment for balanced matches
- Historical performance tracked per drawback type

## Technical Implementation Notes

### Game Engine Requirements

- Must enforce drawback rules for both players
- Must prevent illegal moves based on player's drawback
- Must highlight legal moves for each player individually
- Must handle special king capture rules

### Network Protocol

- Drawback information is hidden during gameplay
- End-of-game packet reveals opponent's drawback
- Move history is transmitted normally
- Legal move validation happens client-side for each player

This variant fundamentally changes chess strategy by adding hidden information and asymmetric rules, making pattern recognition and deduction as important as traditional chess tactics.
