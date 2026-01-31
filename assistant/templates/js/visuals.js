(() => {
  try {
    if (window.assistantAdvanced) return;
    
    const root = document.querySelector('__BOARD_SELECTOR__');
    if (!root) {
      console.error('[ASSIST] Board root not found');
      return;
    }

    // Capture errors for Python debugging
    window.__assistantErrors = "";
    const logError = (msg) => {
        console.error(msg);
        window.__assistantErrors += msg + "\\n";
    };

    const ensureSquareIds = () => {
      const squares = Array.from(root.querySelectorAll('.square'));
      if (!squares.length) return false;
      
      root.style.overflow = 'visible';
      if (root.parentElement) root.parentElement.style.overflow = 'visible';

      const files = ['A','B','C','D','E','F','G','H'];
      for (let idx = 0; idx < squares.length; idx++) {
        const sq = squares[idx];
        if (!sq.dataset.square) {
          const file = files[idx % 8];
          const rank = 8 - Math.floor(idx / 8);
          sq.dataset.square = `${file}${rank}`;
        }
      }
      return true;
    };

    const drawArrow = (fromSq, toSq, color, className) => {
      const fromEl = root.querySelector(`.square[data-square="${fromSq.toUpperCase()}"]`);
      const toEl = root.querySelector(`.square[data-square="${toSq.toUpperCase()}"]`);
      if (!fromEl || !toEl) return;

      const fromRect = fromEl.getBoundingClientRect();
      const toRect = toEl.getBoundingClientRect();
      
      const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.classList.add(className);
      svg.dataset.assistantArrow = 'true';
      svg.style.cssText = `position:fixed; top:0; left:0; width:100%; height:100%; pointer-events:none; z-index:9998;`;
      
      const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
      const markerId = 'arrow-' + color.replace('#', '') + '-' + Math.random().toString(36).substr(2, 9);
      const marker = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
      marker.setAttribute('id', markerId);
      marker.setAttribute('markerWidth', '10');
      marker.setAttribute('markerHeight', '7');
      marker.setAttribute('refX', '9');
      marker.setAttribute('refY', '3.5');
      marker.setAttribute('orient', 'auto');
      
      const poly = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
      poly.setAttribute('points', '0 0, 10 3.5, 0 7');
      poly.setAttribute('fill', color);
      
      marker.appendChild(poly);
      defs.appendChild(marker);
      svg.appendChild(defs);
      
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', fromRect.left + fromRect.width/2);
      line.setAttribute('y1', fromRect.top + fromRect.height/2);
      line.setAttribute('x2', toRect.left + toRect.width/2);
      line.setAttribute('y2', toRect.top + toRect.height/2);
      line.setAttribute('stroke', color);
      line.setAttribute('stroke-width', '5');
      line.setAttribute('marker-end', `url(#${markerId})`);
      line.setAttribute('opacity', '0.8');
      
      svg.appendChild(line);
      document.body.appendChild(svg);
    };

    window.assistantHighlightBest = (start, stop) => {
      ensureSquareIds();
      document.querySelectorAll('.assistant-best-highlight').forEach(el => el.remove());
      document.querySelectorAll('.assistant-best-arrow').forEach(el => el.remove());
      
      drawArrow(start, stop, '#00ff00', 'assistant-best-arrow');
      
      [start, stop].forEach(sqName => {
        const sq = root.querySelector(`.square[data-square="${sqName.toUpperCase()}"]`);
        if (!sq) return;
        
        const hl = document.createElement('div');
        hl.className = 'assistant-best-highlight';
        hl.style.cssText = `position:absolute; inset:0; border:3px solid rgba(0,255,0,0.9); box-shadow:inset 0 0 15px rgba(0,255,0,0.6); pointer-events:none; z-index:10000;`;
        
        // Ensure square is relative for absolute highlight
        if (window.getComputedStyle(sq).position === 'static') {
            sq.style.position = 'relative';
        }
        sq.appendChild(hl);
      });
    };

    window.assistantShowThreats = (threats) => {
      ensureSquareIds();
      document.querySelectorAll('.assistant-threat-arrow').forEach(el => el.remove());
      threats.forEach(t => drawArrow(t.from, t.to, '#ff0000', 'assistant-threat-arrow'));
    };

    window.assistantShowQualities = (qualityData) => {
      ensureSquareIds();
      document.querySelectorAll('.assistant-quality-overlay').forEach(el => el.remove());
      
      for (const [sqName, data] of Object.entries(qualityData)) {
        const sq = root.querySelector(`.square[data-square="${sqName.toUpperCase()}"]`);
        if (!sq) continue;
        
        const overlay = document.createElement('div');
        overlay.className = 'assistant-quality-overlay';
        overlay.style.cssText = `position:absolute; inset:0; background-color:${data.color}; opacity:0.4; pointer-events:none; z-index:9999;`;
        
        if (window.getComputedStyle(sq).position === 'static') {
            sq.style.position = 'relative';
        }
        sq.appendChild(overlay);
      }
    };

    window.assistantClearAll = () => {
      document.querySelectorAll('.assistant-best-highlight, .assistant-best-arrow, .assistant-threat-arrow, .assistant-quality-overlay').forEach(el => el.remove());
    };

    // Selected square tracking for heatmap
    let selectedSquare = null;
    let pendingSelection = null;

    window.assistantGetSelectedSquare = () => {
        const val = pendingSelection;
        return val;
    };

    window.assistantClearSelectedSquare = () => {
        pendingSelection = null;
    };

    root.addEventListener('click', (e) => {
        const sq = e.target.closest('.square');
        if (!sq || !sq.dataset.square) return;
        
        const name = sq.dataset.square;
        const hasPiece = sq.querySelector('[class*="piece"]') || sq.querySelector('img');
        
        if (hasPiece && name !== selectedSquare) {
            selectedSquare = name;
            pendingSelection = name;
        } else {
            selectedSquare = null;
            pendingSelection = null;
            setTimeout(() => window.assistantClearAll(), 400);
        }
    });

    window.assistantAdvanced = true;
    console.log('ASSIST: Visual system ready');
  } catch (err) {
    console.error('[ASSIST] Visual system error:', err);
    window.__assistantErrors = err.message + ' | ' + err.stack;
  }
})();
