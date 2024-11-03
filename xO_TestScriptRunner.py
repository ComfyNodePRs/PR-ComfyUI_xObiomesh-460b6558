import subprocess
import os
import sys
import shutil
import time
import signal
import threading

# 🧪 Test Script Runner
class xO_TestScriptRunner:
    def __init__(self):
        self.process = None
        self.output = []
        self.output_thread = None
        self.running = False
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "action": (["START", "STOP"], {"default": "START"}),
            },
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "run_test_script"
    CATEGORY = "💦xObiomesh/Utils🛠"
    TITLE = "🧪 Test Script Runner"

    def output_reader(self, pipe, prefix=''):
        try:
            while self.running:
                line = pipe.readline()
                if not line:
                    break
                output_line = f"{prefix}{line.strip()}"
                print(output_line)  # Print to ComfyUI console
                self.output.append(output_line)
        except Exception as e:
            print(f"Error reading output: {str(e)}")

    def run_test_script(self, action):
        if action == "STOP":
            return self.stop_script()

        try:
            # Get the script location
            script_dir = os.path.dirname(__file__)
            test_script = os.path.join(script_dir, "xO_runner_test_script.py")
            
            print(f"Current working directory: {os.getcwd()}")
            print(f"Script location: {test_script}")
            
            # Get Python executable (using the same Python that's running ComfyUI)
            python_exe = sys.executable
            
            if not os.path.exists(test_script):
                return (f"Error: Test script not found at {test_script}",)

            # Prepare the command
            cmd = [
                python_exe,
                test_script
            ]

            # Clear previous output
            self.output = []
            self.running = True

            # Run the command with pipe for output
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Start output reader threads
            stdout_thread = threading.Thread(target=self.output_reader, args=(self.process.stdout, ''))
            stderr_thread = threading.Thread(target=self.output_reader, args=(self.process.stderr, 'ERROR: '))
            
            stdout_thread.daemon = True
            stderr_thread.daemon = True
            
            stdout_thread.start()
            stderr_thread.start()
            
            # Wait for a short time to capture initial output
            time.sleep(1)
            
            # Return current output
            current_output = "\n".join(self.output) if self.output else "Script started, waiting for output..."
            return (f"Script running...\n{current_output}",)
            
        except Exception as e:
            self.running = False
            return (f"Error running test script: {str(e)}",)

    def stop_script(self):
        if self.process is None:
            return ("No script is currently running",)
        
        try:
            self.running = False
            if self.process.poll() is None:  # Process is still running
                if os.name == 'nt':  # Windows
                    self.process.terminate()
                else:  # Unix/Linux/Mac
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                
                # Wait a bit to see if it terminated
                time.sleep(0.5)
                
                # Force kill if still running
                if self.process.poll() is None:
                    if os.name == 'nt':
                        self.process.kill()
                    else:
                        os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                
                final_output = "\n".join(self.output) if self.output else "No output captured"
                return (f"Script stopped.\nFinal output:\n{final_output}",)
            else:
                final_output = "\n".join(self.output) if self.output else "No output captured"
                return (f"Script was already completed.\nFinal output:\n{final_output}",)
                
        except Exception as e:
            return (f"Error stopping script: {str(e)}",)
        finally:
            self.process = None
            self.running = False