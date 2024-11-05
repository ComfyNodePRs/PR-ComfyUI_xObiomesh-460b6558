import os
import subprocess
import sys
import logging

def run_web_server():
    try:
        # Get the absolute path to the gallery_server directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Path to the ASCII server script
        server_script = os.path.join(current_dir, 'ascii_server.py')
        
        if not os.path.exists(server_script):
            raise FileNotFoundError(f"Server script not found at: {server_script}")

        # Use Python executable from sys.executable
        python_path = sys.executable
        
        # Start the server process in a new console window
        if os.name == 'nt':  # Windows
            process = subprocess.Popen(
                ['start', 'cmd', '/k', python_path, server_script],
                cwd=current_dir,
                shell=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:  # Linux/Mac
            process = subprocess.Popen(
                ['gnome-terminal', '--', python_path, server_script],
                cwd=current_dir
            )
        
        # Log startup
        logging.info(f"Starting gallery server from: {server_script}")
        logging.info(f"Using Python: {python_path}")
        logging.info(f"Working directory: {current_dir}")
        
        return process
        
    except Exception as e:
        logging.error(f"Error starting gallery server: {str(e)}")
        return None

