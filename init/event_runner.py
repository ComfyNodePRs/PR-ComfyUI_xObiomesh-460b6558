import os
from datetime import datetime
import time as time_module
import sys
import random
from datetime import time as datetime_time
import subprocess
import logging

           

def load_ascii_art(artfile='halo.txt'):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    ascii_dir = os.path.join(current_dir, 'ascii')
    # Only get files ending with '_simple.txt'
    available_arts = [f for f in os.listdir(ascii_dir) if f.endswith('_simple.txt')]
    if not available_arts:
        raise FileNotFoundError("No simple ASCII art files found.")
    
    # Get current time for time-based selection
    current_time = datetime.now().time()
    
    if artfile:
        random_art = f"{artfile}_simple.txt"
    else:
        if current_time < datetime_time(12, 0):  # Before noon
            random_art = 'elephant_simple.txt'
        else:  # Afternoon and evening
            random_art = 'dolphin_simple.txt'
    
    art_file = os.path.join(ascii_dir, random_art)
    
    try:
        with open(art_file, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        # Fallback to any available simple art if specified file doesn't exist
        random_art = random.choice(available_arts)
        art_file = os.path.join(ascii_dir, random_art)
        with open(art_file, 'r', encoding='utf-8') as f:
            return f.read()

def stream_text(text, delay=0.02):
    """Stream text line by line with a delay"""
    for line in text.split('\n'):
        print(line)
        sys.stdout.flush()  # Ensure immediate output
        time_module.sleep(delay)

def display_init_info(run_count, run_count_normalized):
    ascii_art = load_ascii_art()
    version_line = f"\n        >> Neural Nodes by xObiomesh v.0.1.{run_count_normalized} <<"
    stream_text(ascii_art)

    # Stream the additional information
    stream_text(version_line)
    stream_text(f"\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0.01)
    stream_text(f"This script has been run {run_count} times")