# Implementation Notes for Socket.IO Integration

## Current Issue
The assistant currently uses HTTP polling which doesn't work because:
1. Server returns `success: false` for unauthenticated polling requests
2. Real-time updates come via Socket.IO, not HTTP

## Solution
Playwright's WebSocket/Socket.IO interception doesn't work well. Instead:

**Use the browser's existing Socket.IO connection** by injecting JavaScript that listens to the Socket.IO events and forwards them to our code.

## Implementation Strategy

1. **Inject a Socket.IO listener** into the page that hooks into the existing socket
2. **Forward `update` events** to our Python code via page.evaluate callbacks
3. **Process game state** when we receive updates
4. **Highlight best moves** as before

## Code Pattern

```javascript
// Inject into page
window.__assistantSocketListener = () => {
    // Find the existing socket instance
    const checkForSocket = setInterval(() => {
        // React stores socket in component state
        // We can access it via React DevTools or global scope
        if (window.socket) {
            window.socket.on('update', (data) => {
                window.__lastGameUpdate = data;
                // Trigger callback to Python
            });
            clearInterval(checkForSocket);
        }
    }, 100);
};
```

## Alternative: Direct Socket.IO Connection from Python

Use `python-socketio` library to connect directly:
- Calculate correct port from game ID
- Connect to `wss://www.drawbackchess.com/app{N}/socket.io`
- Emit `join` event with game room
- Listen for `update` events

This is cleaner but requires managing the Socket.IO connection separately from the browser.
