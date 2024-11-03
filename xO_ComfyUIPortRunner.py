import subprocess
import os
import sys
import shutil

# 🚀 Port Runner for ComfyUI instances
class xO_ComfyUIPortRunner:
    def __init__(self):
        pass
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "port": ("INT", {"default": 8190, "min": 8190, "max": 8199, "step": 1}),
            },
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "run_comfyui"
    CATEGORY = "💦xObiomesh/Utils🛠"
    TITLE = "🚀 ComfyUI Port Runner"

    def run_comfyui(self, port):
        if not (8190 <= port <= 8199):
            return ("Port must be between 8190 and 8199",)

        try:
            # Print current working directory and file location
            current_dir = os.getcwd()
            file_dir = os.path.dirname(__file__)
            print(f"Current working directory: {current_dir}")
            print(f"Script location: {file_dir}")
            
            # Get the ComfyUI root directory
            comfy_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            print(f"Computed ComfyUI root: {comfy_root}")
            
            # Try different possible python executable locations
            python_locations = [
                os.path.join(comfy_root, "python_embedded", "python.exe"),  # Windows standalone
                os.path.join(comfy_root, "env", "Scripts", "python.exe"),   # venv on Windows
            ]
            
            print("Searching for Python in:")
            for loc in python_locations:
                print(f"- {loc} (exists: {os.path.exists(loc)})")
            
            python_exe = None
            for loc in python_locations:
                if os.path.exists(loc):
                    python_exe = loc
                    break
                    
            if not python_exe:
                return ("Error: Could not find Python executable. Searched in:\n" + 
                       "\n".join(f"- {loc}" for loc in python_locations))

            # Look for main.py in different possible locations
            main_locations = [
                os.path.join(comfy_root, "main.py"),                    # Direct in ComfyUI
                os.path.join(comfy_root, "ComfyUI", "main.py"),        # In ComfyUI subdirectory
            ]
            
            main_script = None
            for loc in main_locations:
                if os.path.exists(loc):
                    main_script = loc
                    break
                    
            if not main_script:
                return ("Error: Could not find ComfyUI main.py",)

            # Prepare the command
            cmd = [
                python_exe,
                "-s",
                main_script,
                "--listen",
                "0.0.0.0",
                "--port",
                str(port)
            ]

            # Add windows-standalone-build flag only if using embedded Python
            if "python_embedded" in python_exe:
                cmd.insert(3, "--windows-standalone-build")

            # Run the command
            process = subprocess.Popen(cmd)
            
            return (f"ComfyUI started on port {port}",)
            
        except Exception as e:
            return (f"Error starting ComfyUI: {str(e)}\nTried using Python: {python_exe}\nScript: {main_script}",) 