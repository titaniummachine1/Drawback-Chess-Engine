import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import chess
import chess.engine
from .settings import SettingsManager

class EngineManager:
    def __init__(self, engine_path: Path, variant_config: Dict, settings_mgr: SettingsManager):
        self.engine_path = engine_path
        self.variant_config = variant_config
        self.settings_mgr = settings_mgr
        self.engine = chess.engine.SimpleEngine.popen_uci(str(engine_path))
        self._apply_config()
        self.move_cache = {}
        self.quality_cache = {}

    def _apply_config(self):
        """Apply variant configuration to the engine."""
        if not self.variant_config:
            return
            
        options = {
            "UCI_Variant": "chess",
            "Skill Level": 20
        }
        
        # Extract variant name from VariantConfig object
        variant_name = self.variant_config.get_variant_name()
        if variant_name:
            options["UCI_Variant"] = variant_name
                
        for name, val in options.items():
            try:
                self.engine.configure({name: val})
            except:
                pass

    def score_moves(self, fen: str, uci_moves: List[str]) -> Tuple[Optional[str], float]:
        """Find best move from list using engine."""
        cache_key = f"{fen}:{','.join(sorted(uci_moves))}"
        if cache_key in self.move_cache:
            return self.move_cache[cache_key]
            
        board = chess.Board(fen)
        moves = []
        for m in uci_moves:
            try:
                moves.append(chess.Move.from_uci(m))
            except:
                continue
                
        if not moves:
            return None, 0.0
            
        settings = self.settings_mgr.settings
        limit = chess.engine.Limit(
            depth=settings.get("search_depth", 14),
            time=settings.get("search_time", 2.0)
        )
        
        try:
            info = self.engine.analyse(board, limit, root_moves=moves)
            best = info.get("pv", [None])[0]
            score = info["score"].white().score(mate_score=10000)
            
            result = (best.uci(), float(score)) if best else (None, 0.0)
            self.move_cache[cache_key] = result
            return result
        except Exception as e:
            print(f"[ENGINE] Analysis error: {e}")
            return None, 0.0

    async def evaluate_moves_progressive(self, fen: str, uci_moves: List[str], callback=None) -> Dict[str, float]:
        """Progressive deepening for quality analysis."""
        board = chess.Board(fen)
        moves = []
        for m in uci_moves:
            try:
                moves.append(chess.Move.from_uci(m))
            except:
                continue
                
        if not moves:
            return {}

        results = {}
        settings = self.settings_mgr.settings
        max_depth = settings.get("search_depth", 14)
        
        for depth in [1, 6, max_depth]:
            for move in moves:
                board.push(move)
                limit = chess.engine.Limit(depth=depth)
                info = self.engine.analyse(board, limit)
                score = info["score"].white().score(mate_score=10000)
                results[move.uci()] = float(score)
                board.pop()
            
            if callback:
                await callback(results)
                
        return results

    def close(self):
        try:
            self.engine.close()
        except:
            pass
