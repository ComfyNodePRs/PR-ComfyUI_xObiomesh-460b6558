import requests
import json
import time
import os
import webbrowser
import base64

class ComfyUIAPI:
    def __init__(self, host="127.0.0.1", port=8188):
        self.base_url = f"http://{host}:{port}"
        
    def check_connection(self, max_retries=30, retry_delay=1):
        """Check if ComfyUI server is responding"""
        print(f"Checking connection to {self.base_url}")
        for i in range(max_retries):
            try:
                response = requests.get(f"{self.base_url}/system_stats")
                if response.status_code == 200:
                    print("Successfully connected to ComfyUI server")
                    return True
                print(f"Attempt {i+1}/{max_retries}: Server not ready (status {response.status_code})")
            except requests.exceptions.ConnectionError:
                print(f"Attempt {i+1}/{max_retries}: Server not responding")
            time.sleep(retry_delay)
        raise Exception(f"Could not connect to ComfyUI server at {self.base_url} after {max_retries} attempts")

    def open_in_browser(self, workflow_data=None):
        """Open ComfyUI in browser with optional workflow"""
        try:
            if workflow_data:
                # Convert workflow to API format first
                api_data = self.prepare_prompt(workflow_data)
                # Encode the API format data
                workflow_json = json.dumps(api_data)
                workflow_b64 = base64.b64encode(workflow_json.encode('utf-8')).decode('utf-8')
                url = f"{self.base_url}/?api={workflow_b64}"
            else:
                url = self.base_url
                
            print(f"Opening ComfyUI in browser: {url}")
            webbrowser.open(url)
        except Exception as e:
            print(f"Warning: Could not open browser: {str(e)}")

    def load_workflow(self, workflow_path):
        """Load a workflow from a JSON file"""
        try:
            with open(workflow_path, 'r') as f:
                workflow_data = json.load(f)
            print(f"Successfully loaded workflow from {workflow_path}")
            
            # Convert workflow to API format
            api_data = self.prepare_prompt(workflow_data)
            
            # Load workflow via API
            url = f"{self.base_url}/load"
            response = requests.post(url, json=api_data)
            response.raise_for_status()
            
            print("Successfully loaded workflow via API")
            return workflow_data
            
        except Exception as e:
            raise Exception(f"Failed to load workflow: {str(e)}")

    def prepare_prompt(self, workflow_data):
        """Convert workflow data to API format"""
        try:
            prompt = {}
            
            # Process nodes
            for node in workflow_data.get("nodes", []):
                node_id = str(node["id"])
                node_data = {
                    "class_type": node["type"],
                    "inputs": {}
                }
                
                # Handle inputs/links
                if "inputs" in node:
                    for input_data in node["inputs"]:
                        input_name = input_data["name"]
                        if "link" in input_data:
                            # Find the corresponding link
                            for link in workflow_data.get("links", []):
                                if link[3] == node["id"] and link[4] == 0:  # Match target node and input index
                                    source_node_id = str(link[1])
                                    source_output_index = link[2]
                                    node_data["inputs"][input_name] = [source_node_id, source_output_index]
                                    break
                
                # Handle widget values
                if "widgets_values" in node:
                    for i, value in enumerate(node["widgets_values"]):
                        node_data["inputs"][f"widget_{i}"] = value
                
                prompt[node_id] = node_data
            
            return {
                "prompt": prompt,
                "client_id": "xObiomesh-workflow-runner"
            }
            
        except Exception as e:
            raise Exception(f"Failed to prepare prompt: {str(e)}")

    def queue_prompt(self, workflow_data):
        """Queue a prompt for execution"""
        try:
            url = f"{self.base_url}/prompt"
            print(f"Queueing prompt to {url}")
            
            # Convert workflow to API format
            api_data = self.prepare_prompt(workflow_data)
            print("Sending API data:")
            print(json.dumps(api_data, indent=2))
            
            response = requests.post(url, json=api_data)
            
            # Print response details if there's an error
            if response.status_code != 200:
                print(f"Error response status: {response.status_code}")
                print("Response headers:", dict(response.headers))
                print("Response content:", response.text)
                response.raise_for_status()
                
            prompt_data = response.json()
            print(f"Successfully queued prompt with ID: {prompt_data.get('prompt_id')}")
            return prompt_data
            
        except Exception as e:
            raise Exception(f"Failed to queue prompt: {str(e)}")

    def get_history(self, prompt_id):
        """Get the history/status of a prompt"""
        try:
            url = f"{self.base_url}/history"
            response = requests.get(url)
            response.raise_for_status()
            history = response.json()
            return history.get(str(prompt_id))
        except Exception as e:
            raise Exception(f"Failed to get history: {str(e)}")

    def get_progress(self):
        """Get current execution progress"""
        try:
            url = f"{self.base_url}/progress"
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting progress: {str(e)}")
            return None

    def wait_for_prompt(self, prompt_id, timeout=300):
        """Wait for a prompt to complete"""
        print(f"Waiting for prompt {prompt_id} to complete (timeout: {timeout}s)")
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Check progress
                progress = self.get_progress()
                if progress:
                    print(f"Progress: {progress.get('value', 0)}% - {progress.get('text', 'Processing...')}")
                
                # Check history
                history = self.get_history(prompt_id)
                if history and "outputs" in history:
                    print(f"Prompt {prompt_id} completed successfully")
                    return history
                    
                time.sleep(1)
            except Exception as e:
                print(f"Error checking prompt status: {str(e)}")
                time.sleep(1)
        raise Exception(f"Timeout waiting for prompt completion after {timeout}s")

    def get_images(self, history_data):
        """Extract image paths from history data"""
        try:
            outputs = history_data.get("outputs", {})
            images = []
            for node_id, node_output in outputs.items():
                if "images" in node_output:
                    for image in node_output["images"]:
                        image_url = f"{self.base_url}/view?filename={image['filename']}"
                        images.append(image_url)
                        print(f"Found image: {image_url}")
            return images
        except Exception as e:
            raise Exception(f"Failed to extract images: {str(e)}")