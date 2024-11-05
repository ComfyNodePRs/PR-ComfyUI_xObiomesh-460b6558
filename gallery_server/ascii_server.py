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
        
        # Add to console queue
        try:
            console_data = {
                'time': formatted_time,
                'level': record.levelname,
                'message': record.msg
            }
            console_queue.put(console_data)
            
            # Notify all connected console clients
            for client in console_clients:
                try:
                    client.write(f"data: {json.dumps(console_data)}\n\n".encode())
                    client.flush()
                except:
                    console_clients.discard(client)
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
clients = []
output_dir = None
comfy_dir = None
console_queue = Queue(maxsize=1000)  # Store last 1000 messages
console_clients = set()

# Add thumbnail configuration
THUMBNAIL_SIZE = (250, 250)  # Size for thumbnails
THUMBNAIL_CACHE_DIR = 'thumbnails'  # Directory to store thumbnails
REFRESH_INTERVAL = 10000  # Minimum time between image list refreshes in ms

# Create thumbnail cache directory if it doesn't exist
if not os.path.exists(THUMBNAIL_CACHE_DIR):
    os.makedirs(THUMBNAIL_CACHE_DIR)

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
            client_count = len(clients)
            for client in list(clients):
                try:
                    client.write(message.encode())
                    client.flush()
                except:
                    if client in clients:
                        clients.remove(client)
                        
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
            if self.handler.wfile in clients:
                clients.remove(self.handler.wfile)
                logging.info(f"Client disconnected. Remaining clients: {len(clients)}")

    def stop(self):
        self.running = False

class GalleryHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.sse_handler = None
        super().__init__(*args, **kwargs)

    def do_GET(self):
        try:
            logging.info(f"Handling request for path: {self.path}")
            
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
                logging.info(f"🔌 New client connected from {self.client_address[0]}")
                # ... rest of events handling ...
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
                    # Get just the filename from the path and decode it
                    workflow_filename = unquote(self.path[16:])  # Remove '/api/run-workflow/'
                    
                    # Find the workflows directory
                    workflows_dir = os.path.normpath(os.path.join(comfy_dir, 'user', 'default', 'workflows'))
                    if not os.path.exists(workflows_dir):
                        workflows_dir = os.path.normpath(os.path.join(comfy_dir, '.users', 'default', 'workflows'))
                    
                    if not os.path.exists(workflows_dir):
                        logging.error(f"Workflows directory not found")
                        self.send_error(404, 'Workflows directory not found')
                        return
                        
                    # Build the full path correctly
                    full_path = os.path.join(workflows_dir, os.path.basename(workflow_filename))
                    full_path = os.path.normpath(full_path)
                    
                    logging.info(f"Attempting to run workflow: {full_path}")
                    
                    if not os.path.exists(full_path):
                        logging.error(f"Workflow file not found: {full_path}")
                        self.send_error(404, 'Workflow file not found')
                        return
                    
                    # Read the workflow file with proper encoding
                    try:
                        # Try UTF-8 first
                        with open(full_path, 'r', encoding='utf-8') as f:
                            workflow_data = json.load(f)
                    except UnicodeDecodeError:
                        # If UTF-8 fails, try with utf-8-sig (for files with BOM)
                        with open(full_path, 'r', encoding='utf-8-sig') as f:
                            workflow_data = json.load(f)
                    
                    # Send the workflow to the ComfyUI API
                    # I changed the port to 8189 because 8188 was already in use by another instance of ComfyUI
                    api_url = "http://127.0.0.1:8189/prompt"  
                    
                    logging.info(f"Sending workflow to ComfyUI API at {api_url}")
                    
                    response = requests.post(api_url, json={
                        "prompt": workflow_data
                    })
                    
                    if response.status_code == 200:
                        logging.info("Workflow sent successfully")
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        
                        self.wfile.write(json.dumps({
                            'success': True,
                            'message': 'Workflow started successfully'
                        }).encode())
                    else:
                        logging.error(f"Failed to send workflow: {response.text}")
                        self.send_response(500)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        
                        self.wfile.write(json.dumps({
                            'success': False,
                            'error': f'Failed to send workflow: {response.text}'
                        }).encode())
                        
                except Exception as e:
                    logging.error(f"Error running workflow: {str(e)}")
                    self.send_error(500, 'Internal Server Error')
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
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    
                    # Send existing console messages
                    while not console_queue.empty():
                        data = console_queue.get()
                        self.wfile.write(f"data: {json.dumps(data)}\n\n".encode())
                        self.wfile.flush()
                    
                    # Add client to console clients set
                    console_clients.add(self.wfile)
                    
                    # Keep connection alive
                    while True:
                        try:
                            self.wfile.write(b":\n\n")  # Send keepalive
                            self.wfile.flush()
                            time.sleep(15)
                        except:
                            break
                        
                    console_clients.discard(self.wfile)
                    
                except Exception as e:
                    logging.error(f"Error handling console stream: {str(e)}")
                    if self.wfile in console_clients:
                        console_clients.discard(self.wfile)
            elif self.path.startswith('/api/browse-folders'):
                try:
                    # Get the current path from query parameter, default to comfy_dir
                    current_path = self.headers.get('X-Current-Path', comfy_dir)
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
                    dirs = []
                    try:
                        for entry in os.scandir(current_path):
                            if entry.is_dir():
                                try:
                                    # Check if directory contains json files
                                    has_json = any(f.endswith('.json') for f in os.listdir(entry.path))
                                    dirs.append({
                                        'name': entry.name,
                                        'path': entry.path,
                                        'has_json': has_json
                                    })
                                except PermissionError:
                                    continue
                    except PermissionError:
                        dirs = []
                    
                    # Get parent directory
                    parent_path = os.path.dirname(current_path)
                    if os.path.exists(parent_path) and parent_path != current_path:
                        dirs.insert(0, {
                            'name': '..',
                            'path': parent_path,
                            'has_json': False
                        })
                    
                    response_data = {
                        'current_path': current_path,
                        'directories': dirs
                    }
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps(response_data).encode())
                    
                except Exception as e:
                    logging.error(f"Error browsing folders: {str(e)}")
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
            if self.path.startswith('/api/rename/'):
                # First send the response headers
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                
                # Read content length and data
                content_length = int(self.headers.get('Content-Length', 0))
                content_type = self.headers.get('Content-Type', '')
                
                if content_type != 'application/json':
                    self.send_error(400, 'Content-Type must be application/json')
                    return
                
                post_data = self.rfile.read(content_length)
                try:
                    data = json.loads(post_data.decode('utf-8'))
                except json.JSONDecodeError:
                    self.send_error(400, 'Invalid JSON data')
                    return
                
                if 'newName' not in data:
                    self.send_error(400, 'Missing newName in request')
                    return
                
                # Get the file path and decode URL-encoded characters
                file_path = unquote(self.path[11:])  # Remove '/api/rename/'
                # Remove leading slash if present
                file_path = file_path.lstrip('/')
                
                # Debug logging
                logging.info(f"Original file_path: {file_path}")
                logging.info(f"Output directory: {output_dir}")
                
                # Normalize paths to handle different path separators
                output_dir_norm = os.path.normpath(os.path.abspath(output_dir))
                full_path = os.path.normpath(os.path.abspath(os.path.join(output_dir, file_path)))
                
                # More debug logging
                logging.info(f"Normalized output_dir: {output_dir_norm}")
                logging.info(f"Full path: {full_path}")
                
                # Security check - make sure the path is within output directory
                is_within_output = full_path.startswith(output_dir_norm + os.sep) or full_path == output_dir_norm
                logging.info(f"Is within output directory: {is_within_output}")
                
                if not is_within_output:
                    logging.error(f"❌ Attempted to access file outside output directory:")
                    logging.error(f"File path: {full_path}")
                    logging.error(f"Output directory: {output_dir_norm}")
                    self.send_error(403, 'Access denied')
                    return

                new_name = data['newName']
                # Ensure new name doesn't contain path separators
                if os.path.sep in new_name or (os.path.altsep and os.path.altsep in new_name):
                    self.send_error(400, 'Invalid filename')
                    return
                
                # Create new path in same directory as original file
                new_path = os.path.join(os.path.dirname(full_path), new_name)
                logging.info(f"New path will be: {new_path}")
                
                try:
                    if os.path.exists(full_path):
                        # Delete old thumbnail if it exists
                        old_mtime = os.path.getmtime(full_path)
                        old_hash = hashlib.md5(f"{full_path}{old_mtime}".encode('utf-8')).hexdigest()
                        old_thumb = os.path.join(THUMBNAIL_CACHE_DIR, f"{old_hash}.jpg")
                        if os.path.exists(old_thumb):
                            os.remove(old_thumb)

                        # Check if target file already exists
                        if os.path.exists(new_path):
                            self.send_error(409, 'File with that name already exists')
                            return

                        # Rename the file
                        os.rename(full_path, new_path)
                        logging.info(f"✅ Successfully renamed: {file_path} to {new_name}")
                        
                        # Generate new thumbnail
                        generate_thumbnail(new_path)
                        
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({'success': True}).encode())
                    else:
                        logging.warning(f"⚠️ File not found: {file_path}")
                        self.send_error(404, 'File not found')
                except Exception as e:
                    logging.error(f"❌ Error renaming file: {e}")
                    self.send_error(500, f'Failed to rename file: {str(e)}')
                return

            self.send_error(404, 'Not found')
            
        except Exception as e:
            logging.error(f"❌ Error handling POST request: {str(e)}")
            self.send_error(500, 'Internal Server Error')

    def restart_server(self):
        """Restart the server by executing the script again"""
        try:
            logging.info("🔄 Restarting server...")
            # Get the path to the current script
            script_path = os.path.abspath(__file__)
            
            # Use Python executable from sys.executable
            python_path = sys.executable
            
            # Start new process
            if os.name == 'nt':  # Windows
                subprocess.Popen(
                    ['start', 'cmd', '/k', python_path, script_path],
                    shell=True,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            else:  # Linux/Mac
                subprocess.Popen(
                    ['gnome-terminal', '--', python_path, script_path]
                )
            
            # Schedule shutdown of current server
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