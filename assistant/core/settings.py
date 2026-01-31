import json
from pathlib import Path
from typing import Dict, Any

class SettingsManager:
    def __init__(self, settings_file: Path):
        self.settings_file = settings_file
        self.settings = {
            "show_for_player": True,
            "show_for_opponent": False,
            "show_move_quality": False,
            "show_threats": True,
            "show_best_move": True,
            "auto_play": False,
            "auto_queue": False,
            "search_depth": 14,
            "search_time": 2.0
        }
        self.load()

    def load(self):
        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r") as f:
                    self.settings.update(json.load(f))
            except Exception as e:
                print(f"[SETTINGS] Load error: {e}")

    def save(self):
        try:
            with open(self.settings_file, "w") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"[SETTINGS] Save error: {e}")

    def update(self, new_settings: Dict[str, Any]) -> bool:
        changed = False
        for k, v in new_settings.items():
            if k in self.settings and self.settings[k] != v:
                self.settings[k] = v
                changed = True
        if changed:
            self.save()
        return changed
