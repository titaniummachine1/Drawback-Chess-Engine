(() => {
  try {
    if (window.assistantUIPanel) return;
    
    const panel = document.createElement('div');
    panel.id = 'assistant-ui-panel';
    panel.style.cssText = `
      position: fixed;
      top: 10px;
      right: 10px;
      background: rgba(0, 0, 0, 0.85);
      color: white;
      padding: 15px;
      border-radius: 8px;
      font-family: Arial, sans-serif;
      font-size: 12px;
      z-index: 2147483647 !important;
      min-width: 220px;
      box-shadow: 0 4px 6px rgba(0,0,0,0.3);
      pointer-events: auto !important;
    `;
    
    panel.innerHTML = `
      <div style="font-weight: bold; margin-bottom: 10px; font-size: 14px;">Chess Assistant</div>
      <div style="margin-bottom: 8px;">
        <label><input type="checkbox" id="assist-show-player" checked> Show for Player</label>
      </div>
      <div style="margin-bottom: 8px;">
        <label><input type="checkbox" id="assist-show-opponent"> Show for Opponent</label>
      </div>
      <div style="margin-bottom: 8px;">
        <label><input type="checkbox" id="assist-show-threats" checked> Show Threats</label>
      </div>
      <div style="margin-bottom: 8px;">
        <label><input type="checkbox" id="assist-show-best" checked> Best Move</label>
      </div>
      <div style="margin-bottom: 8px;">
        <label><input type="checkbox" id="assist-show-heatmap"> Heatmap</label>
      </div>
      <div style="margin-bottom: 8px;">
        <label><input type="checkbox" id="assist-auto-play"> Auto-Play</label>
      </div>
      <div style="margin-bottom: 8px;">
        <label><input type="checkbox" id="assist-auto-queue"> Auto-Queue</label>
      </div>
      <div style="margin-top: 12px; padding-top: 8px; border-top: 1px solid #555;">
        <div style="margin-bottom: 4px; font-size: 11px; color: #aaa;">Max Depth: <span id="depth-value">14</span></div>
        <input type="range" id="assist-depth" min="1" max="20" value="14" style="width: 100%;">
      </div>
      <div style="margin-top: 8px;">
        <div style="margin-bottom: 4px; font-size: 11px; color: #aaa;">Max Time: <span id="time-value">2.0</span>s</div>
        <input type="range" id="assist-time" min="0.5" max="10" step="0.5" value="2.0" style="width: 100%;">
      </div>
    `;
    
    document.body.appendChild(panel);

    // Event listeners for UI feedback
    document.getElementById('assist-depth').addEventListener('input', (e) => {
      document.getElementById('depth-value').textContent = e.target.value;
    });
    document.getElementById('assist-time').addEventListener('input', (e) => {
      document.getElementById('time-value').textContent = e.target.value;
    });

    window.assistantGetSettings = () => {
      return {
        showPlayer: document.getElementById('assist-show-player').checked,
        showOpponent: document.getElementById('assist-show-opponent').checked,
        showThreats: document.getElementById('assist-show-threats').checked,
        showBest: document.getElementById('assist-show-best').checked,
        showHeatmap: document.getElementById('assist-show-heatmap').checked,
        autoPlay: document.getElementById('assist-auto-play').checked,
        autoQueue: document.getElementById('assist-auto-queue').checked,
        depth: parseInt(document.getElementById('assist-depth').value),
        time: parseFloat(document.getElementById('assist-time').value)
      };
    };

    window.assistantUIPanel = true;
    console.log('ASSIST: UI system ready');
  } catch (err) {
    console.error('[ASSIST] UI system error:', err);
  }
})();
