import os
import subprocess
import sys
import logging
import signal

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
        
        # Start the server process with hidden console
        if os.name == 'nt':  # Windows
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            # Kill any existing pythonw processes running ascii_server.py
            try:
                subprocess.run(['taskkill', '/F', '/IM', 'pythonw.exe'], 
                             startupinfo=startupinfo,
                             capture_output=True)
            except:
                pass
            
            process = subprocess.Popen(
                ['pythonw', server_script],  # Use pythonw for hidden console
                cwd=current_dir,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        else:  # Linux/Mac
            # Kill any existing server processes
            try:
                subprocess.run(['pkill', '-f', server_script])
            except:
                pass
                
            process = subprocess.Popen(
                [python_path, server_script],
                cwd=current_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setpgrp  # Prevent signal propagation
            )
        
        # Log startup
        logging.info(f"Starting gallery server from: {server_script}")
        logging.info(f"Using Python: {python_path}")
        logging.info(f"Working directory: {current_dir}")
        
        return process
        
    except Exception as e:
        logging.error(f"Error starting gallery server: {str(e)}")
        return None

def stop_server(process):
    if process:
        try:
            if os.name == 'nt':
                process.terminate()
            else:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        except:
            pass

if __name__ == "__main__":
    server_process = run_web_server()
    try:
        if server_process:
            server_process.wait()
    except KeyboardInterrupt:
        stop_server(server_process)

