import time
import sys
import os
import subprocess
import shutil

def main():
    try:
        print("="*50)
        print("Test script started!")
        print(f"Python version: {sys.version}")
        print(f"Python executable: {sys.executable}")
        print("="*50)
        
        # Use exact paths and arguments
        python_exe = r"C:\ComfyUI_windev\python_embeded\python.exe"
        main_script = r"ComfyUI\main.py"
        
        if not os.path.exists(python_exe):
            print(f"Error: Python executable not found at {python_exe}")
            return
            
        # Create the command with exact arguments
        cmd = [
            python_exe,
            "-s",
            main_script,
            "--windows-standalone-build",
            "--listen",
            "0.0.0.0",
            "--port",
            "8188"
        ]
        
        print(f"Running command: {' '.join(cmd)}")
        
        # Start the process in a new shell window
        process = subprocess.Popen(
            cmd,
            creationflags=subprocess.CREATE_NEW_CONSOLE,  # This creates a new console window
            cwd=r"C:\ComfyUI_windev"  # Set the working directory
        )
        
        print("ComfyUI process started! PID:", process.pid)
        print("\nPress Enter to exit...")
        input()  # This will pause the script
            
    except Exception as e:
        print(f"ERROR in test script: {str(e)}")
        import traceback
        print(traceback.format_exc())
        print("\nPress Enter to exit...")
        input()

if __name__ == "__main__":
    main()
    print("Test script exiting!")