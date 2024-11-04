import os
from datetime import datetime
import time as time_module
import sys
import random
from datetime import time as datetime_time
import subprocess
import logging

# Add new function to handle web server
def run_web_server():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    server_script = os.path.join(current_dir, '..', 'library-server', 'ascii_server.py')
    
    # Get path to ComfyUI's Python
    comfy_dir = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
    python_path = os.path.join(comfy_dir, 'python_embeded', 'python.exe')
    
    if not os.path.exists(python_path):
        # Fallback to system Python if embedded not found
        python_path = 'python'
    
    # Log the paths for debugging
    print(f"Current directory: {current_dir}")
    print(f"Server script path: {server_script}")
    print(f"Python path: {python_path}")
    
    try:
        if sys.platform == 'win32':
            # Normalize paths
            server_script = os.path.normpath(server_script)
            python_path = os.path.normpath(python_path)
            
            # Create batch file content
            batch_content = f'''@echo off
echo Starting ComfyUI Gallery Server...
echo.
cd /d "{os.path.dirname(server_script)}"
"{python_path}" -u "{server_script}"
if errorlevel 1 (
    echo.
    echo Server failed to start
    echo Press any key to exit...
    pause >nul
) else (
    echo.
    echo Server stopped normally
    echo Press any key to exit...
    pause >nul
)
'''
            batch_file = os.path.join(os.path.dirname(server_script), 'run_server.bat')
            
            with open(batch_file, 'w', encoding='utf-8') as f:
                f.write(batch_content)
            
            # Run the batch file in a new window
            subprocess.Popen(
                ['cmd', '/c', 'start', 'ComfyUI Gallery Server', '/wait', batch_file],
                shell=True,
                cwd=os.path.dirname(server_script)
            )
        else:
            # Unix-like systems
            if sys.platform == 'darwin':  # macOS
                subprocess.Popen(['open', '-a', 'Terminal', python_path, server_script])
            else:  # Linux
                terminals = ['gnome-terminal', 'xterm', 'konsole']
                for terminal in terminals:
                    try:
                        subprocess.Popen([terminal, '--', python_path, server_script])
                        break
                    except FileNotFoundError:
                        continue

        print("\nStarting ASCII Art server at http://localhost:8200")
        print("The server is running in a new window.")
        print("You can close it by closing the server window.\n")
        
    except Exception as e:
        print(f"Error starting server: {str(e)}")
        logging.error(f"Failed to start server: {str(e)}")

# Modify the display_ascii_art function
def display_ascii_art():
    user_input = input("Press 'y' to display ASCII art files, 'ui' for web interface, or enter to skip: ")
    if user_input.lower() == 'y':
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ascii_dir = os.path.join(current_dir, 'ascii')
        for file in os.listdir(ascii_dir):
            with open(os.path.join(ascii_dir, file), 'r', encoding='utf-8') as f:
                print(f.read())
                input("Press enter to continue...")
    elif user_input.lower() == 'ui':
        run_web_server()

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
    # Stream the ASCII art
    
    # Stream the additional information
    stream_text(version_line)
    stream_text(f"\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0.01)
    stream_text(f"This script has been run {run_count} times")
    input("Press enter to continue...")  # Pause and await user input