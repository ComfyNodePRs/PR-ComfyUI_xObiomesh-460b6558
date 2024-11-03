import os
from datetime import datetime

def load_ascii_art(art_type='dolphin'):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    ascii_dir = os.path.join(current_dir, 'ascii')
    art_file = os.path.join(ascii_dir, f'{art_type}.txt')
    
    try:
        with open(art_file, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        # Fallback to dolphin if requested art not found
        default_file = os.path.join(ascii_dir, 'dolphin.txt')
        with open(default_file, 'r', encoding='utf-8') as f:
            return f.read()

def display_init_info(run_count, art_type='dolphin'):
    ascii_art = load_ascii_art(art_type)
    version_line = "\n        >> Neural Nodes by xObiomesh v.0.2.1 <<"
    
    print(ascii_art)
    print(version_line)
    print(f"\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"This script has been run {run_count} times") 