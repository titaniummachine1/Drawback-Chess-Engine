import asyncio
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import chess
from playwright.async_api import Page

class MoveManager:
    def __init__(self, page: Page):
        self.page = page
        self.last_played_move = None
        self.last_played_ply = -1

    async def submit_move(self, game_id: str, color: str, username: str, port: int, uci_move: str, current_ply: int):
        """Submit a move via HTTP POST."""
        if not game_id or not username or not color or not port:
            return False
            
        # Prevent duplicate submissions
        if self.last_played_move == uci_move and self.last_played_ply == current_ply:
            return False
            
        start = uci_move[:2].upper()
        stop = uci_move[2:4].upper()
        promotion = uci_move[4:5].upper() if len(uci_move) > 4 else None
        
        payload = {
            'id': game_id,
            'color': color,
            'username': username,
            'start': start,
            'stop': stop
        }
        if promotion:
            payload['promotion'] = promotion
            
        try:
            print(f"[MOVE] Submitting: {start} -> {stop}")
            url = f"https://www.drawbackchess.com/app{port - 5000}/move"
            response = await self.page.request.post(
                url,
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'}
            )
            
            if response.ok:
                result = await response.json()
                if result.get('success'):
                    print(f"[MOVE] Success: {uci_move}")
                    self.last_played_move = uci_move
                    self.last_played_ply = current_ply
                    return True
                else:
                    error_msg = result.get('error', 'Unknown error')
                    if error_msg:
                        print(f"[MOVE] Rejected: {error_msg}")
            else:
                print(f"[MOVE] HTTP Error: {response.status}")
        except Exception as e:
            print(f"[MOVE] Submission failed: {e}")
            
        return False

    async def auto_join_queue(self, username: str):
        """Join matchmaking queue."""
        if not username:
            return False
            
        try:
            # Check if already in game/queue
            if '/game/' in self.page.url:
                return False
                
            is_queued = await self.page.evaluate("""
                () => !!Array.from(document.querySelectorAll('button'))
                    .find(btn => btn.textContent.includes('Leave Queue'))
            """)
            if is_queued:
                return False
                
            prefs = await self.page.evaluate("""
                () => {
                    let p = localStorage.getItem('time-preference');
                    return {
                        pref: p === 'any' ? null : p,
                        strong: localStorage.getItem('time-preference-is-strong') === 'true'
                    }
                }
            """)
            
            payload = {
                'username': username,
                'timePreference': prefs['pref'],
                'timePreferenceIsStrong': prefs['strong']
            }
            
            response = await self.page.request.post(
                "https://www.drawbackchess.com/join_queue",
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'}
            )
            
            if response.ok:
                result = await response.json()
                if result.get('success') or result.get('error') == 'Already in queue':
                    print("[QUEUE] Joined matchmaking")
                    return True
        except:
            pass
        return False
