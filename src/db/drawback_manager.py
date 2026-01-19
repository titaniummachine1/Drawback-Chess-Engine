"""
Manager for Drawback knowledge and AI performance statistics.
Tracks how well the AI 'guesses' drawbacks and manages description mappings.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class DrawbackManager:
    """Manages the catalog of known drawbacks and AI proficiency stats."""

    def __init__(self, stats_path: str = None):
        if stats_path is None:
            # Default to data/ directory
            project_root = Path(__file__).parent.parent.parent
            self.stats_path = project_root / "data" / "drawback_stats.json"
        else:
            self.stats_path = Path(stats_path)

        self.stats_path.parent.mkdir(exist_ok=True)
        self.catalog = self._load_stats()

    def _load_stats(self) -> Dict[str, Any]:
        if self.stats_path.exists():
            try:
                with open(self.stats_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load drawback stats: {e}")
        return {}

    def save_stats(self):
        try:
            with open(self.stats_path, "w", encoding="utf-8") as f:
                json.dump(self.catalog, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save drawback stats: {e}")

    def register_drawback(self, name: str, description: str):
        """Add or update a drawback in the catalog."""
        if name not in self.catalog:
            self.catalog[name] = {
                "description": description,
                "first_seen": datetime.now().isoformat(),
                "guess_attempts": 0,
                "guess_correct": 0,
                "difficulty_rank": 0.0,  # 0.0 to 1.0 (internal estimate)
                "accuracy": 0.0
            }
        else:
            # Update description if it was missing or shorter
            if not self.catalog[name]["description"] or len(description) > len(self.catalog[name]["description"]):
                self.catalog[name]["description"] = description

        self.save_stats()

    def record_guess(self, drawback_name: str, is_correct: bool):
        """Record an AI guess result for proficiency tracking."""
        if drawback_name not in self.catalog:
            return

        entry = self.catalog[drawback_name]
        entry["guess_attempts"] += 1
        if is_correct:
            entry["guess_correct"] += 1

        # Update accuracy
        entry["accuracy"] = entry["guess_correct"] / entry["guess_attempts"]

        # If accuracy is very low after many attempts, it signals we need more sensors
        if entry["guess_attempts"] > 50 and entry["accuracy"] < 0.2:
            logger.warning(
                f"AI struggled with '{drawback_name}' (Acc: {entry['accuracy']:.2f}). Consider adding more sensors.")

        self.save_stats()

    def get_worst_performing(self, min_attempts: int = 10) -> List[Dict[str, Any]]:
        """Get drawbacks where AI accuracy is lowest."""
        candidates = []
        for name, data in self.catalog.items():
            if data["guess_attempts"] >= min_attempts:
                candidates.append({"name": name, **data})

        return sorted(candidates, key=lambda x: x["accuracy"])

    def get_summary(self) -> str:
        """Text summary of known drawbacks and AI performance."""
        lines = ["--- Drawback AI Proficiency Report ---"]
        for name, data in self.catalog.items():
            lines.append(
                f"- {name}: Acc {data['accuracy']:.2%} ({data['guess_correct']}/{data['guess_attempts']})")
        return "\n".join(lines)
