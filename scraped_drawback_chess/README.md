# Drawback Chess Source Code Analysis

## Successfully Extracted Files

✅ **418 source files** extracted from source map including:
- `GamePage.js` - Main game component with Socket.IO logic
- `ChessPiece.js` - Chess piece rendering
- `Square.js` - Board square logic
- All Socket.IO client libraries
- Complete React component tree

## Key Discoveries

### 1. Socket.IO Architecture

**Connection:**
- Uses Socket.IO (not plain WebSockets)
- Connects to ports 5001-5016 based on game ID hash
- Path: `/app{1-16}/socket.io`

**Critical Event:**
```javascript
socket.on('update', (data) => {
    // Receives complete game state after each move
    // data.game contains: board, moves, turn, ply, etc.
    // data.isPremove indicates if move was a premove
});
```

**Room Joining:**
```javascript
socket.emit('join', { room: gameId });
socket.emit('join', { room: gameId + '-' + username });
```

### 2. Game State Structure

The `game` object from `update` events contains:
- `board`: Object mapping squares (e.g., "A1") to `{piece, color}` or `null`
- `moves`: Object mapping squares to arrays of legal moves
  - Each move: `{stop, capture, checking, inCheck, highlight}`
- `turn`: "white" or "black"
- `ply`: Current half-move number
- `lastMove`: `{start, stop}` of last move
- `result`: Game result or `null`
- `timer`: `{white, black, running}`

### 3. Move Submission

**HTTP POST** to `/move` endpoint:
```javascript
fetchWrapper('/move', {
    id: gameId,
    color: playerColor,
    username: username,
    start: "E2",
    stop: "E4",
    promotion: "Q"  // optional
}, 'POST', port)
```

### 4. Port Calculation

```javascript
function simpleHash(string) {
    let hash = 0;
    for (let i = 0; i < string.length; i++) {
        hash = ((hash << 5) - hash) + string.charCodeAt(i);
        hash = hash & hash;
    }
    while (hash < 0) hash += 2**32;
    return hash;
}

function getPort(gameId) {
    return 5001 + simpleHash(gameId) % 16;  // Returns 5001-5016
}
```

## Why HTTP Polling Failed

1. The server requires authentication cookies
2. Polling requests without proper session return `success: false`
3. Real-time updates are **only sent via Socket.IO**, not HTTP

## Solution for Assistant

### Option 1: Inject Socket.IO Listener (Recommended)
Inject JavaScript into the page that hooks into the existing Socket.IO connection:

```javascript
// Find React's socket instance and listen to it
const reactRoot = document.querySelector('#root');
// Access React internals to get socket
// Forward 'update' events to Python via callbacks
```

### Option 2: Direct Socket.IO Connection
Use `python-socketio` to connect independently:

```python
import socketio

sio = socketio.Client()
port = calculate_port(game_id)
sio.connect(f'https://www.drawbackchess.com', 
            socketio_path=f'/app{port-5000}/socket.io')
sio.emit('join', {'room': game_id})

@sio.on('update')
def on_update(data):
    game_state = data['game']
    # Process game state and highlight best move
```

## Files Location

- **Source files**: `scraped_drawback_chess/sources/`
- **Main game logic**: `sources/GamePage.js`
- **Socket.IO analysis**: `SOCKET_IO_ANALYSIS.md`
- **Source map**: `main.fed58aff.js.map`

## Next Steps

1. Implement Socket.IO listener in the assistant
2. Hook into `update` events to receive game state
3. Remove HTTP polling code
4. Test with live games
