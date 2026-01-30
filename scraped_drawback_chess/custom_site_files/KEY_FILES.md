# Key Custom Site Files

## Core Game Files

### 1. **GamePage.js** (1863 lines)
Main game component containing:
- Socket.IO connection setup
- Game state management
- Move handling
- Board rendering
- Timer management

**Key Socket.IO code:**
```javascript
// Line 1025-1028: Socket connection
setSocket(io.connect(baseURL, { 
    transports: ['websocket'], 
    path: `/app${port - 5000}/socket.io` 
}));

// Line 1341-1352: Update event handler
socket.on('update', (data) => {
    setGame({
        ...data['game'],
        mostRecentMoveWasPremove: data['isPremove'],
    });
});

// Line 1324-1325: Join game room
socket.emit('join', { room: id + '-' + username });
socket.emit('join', { room: id });
```

### 2. **Square.js**
Individual square component:
- Handles piece dragging
- Move validation
- Legal move highlighting
- Click/drag handlers

### 3. **ChessPiece.js**
Chess piece rendering:
- SVG piece images
- Piece colors and types
- Visual representation

### 4. **Helpers.js**
Utility functions:
- `fetchWrapper()` - HTTP request wrapper
- `getUsername()` - Get current username
- Sound playback functions
- Port calculation

### 5. **Settings.js**
Configuration:
- `baseURL` - API base URL
- Environment variables
- App settings

## Dialog Components

- **GameOverDialog.js** - End game dialog
- **SettingsDialog.js** - Game settings
- **AcceptChallengeDialog.js** - Challenge acceptance
- **HostGameDialog.js** - Host game dialog
- **PlayVsFriendDialog.js** - Friend game setup

## UI Components

- **Timer.js** - Chess clock component
- **MaterialIndicator.js** - Material advantage display
- **PlayerInfo.js** - Player information display
- **Toast.js** - Notification messages
- **ChessNotationText.js** - Chess notation rendering

## Page Components

- **LandingPage.js** - Home/lobby page
- **LeaderboardPage.js** - Rankings
- **MatchHistoryPage.js** - Game history
- **GeneratorPage.js** - Drawback generator
- **DrawbackGlossary.js** - Drawback explanations

## Entry Points

- **App.js** - Main React app component
- **index.js** - React app entry point

## Most Important for Assistant

For implementing the chess assistant, focus on:

1. **GamePage.js** - Lines 1000-1400
   - Socket.IO setup and event handlers
   - Game state structure
   - Move submission logic

2. **Helpers.js**
   - `fetchWrapper()` for HTTP requests
   - Port calculation function

3. **Square.js**
   - How moves are submitted
   - Legal move validation

All files are already beautified and ready to read in:
`c:\GitHubProjekty\drawbackChessAi\scraped_drawback_chess\custom_site_files\`
