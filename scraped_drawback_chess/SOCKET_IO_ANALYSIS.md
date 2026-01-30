# Drawback Chess Socket.IO Analysis

## Connection Setup

The game uses **Socket.IO** for real-time communication.

### Connection Code (from GamePage.js:1022-1028)
```javascript
if (process.env.REACT_APP_LOCAL) {
    setSocket(io.connect(process.env.REACT_APP_FULL_URL))
} else {
    setSocket(io.connect(baseURL, { 
        transports: ['websocket'], 
        path: `/app${port - 5000}/socket.io` 
    }));
}
```

### Port Calculation (from GamePage.js:318-320)
```javascript
function getPort(gameId) {
    return process.env.REACT_APP_LOCAL ? 5001 : 5001 + simpleHash(gameId) % 16;
}
```

**Ports**: 5001-5016 (distributed based on game ID hash)
**Path**: `/app1/socket.io` through `/app16/socket.io`

## Socket.IO Events

### Events the client LISTENS for:

1. **`update`** (GamePage.js:1341-1352)
   - Most important event - receives game state updates
   - Payload: `{ game: {...}, isPremove: bool, premoveFailedBecauseOfHandicap: bool }`
   - Updates the entire game state including board, moves, turn, etc.

2. **`message`** (GamePage.js:1355-1357)
   - Receives messages to display to the user
   - Payload: `{ message: string }`

3. **`other_message`** (GamePage.js:1359-1363)
   - Receives messages about opponent actions
   - Example: `{ message: 'decline_rematch' }`

4. **`rematch`** (GamePage.js:1365-1369)
   - Notification that opponent wants to rematch

5. **`new_player`** (GamePage.js:1371-1383)
   - Notification when a new player joins the game
   - Triggers a full game state fetch via HTTP

6. **`disconnect`** (GamePage.js:1008-1010)
   - Socket disconnection handler

### Events the client EMITS:

1. **`join`** (GamePage.js:1324-1325)
   - Joins game rooms
   - Emitted twice: `{ room: gameId + '-' + username }` and `{ room: gameId }`

2. **`leave`** (GamePage.js:1328-1329)
   - Leaves game rooms when component unmounts

## HTTP API Endpoints

### Game State
- **GET `/game`** - Fetch game state
  - Params: `{ id, color, username, ply? }`
  - Returns: `{ success: bool, game: {...} }`

### Move Submission
- **POST `/move`** - Submit a move
  - Params: `{ id, color, username, start, stop, promotion? }`
  - Returns: `{ success: bool, game: {...} }`

### Premoves
- **POST `/premove`** - Submit a premove
  - Params: `{ id, color, username, start, stop, promotion? }`
  
- **POST `/premove/cancel`** - Cancel premove
  - Params: `{ id, color, username }`

### Other Actions
- **POST `/resign`** - Resign the game
- **POST `/offer_draw`** - Offer a draw
- **POST `/abort`** - Abort the game
- **POST `/rematch`** - Request a rematch

## Game State Structure

The `game` object received from `update` events and HTTP responses contains:

```javascript
{
    id: string,
    board: { [square]: { piece: string, color: string } | null },
    moves: { [square]: [{ stop: string, capture: bool, checking: bool, ... }] },
    turn: 'white' | 'black',
    ply: number,
    scoreSheet: { [moveNum]: [string, string?] },
    result: string | null,
    timer: { white: number, black: number, running: bool },
    handicaps: { white: string, black: string },
    playersInCheck: { white: bool, black: bool },
    premoves: { white: object | null, black: object | null },
    lastMove: { start: string, stop: string } | null,
    // ... many other fields
}
```

## Key Insights for Assistant

1. **Real-time updates come via Socket.IO `update` event**, not HTTP polling
2. **Must connect to the correct port** (5001-5016 based on game ID hash)
3. **Must join the game room** via `socket.emit('join', { room: gameId })`
4. **Legal moves are in `game.moves`** object, keyed by starting square
5. **Move submission is via HTTP POST to `/move`**, not Socket.IO
6. **The `update` event provides the complete game state** after each move
