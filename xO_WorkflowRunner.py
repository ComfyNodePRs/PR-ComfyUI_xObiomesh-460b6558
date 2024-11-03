import os
from .xO_comfyui_api import ComfyUIAPI
import time

class xO_WorkflowRunner:
    def __init__(self):
        self.api = None
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "workflow_path": ("STRING", {"default": r"C:\ComfyUI_windev\ComfyUI\user\default\workflows\text_test.json"}),
                "port": ("INT", {"default": 8188, "min": 8188, "max": 8199, "step": 1}),
                "run": ("BOOLEAN", {"default": False}),
                "open_browser": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "run_workflow"
    CATEGORY = "💦xObiomesh/Utils🛠"
    TITLE = "🔄 Workflow Runner"

    def run_workflow(self, workflow_path, port, run, open_browser):
        if not run:
            return ("Set 'run' to True to execute workflow",)

        try:
            print(f"\n{'='*50}")
            print(f"Starting workflow execution on port {port}")
            print(f"Workflow path: {workflow_path}")
            
            # Initialize API
            self.api = ComfyUIAPI(port=port)
            
            # Check connection to ComfyUI and open browser if requested
            print("Checking connection to ComfyUI server...")
            self.api.check_connection()
            
            # Give the browser time to open
            if open_browser:
                time.sleep(2)
            
            # Check if workflow file exists
            if not os.path.exists(workflow_path):
                return (f"Workflow file not found: {workflow_path}",)
            
            # Load workflow
            print("Loading workflow...")
            workflow_data = self.api.load_workflow(workflow_path)
            
            # Give the browser time to load the workflow
            if open_browser:
                time.sleep(2)
            
            # Queue prompt
            print("Queueing workflow for execution...")
            prompt_response = self.api.queue_prompt(workflow_data)
            prompt_id = prompt_response['prompt_id']
            print(f"Workflow queued with ID: {prompt_id}")
            
            # Wait for completion
            print("Waiting for workflow to complete...")
            history = self.api.wait_for_prompt(prompt_id)
            
            # Get image URLs
            print("Extracting results...")
            images = self.api.get_images(history)
            
            # Format response
            print(f"{'='*50}\n")
            if images:
                return (f"Workflow completed successfully!\nGenerated images:\n" + "\n".join(images),)
            else:
                return ("Workflow completed but no images were generated",)
            
        except Exception as e:
            error_msg = f"Error running workflow: {str(e)}"
            print(f"ERROR: {error_msg}")
            return (error_msg,) 