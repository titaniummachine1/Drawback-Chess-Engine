import asyncio
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import chess
from playwright.async_api import Page, BrowserContext

class VisualManager:
    def __init__(self, page: Page, board_selector: str):
        self.page = page
        self.board_selector = board_selector
        self.js_template_path = Path(__file__).resolve().parents[1] / "templates" / "js" / "visuals.js"
        self.ui_template_path = Path(__file__).resolve().parents[1] / "templates" / "js" / "ui_panel.js"

    async def inject_visuals(self):
        """Inject the advanced visual overlay system."""
        try:
            is_injected = await self.page.evaluate("() => !!window.assistantAdvanced")
            if is_injected:
                return True

            if not self.js_template_path.exists():
                print(f"[VISUALS] Template missing: {self.js_template_path}")
                return False

            with open(self.js_template_path, "r", encoding="utf-8") as f:
                js_code = f.read().replace('__BOARD_SELECTOR__', self.board_selector)

            await self.page.add_script_tag(content=js_code)
            await asyncio.sleep(0.2)
            
            success = await self.page.evaluate("() => !!window.assistantAdvanced")
            if success:
                print("[VISUALS] Advanced overlay injected")
            return success
        except Exception as e:
            print(f"[VISUALS] Injection error: {e}")
            return False

    async def inject_ui_panel(self):
        """Inject the UI control panel."""
        try:
            is_injected = await self.page.evaluate("() => !!window.assistantUIPanel")
            if is_injected:
                return True

            if not self.ui_template_path.exists():
                return False

            with open(self.ui_template_path, "r", encoding="utf-8") as f:
                js_code = f.read()

            await self.page.add_script_tag(content=js_code)
            print("[VISUALS] UI panel injected")
            return True
        except Exception as e:
            print(f"[VISUALS] UI injection error: {e}")
            return False

    async def clear_all(self):
        """Clear all visual overlays on the board."""
        try:
            await self.page.evaluate("() => window.assistantClearAll && window.assistantClearAll()")
        except:
            pass

    async def highlight_best_move(self, start: str, stop: str):
        """Show best move highlight and arrow."""
        try:
            await self.page.evaluate(f"() => window.assistantHighlightBest && window.assistantHighlightBest('{start}', '{stop}')")
        except Exception as e:
            print(f"[VISUALS] Highlight error: {e}")

    async def show_threats(self, threats: List[Dict]):
        """Show threat arrows."""
        try:
            await self.page.evaluate("(t) => window.assistantShowThreats && window.assistantShowThreats(t)", threats)
        except Exception as e:
            print(f"[VISUALS] Threat display error: {e}")

    async def show_move_qualities(self, quality_data: Dict):
        """Show move quality heatmap."""
        try:
            await self.page.evaluate("(d) => window.assistantShowQualities && window.assistantShowQualities(d)", quality_data)
        except:
            pass

    async def get_selected_square(self) -> Optional[str]:
        """Get the square currently selected by the user."""
        try:
            return await self.page.evaluate("() => window.assistantGetSelectedSquare && window.assistantGetSelectedSquare()")
        except:
            return None

    async def clear_selected_square(self):
        """Reset the selected square flag."""
        try:
            await self.page.evaluate("() => window.assistantClearSelectedSquare && window.assistantClearSelectedSquare()")
        except:
            pass

    async def get_ui_settings(self) -> Optional[Dict]:
        """Get current settings from the UI panel."""
        try:
            return await self.page.evaluate("() => window.assistantGetSettings && window.assistantGetSettings()")
        except:
            return None
