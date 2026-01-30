"""Extract and beautify only custom site files (exclude node_modules)."""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRAPED_DIR = REPO_ROOT / "scraped_drawback_chess"
SOURCES_DIR = SCRAPED_DIR / "sources"
CUSTOM_DIR = SCRAPED_DIR / "custom_site_files"
CUSTOM_DIR.mkdir(exist_ok=True)

def is_custom_file(filename):
    """Check if file is custom site code (not node_modules)."""
    exclude_patterns = [
        'node_modules',
        '../node_modules',
        'webpack',
        '@emotion',
        '@mui',
        '@babel',
        'react-',
        'stylis',
        'socket.io-parser',
        'engine.io',
        'component-emitter'
    ]
    
    for pattern in exclude_patterns:
        if pattern in filename:
            return False
    
    return True

def beautify_js(content):
    """Basic JavaScript beautification."""
    lines = []
    indent_level = 0
    indent_str = "    "
    
    for line in content.split('\n'):
        stripped = line.strip()
        
        if not stripped:
            lines.append('')
            continue
        
        if stripped.startswith('}') or stripped.startswith(']') or stripped.startswith(')'):
            indent_level = max(0, indent_level - 1)
        
        lines.append(indent_str * indent_level + stripped)
        
        open_braces = stripped.count('{') - stripped.count('}')
        open_brackets = stripped.count('[') - stripped.count(']')
        open_parens = stripped.count('(') - stripped.count(')')
        
        indent_level += open_braces + open_brackets + open_parens
        indent_level = max(0, indent_level)
    
    return '\n'.join(lines)

def extract_custom_files():
    """Extract and beautify custom site files."""
    
    if not SOURCES_DIR.exists():
        print(f"[ERROR] Sources directory not found: {SOURCES_DIR}")
        return
    
    print(f"[EXTRACT] Scanning {SOURCES_DIR} for custom files...")
    
    custom_files = []
    all_files = list(SOURCES_DIR.glob("*.js"))
    
    print(f"[FOUND] {len(all_files)} total files")
    
    for file_path in all_files:
        filename = file_path.name
        
        if is_custom_file(filename):
            custom_files.append(file_path)
    
    print(f"[FILTERED] {len(custom_files)} custom site files (excluded {len(all_files) - len(custom_files)} node_modules)")
    
    manifest = {}
    
    for file_path in sorted(custom_files):
        try:
            content = file_path.read_text(encoding='utf-8')
            
            clean_name = file_path.name
            for prefix in ['node_modules_', '../']:
                clean_name = clean_name.replace(prefix, '')
            
            clean_name = clean_name.replace('_', '/')
            if not clean_name.endswith('.js'):
                clean_name += '.js'
            
            parts = clean_name.split('/')
            if len(parts) > 1:
                subdir = CUSTOM_DIR / '/'.join(parts[:-1])
                subdir.mkdir(parents=True, exist_ok=True)
                output_path = subdir / parts[-1]
            else:
                output_path = CUSTOM_DIR / clean_name
            
            beautified = content
            
            with output_path.open('w', encoding='utf-8') as f:
                f.write(beautified)
            
            manifest[str(output_path.relative_to(CUSTOM_DIR))] = {
                'original': file_path.name,
                'size': len(content),
                'lines': len(content.split('\n'))
            }
            
            print(f"[SAVED] {output_path.relative_to(CUSTOM_DIR)}")
            
        except Exception as e:
            print(f"[ERROR] Failed to process {file_path.name}: {e}")
    
    manifest_path = CUSTOM_DIR / "manifest.json"
    with manifest_path.open('w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"Extracted {len(manifest)} custom site files")
    print(f"Location: {CUSTOM_DIR}")
    print(f"Manifest: {manifest_path}")
    print(f"{'='*60}\n")
    
    print("\nCustom files extracted:")
    for filename in sorted(manifest.keys()):
        print(f"  - {filename}")

if __name__ == "__main__":
    extract_custom_files()
