import os
import logging
from http.server import HTTPServer, SimpleHTTPRequestHandler
import webbrowser
from datetime import datetime
import sys
import json
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
from PIL import Image
import io
import hashlib
from email.utils import formatdate
import socket
import mimetypes
import shutil
from urllib.parse import unquote
import subprocess
import requests
from queue import Queue
import glob
from ollama import Client
from collections import defaultdict

# Configure logging with colors for better visibility
class ColorFormatter(logging.Formatter):
    COLORS = {
        'INFO': '\033[92m',  # Green
        'WARNING': '\033[93m',  # Yellow
        'ERROR': '\033[91m',  # Red
        'CRITICAL': '\033[91m\033[1m',  # Bold Red
        'DEBUG': '\033[94m',  # Blue
        'RESET': '\033[0m'  # Reset
    }

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        formatted_time = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        message = f"{color}{record.msg}{self.COLORS['RESET']}"
        
        # Add to console queue with size limit
        try:
            console_data = {
                'time': formatted_time,
                'level': record.levelname,
                'message': record.msg
            }
            
            # Remove oldest message if queue is full
            if console_queue.full():
                try:
                    console_queue.get_nowait()
                except:
                    pass
            
            console_queue.put(console_data)
            
            # Notify console clients
            dead_clients = set()
            for client in connection_manager.console_clients:
                try:
                    client.write(f"data: {json.dumps(console_data)}\n\n".encode())
                    client.flush()
                except:
                    dead_clients.add(client)
            
            # Remove dead clients
            for client in dead_clients:
                connection_manager.remove_client(client, is_console=True)
                
        except:
            pass
        
        return super().format(record)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Set color formatter
for handler in logging.getLogger().handlers:
    if isinstance(handler, logging.StreamHandler):
        handler.setFormatter(ColorFormatter('%(asctime)s - %(levelname)s - %(message)s'))

# Global variables
MAX_CONSOLE_MESSAGES = 1000
MAX_CLIENTS = 100
CLEANUP_INTERVAL = 300  # 5 minutes

# Add this new class for connection management
class ConnectionManager:
    def __init__(self):
        self.clients = set()
        self.console_clients = set()
        self.last_cleanup = time.time()
        
    def add_client(self, client, is_console=False):
        if is_console:
            self.console_clients.add(client)
        else:
            self.clients.add(client)
        self.cleanup_if_needed()
            
    def remove_client(self, client, is_console=False):
        if is_console:
            self.console_clients.discard(client)
        else:
            self.clients.discard(client)
            
    def cleanup_if_needed(self):
        current_time = time.time()
        if current_time - self.last_cleanup > CLEANUP_INTERVAL:
            self.cleanup_connections()
            self.last_cleanup = current_time
            
    def cleanup_connections(self):
        # Clean up dead connections
        for client_set in [self.clients, self.console_clients]:
            dead_clients = set()
            for client in client_set:
                try:
                    # Try to write a keepalive
                    client.write(b":\n\n")
                    client.flush()
                except:
                    dead_clients.add(client)
            
            # Remove dead clients
            for client in dead_clients:
                client_set.discard(client)
                try:
                    client.close()
                except:
                    pass

# Replace global variables with ConnectionManager
connection_manager = ConnectionManager()
console_queue = Queue(maxsize=MAX_CONSOLE_MESSAGES)

# Add thumbnail configuration
THUMBNAIL_SIZE = (250, 250)  # Size for thumbnails
THUMBNAIL_CACHE_DIR = 'thumbnails'  # Directory to store thumbnails
REFRESH_INTERVAL = 10000  # Minimum time between image list refreshes in ms

# Create thumbnail cache directory if it doesn't exist
if not os.path.exists(THUMBNAIL_CACHE_DIR):
    os.makedirs(THUMBNAIL_CACHE_DIR)

# Store conversation history per client
conversation_histories = defaultdict()

class ImageChangeHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory or not event.src_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            return
            
        try:
            rel_path = os.path.relpath(event.src_path, output_dir).replace('\\', '/')
            logging.info(f"🖼️ New image detected: {os.path.basename(event.src_path)}")
            
            image_data = {
                'path': rel_path,
                'name': os.path.basename(event.src_path),
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            message = f"data: {json.dumps(image_data)}\n\n"
            client_count = len(connection_manager.clients)
            for client in list(connection_manager.clients):
                try:
                    client.write(message.encode())
                    client.flush()
                except:
                    if client in connection_manager.clients:
                        connection_manager.remove_client(client)
                        
            logging.info(f"📤 Notified {client_count} connected clients")
            
        except Exception as e:
            logging.error(f"❌ Error handling new image: {e}")

def generate_thumbnail(image_path):
    """Generate a thumbnail for an image and cache it"""
    try:
        # Ensure thumbnail directory exists
        os.makedirs(THUMBNAIL_CACHE_DIR, exist_ok=True)
        
        # Generate unique thumbnail filename
        mtime = os.path.getmtime(image_path)
        hash_input = f"{image_path}{mtime}".encode('utf-8')
        thumb_filename = hashlib.md5(hash_input).hexdigest() + '.jpg'
        thumb_path = os.path.join(THUMBNAIL_CACHE_DIR, thumb_filename)
        
        # Check if thumbnail exists and is up to date
        if os.path.exists(thumb_path):
            thumb_mtime = os.path.getmtime(thumb_path)
            if thumb_mtime >= mtime:
                return thumb_filename
        
        # Generate new thumbnail
        with Image.open(image_path) as img:
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Calculate aspect ratio
            aspect = img.width / img.height
            if aspect > 1:
                new_width = THUMBNAIL_SIZE[0]
                new_height = int(THUMBNAIL_SIZE[0] / aspect)
            else:
                new_height = THUMBNAIL_SIZE[1]
                new_width = int(THUMBNAIL_SIZE[1] * aspect)
            
            # Resize with proper aspect ratio
            img.thumbnail((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Create background
            thumb = Image.new('RGB', THUMBNAIL_SIZE, (0, 0, 0))
            # Paste resized image centered
            x = (THUMBNAIL_SIZE[0] - new_width) // 2
            y = (THUMBNAIL_SIZE[1] - new_height) // 2
            thumb.paste(img, (x, y))
            
            # Save with optimization
            thumb.save(thumb_path, 'JPEG', quality=85, optimize=True)
            logging.info(f"Generated thumbnail: {thumb_path}")
            
        return thumb_filename
        
    except Exception as e:
        logging.error(f"Error generating thumbnail for {image_path}: {str(e)}")
        return None

def get_image_list():
    """Get list of images in output directory"""
    images = []
    try:
        for root, _, files in os.walk(output_dir):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, output_dir).replace('\\', '/')
                    
                    # Generate thumbnail
                    thumb_filename = generate_thumbnail(full_path)
                    
                    images.append({
                        'path': rel_path,
                        'name': file,
                        'date': datetime.fromtimestamp(os.path.getmtime(full_path)).strftime('%Y-%m-%d %H:%M:%S'),
                        'thumbnail': f'/thumbnails/{thumb_filename}' if thumb_filename else None
                    })
        return sorted(images, key=lambda x: x['date'], reverse=True)
    except Exception as e:
        logging.error(f"Error getting image list: {str(e)}")
        return []

class SSEHandler(threading.Thread):
    def __init__(self, handler):
        super().__init__(daemon=True)
        self.handler = handler
        self.running = True

    def run(self):
        try:
            while self.running:
                try:
                    self.handler.wfile.write(b"data: ping\n\n")
                    self.handler.wfile.flush()
                    time.sleep(15)
                except (BrokenPipeError, ConnectionResetError):
                    break
                except Exception as e:
                    logging.error(f"SSE Error: {e}")
                    break
        finally:
            connection_manager.remove_client(self.handler.wfile)
            try:
                self.handler.wfile.close()
            except:
                pass

    def stop(self):
        self.running = False

class GalleryHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.sse_handler = None
        super().__init__(*args, **kwargs)

    def do_GET(self):
        try:
            logging.info(f"Handling request for path: {self.path}")
            
            # Handle Ollama models request first
            if self.path == '/api/ollama/models':
                try:
                    logging.info("Attempting to get Ollama models using subprocess")
                    # Run ollama list command
                    result = subprocess.run(['ollama', 'list'], 
                                         capture_output=True, 
                                         text=True)
                    
                    if result.returncode == 0:
                        # Parse the output, skipping the header line
                        lines = result.stdout.strip().split('\n')[1:]
                        models = []
                        
                        for line in lines:
                            if line.strip():  # Skip empty lines
                                parts = line.split()
                                if parts:
                                    model_name = parts[0]
                                    # Remove ':latest' suffix if present
                                    model_name = model_name.replace(':latest', '')
                                    # Get size if available
                                    size = parts[1] if len(parts) > 1 else 'unknown'
                                    
                                    models.append({
                                        'name': model_name,
                                        'size': size
                                    })
                        
                        # Sort models alphabetically
                        models.sort(key=lambda x: x['name'])
                        
                        logging.info(f"Found {len(models)} Ollama models")
                        
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps(models).encode())
                        return
                        
                    else:
                        logging.error(f"Failed to get models from ollama list: {result.stderr}")
                        self.send_error(500, 'Failed to get model list from Ollama')
                        return
                        
                except FileNotFoundError:
                    logging.error("Ollama command not found. Please ensure Ollama is installed and in PATH")
                    self.send_error(500, 'Ollama not found - Is it installed?')
                    return
                except Exception as e:
                    logging.error(f"Error getting Ollama models: {str(e)}")
                    logging.error(f"Exception type: {type(e)}")
                    import traceback
                    logging.error(f"Traceback: {traceback.format_exc()}")
                    self.send_error(500, f'Failed to get model list: {str(e)}')
                    return

            # Handle static files
            if self.path.startswith('/static/'):
                try:
                    # Get the file path relative to the server directory
                    file_path = os.path.join(os.path.dirname(__file__), self.path[1:])
                    
                    # Check if file exists and is within static directory
                    if os.path.exists(file_path) and os.path.commonpath([file_path, os.path.join(os.path.dirname(__file__), 'static')]) == os.path.join(os.path.dirname(__file__), 'static'):
                        # Get the content type based on file extension
                        content_type, _ = mimetypes.guess_type(file_path)
                        if content_type is None:
                            content_type = 'application/octet-stream'
                        
                        self.send_response(200)
                        self.send_header('Content-type', content_type)
                        self.end_headers()
                        
                        with open(file_path, 'rb') as f:
                            self.wfile.write(f.read())
                        return
                    else:
                        self.send_error(404, 'File not found')
                        return
                except Exception as e:
                    logging.error(f"Error serving static file: {e}")
                    self.send_error(500, 'Internal Server Error')
                    return
            
            if self.path == '/':
                logging.info("📄 Serving gallery page")
                try:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    
                    # Get the path to index.html relative to this script
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    index_path = os.path.join(current_dir, 'index.html')
                    
                    with open(index_path, 'rb') as f:
                        self.wfile.write(f.read())
                    logging.info("Successfully served index.html")
                except Exception as e:
                    logging.error(f"Error serving index.html: {str(e)}")
                    raise
                    
            elif self.path == '/api/images':
                logging.info("📋 Client requested image list")
                try:
                    logging.info("Getting image list")
                    images = get_image_list()
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Cache-Control', 'no-store')
                    self.end_headers()
                    
                    self.wfile.write(json.dumps(images).encode())
                    logging.info(f"Found {len(images)} images")
                    logging.info("Successfully sent image list")
                    
                except Exception as e:
                    logging.error(f"Error getting image list: {str(e)}")
                    self.send_error(500, 'Internal Server Error')
                    
            elif self.path.startswith('/thumbnails/'):
                logging.info(f"🖼️ Serving thumbnail: {os.path.basename(self.path)}")
                try:
                    thumb_filename = os.path.basename(self.path)
                    thumb_path = os.path.join(THUMBNAIL_CACHE_DIR, thumb_filename)
                    
                    if not os.path.exists(thumb_path):
                        # If thumbnail doesn't exist, return 404
                        self.send_error(404, 'Thumbnail not found')
                        return
                        
                    self.send_response(200)
                    self.send_header('Content-type', 'image/jpeg')
                    self.send_header('Cache-Control', 'public, max-age=31536000')
                    file_size = os.path.getsize(thumb_path)
                    self.send_header('Content-Length', str(file_size))
                    self.end_headers()
                    
                    with open(thumb_path, 'rb') as f:
                        self.wfile.write(f.read())
                    logging.info(f"Successfully served thumbnail: {thumb_path}")
                        
                except Exception as e:
                    logging.error(f"Error serving thumbnail {self.path}: {str(e)}")
                    self.send_error(500, 'Internal Server Error')
                
            elif self.path.startswith('/output/'):
                try:
                    rel_path = self.path[8:]
                    file_path = os.path.join(output_dir, rel_path)
                    logging.info(f"Serving file: {file_path}")
                    
                    if os.path.exists(file_path) and os.path.isfile(file_path):
                        self.send_response(200)
                        if file_path.lower().endswith('.png'):
                            self.send_header('Content-type', 'image/png')
                        elif file_path.lower().endswith(('.jpg', '.jpeg')):
                            self.send_header('Content-type', 'image/jpeg')
                        elif file_path.lower().endswith('.gif'):
                            self.send_header('Content-type', 'image/gif')
                        elif file_path.lower().endswith('.webp'):
                            self.send_header('Content-type', 'image/webp')
                        
                        file_size = os.path.getsize(file_path)
                        self.send_header('Content-Length', str(file_size))
                        self.end_headers()
                        
                        with open(file_path, 'rb') as f:
                            self.wfile.write(f.read())
                        logging.info(f"Successfully served file: {file_path}")
                    else:
                        logging.warning(f"File not found: {file_path}")
                        self.send_error(404, 'File not found')
                except Exception as e:
                    logging.error(f"Error serving file {file_path}: {str(e)}")
                    raise
            elif self.path == '/events':
                try:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/event-stream')
                    self.send_header('Cache-Control', 'no-cache')
                    self.send_header('Connection', 'keep-alive')
                    self.end_headers()
                    
                    connection_manager.add_client(self.wfile)
                    
                    # Keep connection alive
                    while True:
                        try:
                            self.wfile.write(b":\n\n")  # Send keepalive
                            self.wfile.flush()
                            time.sleep(15)
                        except:
                            break
                            
                    connection_manager.remove_client(self.wfile)
                    
                except Exception as e:
                    logging.error(f"Error handling event stream: {str(e)}")
                    if self.wfile in connection_manager.clients:
                        connection_manager.remove_client(self.wfile)
                        
            elif self.path == '/api/workflow-folders':
                try:
                    # Get base workflow directories
                    workflow_dirs = []
                    base_paths = [
                        os.path.join(comfy_dir, 'user', 'default', 'workflows'),
                        os.path.join(comfy_dir, '.users', 'default', 'workflows'),
                        os.path.join(comfy_dir, 'workflows'),
                        os.path.join(comfy_dir, 'custom_workflows')
                    ]
                    
                    # Add any directory containing .json files
                    for base_path in base_paths:
                        if os.path.exists(base_path):
                            workflow_dirs.append({
                                'path': os.path.relpath(base_path, comfy_dir),
                                'name': os.path.basename(base_path),
                                'count': len([f for f in glob.glob(os.path.join(base_path, "*.json"))])
                            })
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps(workflow_dirs).encode())
                    
                except Exception as e:
                    logging.error(f"Error getting workflow folders: {str(e)}")
                    self.send_error(500, 'Internal Server Error')
            elif self.path == '/api/workflows':
                try:
                    # Get the folder from query parameter
                    folder_path = self.headers.get('X-Workflow-Folder', 'user/default/workflows')
                    workflows_dir = os.path.normpath(os.path.join(comfy_dir, folder_path))
                    
                    # Security check - ensure path is within comfy_dir
                    if not os.path.commonpath([workflows_dir, comfy_dir]) == comfy_dir:
                        self.send_error(403, 'Access denied')
                        return
                    
                    if not os.path.exists(workflows_dir):
                        self.send_error(404, 'Workflows directory not found')
                        return
                    
                    logging.info(f"Scanning for workflows in: {workflows_dir}")
                    
                    # Get list of workflow files
                    workflows = []
                    for file in os.listdir(workflows_dir):
                        if file.endswith('.json'):
                            workflows.append({
                                'name': file,
                                'path': os.path.join(folder_path, file)  # Return relative path
                            })
                    
                    logging.info(f"Found {len(workflows)} workflows")
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps(workflows).encode())
                    
                except Exception as e:
                    logging.error(f"Error getting workflow list: {str(e)}")
                    self.send_error(500, 'Internal Server Error')
            elif self.path.startswith('/api/run-workflow/'):
                try:
                    workflow_path = unquote(self.path[16:])
                    # Try different possible workflow locations
                    possible_paths = [
                        os.path.join(comfy_dir, workflow_path),
                        os.path.join(comfy_dir, 'workflows', os.path.basename(workflow_path)),
                        os.path.join(comfy_dir, 'user', 'default', 'workflows', os.path.basename(workflow_path)),
                        os.path.join(comfy_dir, '.users', 'default', 'workflows', os.path.basename(workflow_path))
                    ]
                    
                    full_path = None
                    for path in possible_paths:
                        if os.path.exists(path):
                            full_path = path
                            break
                    
                    if not full_path:
                        logging.error(f"Workflow file not found in any location. Tried: {possible_paths}")
                        self.send_error(404, 'Workflow file not found')
                        return
                    
                    logging.info(f"Found workflow at: {full_path}")
                    
                    # Get request body for parameters
                    content_length = int(self.headers.get('Content-Length', 0))
                    post_data = self.rfile.read(content_length)
                    parameters = json.loads(post_data.decode('utf-8')).get('parameters', {})
                    
                    logging.info(f"Received parameters: {parameters}")
                    
                    # Read workflow
                    with open(full_path, 'r', encoding='utf-8') as f:
                        workflow_data = json.load(f)
                    
                    # Update workflow with provided parameters
                    if 'nodes' in workflow_data:
                        for node in workflow_data['nodes']:
                            node_id = str(node.get('id'))
                            if node_id in parameters:
                                # Ensure widgets_values is a list
                                if isinstance(parameters[node_id]['widgets_values'], list):
                                    node['widgets_values'] = parameters[node_id]['widgets_values']
                                else:
                                    # Convert to list if it's not already
                                    node['widgets_values'] = [parameters[node_id]['widgets_values']]
                                logging.info(f"Updated node {node_id} with values: {node['widgets_values']}")
                    
                    # Format the prompt data dynamically based on workflow structure
                    prompt_data = {
                        "prompt": {},
                        "client_id": "gallery_server",
                        "extra_data": {
                            "extra_pnginfo": {
                                "workflow": workflow_data
                            }
                        }
                    }

                    # Build the prompt structure from the workflow nodes
                    if 'nodes' in workflow_data:
                        for node in workflow_data['nodes']:
                            node_id = str(node.get('id'))
                            node_data = {
                                "class_type": node.get('type'),
                                "inputs": {}
                            }
                            
                            # Add inputs from workflow connections
                            if 'inputs' in node:
                                for input_name, input_data in node['inputs'].items():
                                    if isinstance(input_data, dict) and 'link' in input_data:
                                        # This is a connected input
                                        continue
                                    else:
                                        # This is a direct input value
                                        node_data['inputs'][input_name] = input_data

                            # Add widget values if present
                            if 'widgets_values' in node:
                                node_data['widgets_values'] = node['widgets_values']

                            prompt_data['prompt'][node_id] = node_data

                    # Process connections between nodes
                    for node in workflow_data['nodes']:
                        node_id = str(node.get('id'))
                        if 'inputs' in node:
                            for input_name, input_data in node['inputs'].items():
                                if isinstance(input_data, dict) and 'link' in input_data:
                                    # Find the source node and output
                                    for link in workflow_data.get('links', []):
                                        if link[0] == input_data['link']:  # If link ID matches
                                            from_node = str(link[1])
                                            from_output = link[3]
                                            # Add the connection to inputs
                                            prompt_data['prompt'][node_id]['inputs'][input_name] = {
                                                'node': from_node,
                                                'output': from_output
                                            }
                                            break

                    logging.info("Sending workflow to ComfyUI...")
                    logging.info(f"Prompt data: {json.dumps(prompt_data, indent=2)}")
                    
                    # Send modified workflow to ComfyUI
                    api_url = "http://127.0.0.1:8189/prompt"
                    headers = {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    }
                    
                    try:
                        response = requests.post(api_url, json=prompt_data, headers=headers)
                        logging.info(f"ComfyUI response status: {response.status_code}")
                        logging.info(f"ComfyUI response headers: {response.headers}")
                        logging.info(f"ComfyUI response text: {response.text}")
                        
                        if response.status_code == 200:
                            response_data = response.json()
                            logging.info(f"ComfyUI response data: {response_data}")
                            
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            self.wfile.write(json.dumps({
                                'success': True,
                                'message': 'Workflow started successfully',
                                'prompt_id': response_data.get('prompt_id')
                            }).encode())
                        else:
                            error_msg = f"ComfyUI returned status code {response.status_code}"
                            try:
                                error_data = response.json()
                                error_msg += f": {json.dumps(error_data)}"
                            except:
                                error_msg += f": {response.text}"
                            
                            logging.error(error_msg)
                            self.send_response(500)
                            self.send_header('Content-type', 'application/json')
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            self.wfile.write(json.dumps({
                                'success': False,
                                'error': error_msg
                            }).encode())
                    except requests.exceptions.RequestException as e:
                        error_msg = f"Failed to connect to ComfyUI: {str(e)}"
                        logging.error(error_msg)
                        self.send_response(500)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps({
                            'success': False,
                            'error': error_msg
                        }).encode())
                        
                except Exception as e:
                    logging.error(f"Error running workflow: {str(e)}")
                    self.send_error(500, str(e))
            elif self.path == '/api/restart':
                try:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    
                    self.wfile.write(json.dumps({'status': 'restarting'}).encode())
                    
                    # Schedule server restart
                    threading.Thread(target=self.restart_server, daemon=True).start()
                    
                except Exception as e:
                    logging.error(f"Error handling restart request: {str(e)}")
                    self.send_error(500, 'Internal Server Error')
            elif self.path == '/api/console':
                try:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/event-stream')
                    self.send_header('Cache-Control', 'no-cache')
                    self.send_header('Connection', 'keep-alive')
                    self.end_headers()
                    
                    # Send existing console messages
                    messages = []
                    while not console_queue.empty():
                        try:
                            messages.append(console_queue.get_nowait())
                        except:
                            break
                            
                    for msg in messages:
                        console_queue.put(msg)  # Put messages back
                        self.wfile.write(f"data: {json.dumps(msg)}\n\n".encode())
                        self.wfile.flush()
                    
                    connection_manager.add_client(self.wfile, is_console=True)
                    
                    # Keep connection alive
                    while True:
                        try:
                            self.wfile.write(b":\n\n")  # Send keepalive
                            self.wfile.flush()
                            time.sleep(15)
                        except:
                            break
                            
                    connection_manager.remove_client(self.wfile, is_console=True)
                    
                except Exception as e:
                    logging.error(f"Error handling console stream: {str(e)}")
                    if self.wfile in connection_manager.console_clients:
                        connection_manager.remove_client(self.wfile, is_console=True)
            elif self.path.startswith('/api/browse-folders'):
                try:
                    # Get the current path and show_all parameter from headers
                    current_path = self.headers.get('X-Current-Path', comfy_dir)
                    show_all = self.headers.get('X-Show-All', 'false').lower() == 'true'
                    current_path = os.path.abspath(current_path)
                    
                    # Security check - prevent browsing outside of root drive
                    if os.name == 'nt':  # Windows
                        root_drive = os.path.splitdrive(comfy_dir)[0]
                        if not current_path.startswith(root_drive):
                            current_path = root_drive
                    else:  # Unix-like
                        if not current_path.startswith('/'):
                            current_path = '/'
                    
                    # Get directory contents
                    items = []
                    try:
                        for entry in os.scandir(current_path):
                            try:
                                if entry.is_dir() or (show_all and entry.is_file()):
                                    # Check if directory contains json files or if it's a json file
                                    is_json = entry.is_file() and entry.name.endswith('.json')
                                    has_json = is_json or (
                                        entry.is_dir() and 
                                        any(f.endswith('.json') for f in os.listdir(entry.path))
                                    )
                                    
                                    items.append({
                                        'name': entry.name,
                                        'path': entry.path,
                                        'is_file': entry.is_file(),
                                        'is_json': is_json,
                                        'has_json': has_json
                                    })
                            except PermissionError:
                                continue
                    except PermissionError:
                        items = []
                    
                    # Sort items: directories first, then files
                    items.sort(key=lambda x: (x['is_file'], x['name'].lower()))
                    
                    # Add parent directory if it exists
                    parent_path = os.path.dirname(current_path)
                    if os.path.exists(parent_path) and parent_path != current_path:
                        items.insert(0, {
                            'name': '..',
                            'path': parent_path,
                            'is_file': False,
                            'is_json': False,
                            'has_json': False
                        })
                    
                    response_data = {
                        'current_path': current_path,
                        'items': items
                    }
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps(response_data).encode())
                    
                except Exception as e:
                    logging.error(f"Error browsing folders: {str(e)}")
                    self.send_error(500, 'Internal Server Error')
            elif self.path == '/api/text-files':
                try:
                    text_files = []
                    for root, _, files in os.walk(output_dir):
                        for file in files:
                            if file.lower().endswith(('.txt', '.json', '.md')):
                                full_path = os.path.join(root, file)
                                rel_path = os.path.relpath(full_path, output_dir).replace('\\', '/')
                                
                                # Read preview of text content
                                try:
                                    with open(full_path, 'r', encoding='utf-8') as f:
                                        content = f.read(500)  # Read first 500 characters
                                        preview = content[:500] + ('...' if len(content) > 500 else '')
                                except Exception as e:
                                    preview = f"Unable to read file content: {str(e)}"
                                
                                text_files.append({
                                    'path': rel_path,
                                    'name': file,
                                    'date': datetime.fromtimestamp(os.path.getmtime(full_path)).strftime('%Y-%m-%d %H:%M:%S'),
                                    'preview': preview,
                                    'size': os.path.getsize(full_path)
                                })
                    
                    # Sort files by date, newest first
                    text_files.sort(key=lambda x: x['date'], reverse=True)
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Cache-Control', 'no-store')
                    self.end_headers()
                    
                    self.wfile.write(json.dumps(text_files).encode())
                    logging.info(f"Found {len(text_files)} text files")
                    
                except Exception as e:
                    logging.error(f"Error getting text file list: {str(e)}")
                    self.send_error(500, 'Internal Server Error')
            elif self.path == '/api/ollama/generate':
                try:
                    logging.info("Received generate request")
                    
                    # Log request headers
                    logging.info(f"Request headers: {self.headers}")
                    
                    content_length = int(self.headers.get('Content-Length', 0))
                    logging.info(f"Content length: {content_length}")
                    
                    post_data = self.rfile.read(content_length)
                    logging.info(f"Raw post data: {post_data}")
                    
                    data = json.loads(post_data.decode('utf-8'))
                    logging.info(f"Parsed data: {data}")
                    
                    model = data.get('model')
                    prompt = data.get('prompt')
                    client_id = data.get('client_id')  # Added client ID
                    
                    logging.info(f"🤖 Generating response with model: {model}")
                    logging.info(f"📝 User prompt: {prompt}")
                    logging.info(f"👤 Client ID: {client_id}")
                    
                    if not model or not prompt:
                        logging.error("Missing model or prompt in request")
                        self.send_error(400, 'Missing model or prompt')
                        return
                    
                    try:
                        # Create Ollama client
                        client = Client(host='http://localhost:11434')
                        
                        # Get or create conversation history for this client
                        if client_id not in conversation_histories:
                            conversation_histories[client_id] = []
                        
                        # Add user message to history
                        conversation_histories[client_id].append({
                            'role': 'user',
                            'content': prompt
                        })
                        
                        # Generate response with context
                        logging.info("Sending request to Ollama with context...")
                        
                        # Use generate instead of chat for models that don't support chat
                        try:
                            # First try chat API
                            response = client.chat(
                                model=model,
                                messages=conversation_histories[client_id],
                                stream=False
                            )
                            response_content = response['message']['content']
                        except Exception as chat_error:
                            logging.info(f"Chat API failed, falling back to generate: {chat_error}")
                            # Fallback to generate API
                            response = client.generate(
                                model=model,
                                prompt=prompt,
                                stream=False
                            )
                            response_content = response['response']
                        
                        # Add assistant response to history
                        conversation_histories[client_id].append({
                            'role': 'assistant',
                            'content': response_content
                        })
                        
                        logging.info("✅ Response received from Ollama")
                        
                        response_data = {
                            'response': response_content
                        }
                        
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps(response_data).encode())
                        
                        logging.info(f"📤 Sent response to client")
                        
                    except Exception as e:
                        logging.error(f"❌ Error communicating with Ollama: {str(e)}")
                        logging.error(f"Exception type: {type(e)}")
                        logging.error(f"Exception traceback: {traceback.format_exc()}")
                        self.send_error(500, f'Ollama error: {str(e)}')
                        
                except Exception as e:
                    logging.error(f"❌ Error processing generate request: {str(e)}")
                    self.send_error(500, f'Generation failed: {str(e)}')
            elif self.path == '/api/ollama/test':
                try:
                    # Test if ollama command exists
                    which_result = subprocess.run(['which', 'ollama'], 
                                               capture_output=True, 
                                               text=True)
                    ollama_path = which_result.stdout.strip()
                    
                    # Test if ollama service is running
                    import requests
                    health_check = requests.get('http://localhost:11434/api/version')
                    
                    response_data = {
                        'ollama_installed': bool(ollama_path),
                        'ollama_path': ollama_path if ollama_path else None,
                        'service_running': health_check.status_code == 200,
                        'version': health_check.json() if health_check.status_code == 200 else None
                    }
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps(response_data).encode())
                    
                except Exception as e:
                    logging.error(f"Error testing ollama: {str(e)}")
                    self.send_error(500, f'Failed to test ollama: {str(e)}')
                
            elif self.path.startswith('/api/workflow-parameters/'):
                try:
                    workflow_path = unquote(self.path[22:])  # Remove '/api/workflow-parameters/'
                    # Normalize path separators and handle relative path
                    workflow_path = workflow_path.replace('/', os.path.sep).replace('\\', os.path.sep)
                    
                    # Try different possible workflow locations
                    possible_paths = [
                        os.path.join(comfy_dir, workflow_path),
                        os.path.join(comfy_dir, 'workflows', os.path.basename(workflow_path)),
                        os.path.join(comfy_dir, 'user', 'default', 'workflows', os.path.basename(workflow_path)),
                        os.path.join(comfy_dir, '.users', 'default', 'workflows', os.path.basename(workflow_path))
                    ]
                    
                    full_path = None
                    for path in possible_paths:
                        if os.path.exists(path):
                            full_path = path
                            break
                    
                    if not full_path:
                        logging.error(f"Workflow file not found in any location. Tried: {possible_paths}")
                        self.send_error(404, 'Workflow file not found')
                        return
                    
                    logging.info(f"Found workflow at: {full_path}")
                    
                    with open(full_path, 'r', encoding='utf-8') as f:
                        workflow_data = json.load(f)
                    
                    # Extract parameters from workflow nodes
                    parameters = {}
                    if 'nodes' in workflow_data:
                        for node in workflow_data['nodes']:
                            node_id = str(node.get('id'))
                            if 'widgets_values' in node:
                                parameters[node_id] = {
                                    'title': node.get('type', 'Unnamed Node'),
                                    'widgets_values': node['widgets_values']
                                }
                    
                    logging.info(f"Extracted parameters: {parameters}")
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps(parameters).encode())
                    
                except Exception as e:
                    logging.error(f"Error getting workflow parameters: {str(e)}")
                    self.send_error(500, 'Internal Server Error')
                
            else:
                logging.warning(f"Path not found: {self.path}")
                self.send_error(404, 'Not found')
                
        except Exception as e:
            logging.error(f"❌ Error handling request: {e}")
            try:
                self.send_error(500, 'Internal Server Error')
            except:
                pass

    def do_DELETE(self):
        try:
            if self.path.startswith('/api/images/'):
                # Get the file path and decode URL-encoded characters
                file_path = unquote(self.path[12:])  # Remove '/api/images/'
                logging.warning(f"🗑️ Delete request received for: {file_path}")
                
                # Security check
                full_path = os.path.abspath(os.path.join(output_dir, file_path))
                if not full_path.startswith(os.path.abspath(output_dir)):
                    logging.error("❌ Attempted to delete file outside output directory")
                    self.send_error(403, 'Access denied')
                    return

                if os.path.exists(full_path):
                    try:
                        # Delete thumbnail if it exists
                        mtime = os.path.getmtime(full_path)
                        hash_input = f"{full_path}{mtime}".encode('utf-8')
                        thumb_filename = hashlib.md5(hash_input).hexdigest() + '.jpg'
                        thumb_path = os.path.join(THUMBNAIL_CACHE_DIR, thumb_filename)
                        
                        # Delete the original file
                        os.remove(full_path)
                        logging.info(f"✅ Successfully deleted: {file_path}")
                        
                        # Delete thumbnail if it exists
                        if os.path.exists(thumb_path):
                            os.remove(thumb_path)
                            logging.info(f"✅ Deleted associated thumbnail")

                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps({'success': True}).encode())
                        
                    except Exception as e:
                        logging.error(f"❌ Error deleting file: {e}")
                        self.send_error(500, 'Failed to delete file')
                else:
                    logging.warning(f"⚠️ File not found: {file_path}")
                    self.send_error(404, 'File not found')
            elif self.path.startswith('/api/texts/'):
                # Get the file path and decode URL-encoded characters
                file_path = unquote(self.path[11:])  # Remove '/api/texts/'
                logging.warning(f"🗑️ Delete request received for text file: {file_path}")
                
                # Security check
                full_path = os.path.abspath(os.path.join(output_dir, file_path))
                if not full_path.startswith(os.path.abspath(output_dir)):
                    logging.error("❌ Attempted to delete file outside output directory")
                    self.send_error(403, 'Access denied')
                    return

                if os.path.exists(full_path):
                    try:
                        # Delete the text file
                        os.remove(full_path)
                        logging.info(f"✅ Successfully deleted text file: {file_path}")

                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps({'success': True}).encode())
                        
                    except Exception as e:
                        logging.error(f"❌ Error deleting text file: {e}")
                        self.send_error(500, 'Failed to delete file')
                else:
                    logging.warning(f"⚠️ Text file not found: {file_path}")
                    self.send_error(404, 'File not found')
                
            else:
                logging.warning(f"⚠️ Invalid delete path: {self.path}")
                self.send_error(400, 'Invalid request')
                    
        except Exception as e:
            logging.error(f"❌ Error handling delete request: {e}")
            self.send_error(500, 'Internal Server Error')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Max-Age', '86400')  # 24 hours
        self.end_headers()

    def log_message(self, format, *args):
        """Override to use our logging system"""
        logging.info(format % args)

    def do_HEAD(self):
        """Handle HEAD requests for ETag support"""
        if self.path == '/api/images':
            try:
                images = get_image_list()
                # Generate ETag based on content
                content = json.dumps(images).encode()
                etag = hashlib.md5(content).hexdigest()
                
                self.send_response(200)
                self.send_header('ETag', f'"{etag}"')
                self.send_header('Last-Modified', formatdate(time.time(), usegmt=True))
                self.send_header('Cache-Control', 'public, max-age=3600')
                self.end_headers()
            except Exception as e:
                logging.error(f"Error handling HEAD request: {str(e)}")
                self.send_error(500, 'Internal Server Error')

    def do_POST(self):
        try:
            if self.path.startswith('/api/run-workflow/'):
                workflow_path = unquote(self.path[16:])
                # Try different possible workflow locations
                possible_paths = [
                    os.path.join(comfy_dir, workflow_path),
                    os.path.join(comfy_dir, 'workflows', os.path.basename(workflow_path)),
                    os.path.join(comfy_dir, 'user', 'default', 'workflows', os.path.basename(workflow_path)),
                    os.path.join(comfy_dir, '.users', 'default', 'workflows', os.path.basename(workflow_path))
                ]
                
                full_path = None
                for path in possible_paths:
                    if os.path.exists(path):
                        full_path = path
                        break
                
                if not full_path:
                    logging.error(f"Workflow file not found in any location. Tried: {possible_paths}")
                    self.send_error(404, 'Workflow file not found')
                    return
                
                logging.info(f"Found workflow at: {full_path}")
                
                # Get request body for parameters
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                parameters = json.loads(post_data.decode('utf-8')).get('parameters', {})
                
                logging.info(f"Received parameters: {parameters}")
                
                # Read workflow
                with open(full_path, 'r', encoding='utf-8') as f:
                    workflow_data = json.load(f)
                
                # Update workflow with provided parameters
                if 'nodes' in workflow_data:
                    for node in workflow_data['nodes']:
                        node_id = str(node.get('id'))
                        if node_id in parameters:
                            # Ensure widgets_values is a list
                            if isinstance(parameters[node_id]['widgets_values'], list):
                                node['widgets_values'] = parameters[node_id]['widgets_values']
                            else:
                                # Convert to list if it's not already
                                node['widgets_values'] = [parameters[node_id]['widgets_values']]
                            logging.info(f"Updated node {node_id} with values: {node['widgets_values']}")
                
                # Format the prompt data dynamically based on workflow structure
                prompt_data = {
                    "prompt": {},
                    "client_id": "gallery_server",
                    "extra_data": {
                        "extra_pnginfo": {
                            "workflow": workflow_data
                        }
                    }
                }

                # Build the prompt structure from the workflow nodes
                if 'nodes' in workflow_data:
                    for node in workflow_data['nodes']:
                        node_id = str(node.get('id'))
                        node_data = {
                            "class_type": node.get('type'),
                            "inputs": {}
                        }
                        
                        # Add inputs from workflow connections
                        if 'inputs' in node:
                            for input_name, input_data in node['inputs'].items():
                                if isinstance(input_data, dict) and 'link' in input_data:
                                    # This is a connected input
                                    continue
                                else:
                                    # This is a direct input value
                                    node_data['inputs'][input_name] = input_data

                        # Add widget values if present
                        if 'widgets_values' in node:
                            node_data['widgets_values'] = node['widgets_values']

                        prompt_data['prompt'][node_id] = node_data

                # Process connections between nodes
                for node in workflow_data['nodes']:
                    node_id = str(node.get('id'))
                    if 'inputs' in node:
                        for input_name, input_data in node['inputs'].items():
                            if isinstance(input_data, dict) and 'link' in input_data:
                                # Find the source node and output
                                for link in workflow_data.get('links', []):
                                    if link[0] == input_data['link']:  # If link ID matches
                                        from_node = str(link[1])
                                        from_output = link[3]
                                        # Add the connection to inputs
                                        prompt_data['prompt'][node_id]['inputs'][input_name] = {
                                            'node': from_node,
                                            'output': from_output
                                        }
                                        break

                logging.info("Sending workflow to ComfyUI...")
                logging.info(f"Prompt data: {json.dumps(prompt_data, indent=2)}")
                
                # Send modified workflow to ComfyUI
                api_url = "http://127.0.0.1:8189/prompt"
                headers = {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
                
                try:
                    response = requests.post(api_url, json=prompt_data, headers=headers)
                    logging.info(f"ComfyUI response status: {response.status_code}")
                    logging.info(f"ComfyUI response headers: {response.headers}")
                    logging.info(f"ComfyUI response text: {response.text}")
                    
                    if response.status_code == 200:
                        response_data = response.json()
                        logging.info(f"ComfyUI response data: {response_data}")
                        
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps({
                            'success': True,
                            'message': 'Workflow started successfully',
                            'prompt_id': response_data.get('prompt_id')
                        }).encode())
                    else:
                        error_msg = f"ComfyUI returned status code {response.status_code}"
                        try:
                            error_data = response.json()
                            error_msg += f": {json.dumps(error_data)}"
                        except:
                            error_msg += f": {response.text}"
                        
                        logging.error(error_msg)
                        self.send_response(500)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps({
                            'success': False,
                            'error': error_msg
                        }).encode())
                except requests.exceptions.RequestException as e:
                    error_msg = f"Failed to connect to ComfyUI: {str(e)}"
                    logging.error(error_msg)
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'success': False,
                        'error': error_msg
                    }).encode())
                    
            else:
                self.send_error(404, "Not found")
            
        except Exception as e:
            logging.error(f"Error handling POST request: {str(e)}")
            self.send_error(500, str(e))

    def restart_server(self):
        """Restart the server by executing the script again"""
        try:
            logging.info("🔄 Restarting server...")
            # Get the path to the current script
            script_path = os.path.abspath(__file__)
            
            # Use Python executable from sys.executable
            python_path = sys.executable
            
            # Start new process with hidden window
            if os.name == 'nt':  # Windows
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                
                subprocess.Popen(
                    [python_path, script_path],
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:  # Linux/Mac
                subprocess.Popen(
                    [python_path, script_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            
            # Clean up and exit current server
            logging.info("Shutting down current server...")
            # Stop the file observer
            observer.stop()
            observer.join()
            # Close all client connections
            for client in connection_manager.clients:
                try:
                    client.close()
                except:
                    pass
            for client in connection_manager.console_clients:
                try:
                    client.close()
                except:
                    pass
            # Exit after a short delay
            threading.Timer(1.0, lambda: os._exit(0)).start()
            
        except Exception as e:
            logging.error(f"Error restarting server: {str(e)}")

class ThreadedHTTPServer(HTTPServer):
    def process_request(self, request, client_address):
        """Start a new thread to process the request."""
        thread = threading.Thread(target=self.process_request_thread,
                                args=(request, client_address))
        thread.daemon = True
        thread.start()

    def process_request_thread(self, request, client_address):
        """Process the request in a separate thread."""
        try:
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)
        finally:
            self.shutdown_request(request)

def schedule_restart():
    logging.info("Scheduling server restart in 12 hours")
    threading.Timer(12 * 60 * 60, lambda: os._exit(0)).start()

def run_standalone_server():
    global output_dir, comfy_dir
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    comfy_dir = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
    output_dir = os.path.join(comfy_dir, 'output')
    
    logging.info("="*50)
    logging.info("🖼️ ComfyUI Gallery Server")
    logging.info("="*50)
    logging.info(f"📂 Output directory: {output_dir}")
    logging.info(f"📂 ComfyUI directory: {comfy_dir}")
    
    event_handler = ImageChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, output_dir, recursive=True)
    observer.start()
    
    server = ThreadedHTTPServer(('0.0.0.0', 8200), GalleryHandler)
    
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    logging.info("\n🌐 Server URLs:")
    logging.info(f"   Local:   http://localhost:8200")
    logging.info(f"   Network: http://{local_ip}:8200")
    logging.info("\n⌨️  Press Ctrl+C to stop the server")
    logging.info("="*50)
    
    # Schedule restart every 12 hours
    schedule_restart()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("\n👋 Shutting down server...")
    finally:
        observer.stop()
        observer.join()
        server.server_close()

if __name__ == "__main__":
    try:
        run_standalone_server()
    except Exception as e:
        print(f"Error: {e}")
        input("Press Enter to exit...")
        sys.exit(1)