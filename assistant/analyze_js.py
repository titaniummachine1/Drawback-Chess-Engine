"""Analyze scraped JavaScript to find API patterns and game logic."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRAPED_DIR = REPO_ROOT / "scraped_drawback_chess"
ANALYSIS_DIR = SCRAPED_DIR / "analysis"
ANALYSIS_DIR.mkdir(exist_ok=True)

def extract_api_endpoints(js_content):
    patterns = [
        r'["\']/(app\d+/)?game["\']',
        r'["\']/(app\d+/)?move["\']',
        r'["\']/(app\d+/)?new_game["\']',
        r'fetch\(["\']([^"\']+)["\']',
        r'axios\.[a-z]+\(["\']([^"\']+)["\']',
        r'\.get\(["\']([^"\']+)["\']',
        r'\.post\(["\']([^"\']+)["\']',
    ]
    
    endpoints = set()
    for pattern in patterns:
        matches = re.findall(pattern, js_content)
        for match in matches:
            if isinstance(match, tuple):
                match = match[-1]
            if match and not match.startswith('http'):
                endpoints.add(match)
    
    return sorted(endpoints)

def extract_websocket_code(js_content):
    ws_patterns = [
        r'new WebSocket\([^)]+\)',
        r'socket\.io[^;]+',
        r'\.on\(["\']([^"\']+)["\'][^)]+\)',
        r'\.emit\(["\']([^"\']+)["\']',
    ]
    
    ws_code = []
    for pattern in ws_patterns:
        matches = re.findall(pattern, js_content)
        ws_code.extend(matches)
    
    return ws_code

def find_game_state_handlers(js_content):
    patterns = [
        r'function\s+\w*[Gg]ame[Ss]tate\w*\s*\([^)]*\)\s*{[^}]{0,500}}',
        r'const\s+\w*[Gg]ame[Ss]tate\w*\s*=',
        r'["\']moves["\']:\s*{',
        r'["\']board["\']:\s*{',
        r'["\']turn["\']:\s*["\']',
        r'legal.*moves',
    ]
    
    handlers = []
    for pattern in patterns:
        matches = re.findall(pattern, js_content, re.IGNORECASE)
        handlers.extend(matches[:10])
    
    return handlers

def analyze_main_js():
    main_js = SCRAPED_DIR / "main.fed58aff.js"
    
    if not main_js.exists():
        print(f"[ERROR] Main JS not found: {main_js}")
        return
    
    print(f"[ANALYZE] Reading {main_js.name} ({main_js.stat().st_size} bytes)")
    content = main_js.read_text(encoding="utf-8")
    
    print("\n=== API Endpoints ===")
    endpoints = extract_api_endpoints(content)
    for ep in endpoints[:20]:
        print(f"  {ep}")
    
    endpoint_file = ANALYSIS_DIR / "api_endpoints.txt"
    endpoint_file.write_text("\n".join(endpoints), encoding="utf-8")
    print(f"\n[SAVED] {len(endpoints)} endpoints to {endpoint_file}")
    
    print("\n=== WebSocket Patterns ===")
    ws_code = extract_websocket_code(content)
    for code in ws_code[:20]:
        print(f"  {code}")
    
    ws_file = ANALYSIS_DIR / "websocket_patterns.txt"
    ws_file.write_text("\n".join(ws_code), encoding="utf-8")
    print(f"\n[SAVED] {len(ws_code)} WebSocket patterns to {ws_file}")
    
    print("\n=== Game State Handlers ===")
    handlers = find_game_state_handlers(content)
    for handler in handlers[:10]:
        snippet = handler[:200].replace("\n", " ")
        print(f"  {snippet}...")
    
    handler_file = ANALYSIS_DIR / "game_state_handlers.txt"
    handler_file.write_text("\n\n".join(handlers), encoding="utf-8")
    print(f"\n[SAVED] {len(handlers)} handlers to {handler_file}")
    
    search_terms = [
        "legal", "moves", "board", "turn", "ply", "game", "state",
        "fetch", "axios", "request", "response", "socket", "emit", "on"
    ]
    
    print("\n=== Searching for key terms ===")
    term_contexts = {}
    for term in search_terms:
        pattern = rf'.{{0,100}}{term}.{{0,100}}'
        matches = re.findall(pattern, content, re.IGNORECASE)
        term_contexts[term] = matches[:50]
        print(f"  {term}: {len(matches)} occurrences")
    
    context_file = ANALYSIS_DIR / "term_contexts.txt"
    with context_file.open("w", encoding="utf-8") as f:
        for term, contexts in term_contexts.items():
            f.write(f"\n\n=== {term.upper()} ===\n")
            for ctx in contexts[:20]:
                f.write(f"{ctx}\n")
    
    print(f"\n[SAVED] Term contexts to {context_file}")
    
    print("\n=== Extracting URL patterns ===")
    url_pattern = r'["\']/([\w/]+)["\']'
    urls = re.findall(url_pattern, content)
    unique_urls = sorted(set(u for u in urls if '/' in u or len(u) > 3))
    
    url_file = ANALYSIS_DIR / "url_patterns.txt"
    url_file.write_text("\n".join(unique_urls), encoding="utf-8")
    print(f"[SAVED] {len(unique_urls)} URL patterns to {url_file}")
    
    for url in unique_urls[:30]:
        print(f"  /{url}")

if __name__ == "__main__":
    analyze_main_js()
