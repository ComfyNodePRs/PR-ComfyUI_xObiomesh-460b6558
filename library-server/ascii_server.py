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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ascii_server.log'),
        logging.StreamHandler()
    ]
)

# Global variables
clients = []
output_dir = None

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
            image_data = {
                'path': rel_path,
                'name': os.path.basename(event.src_path),
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            message = f"data: {json.dumps(image_data)}\n\n"
            for client in list(clients):  # Use a copy of the list
                try:
                    client.write(message.encode())
                    client.flush()
                except:
                    if client in clients:
                        clients.remove(client)
        except Exception as e:
            logging.error(f"Error handling file event: {e}")

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
    """Get list of images with thumbnails"""
    images = []
    try:
        if not os.path.exists(output_dir):
            logging.error(f"Output directory does not exist: {output_dir}")
            return images

        # Walk through output directory
        all_images = []
        for root, _, files in os.walk(output_dir):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                    try:
                        file_path = os.path.join(root, file)
                        mod_time = os.path.getmtime(file_path)
                        rel_path = os.path.relpath(file_path, output_dir).replace('\\', '/')
                        
                        # Generate thumbnail
                        thumb_filename = generate_thumbnail(file_path)
                        
                        if thumb_filename:
                            all_images.append({
                                'path': rel_path,
                                'name': file,
                                'date': datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S'),
                                'timestamp': mod_time,
                                'thumbnail': thumb_filename
                            })
                    except Exception as e:
                        logging.error(f"Error processing file {file}: {str(e)}")
                        continue
        
        # Sort by timestamp in descending order
        all_images.sort(key=lambda x: x['timestamp'], reverse=True)
        images = [{k: v for k, v in img.items() if k != 'timestamp'} for img in all_images]
        
    except Exception as e:
        logging.error(f"Error scanning for images: {str(e)}")
    return images

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
            
            if self.path == '/':
                try:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    with open('index.html', 'rb') as f:
                        self.wfile.write(f.read())
                    logging.info("Successfully served index.html")
                except Exception as e:
                    logging.error(f"Error serving index.html: {str(e)}")
                    raise
                    
            elif self.path == '/api/images':
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
            else:
                logging.warning(f"Path not found: {self.path}")
                self.send_error(404, 'Not found')
                
        except Exception as e:
            logging.error(f"Unhandled error in do_GET: {str(e)}")
            try:
                self.send_error(500, 'Internal Server Error')
            except:
                pass

    def do_DELETE(self):
        try:
            if self.path.startswith('/delete/'):
                rel_path = self.path[8:]
                file_path = os.path.join(output_dir, rel_path)
                
                logging.info(f"Attempting to delete file: {file_path}")
                
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    try:
                        os.remove(file_path)
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps({'success': True}).encode())
                        logging.info(f"Successfully deleted file: {file_path}")
                    except Exception as e:
                        logging.error(f"Error deleting file {file_path}: {str(e)}")
                        self.send_error(500, 'Failed to delete file')
                else:
                    logging.warning(f"File not found for deletion: {file_path}")
                    self.send_error(404, 'File not found')
            else:
                self.send_error(404, 'Not found')
        except Exception as e:
            logging.error(f"Unhandled error in do_DELETE: {str(e)}")
            self.send_error(500, 'Internal Server Error')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
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
    global output_dir
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    comfy_dir = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
    output_dir = os.path.join(comfy_dir, 'output')
    
    print(f"Current directory: {current_dir}")
    print(f"ComfyUI directory: {comfy_dir}")
    print(f"Output directory: {output_dir}")
    
    os.chdir(current_dir)
    
    event_handler = ImageChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, output_dir, recursive=True)
    observer.start()
    
    # Use ThreadedHTTPServer instead of HTTPServer
    server = ThreadedHTTPServer(('localhost', 8200), GalleryHandler)
    
    print("="*50)
    print("ComfyUI Gallery Server")
    print("="*50)
    print(f"\nServing at http://localhost:8200")
    print(f"Watching directory: {output_dir}")
    print("\nPress Ctrl+C to stop the server")
    print("="*50)
    
    # Open browser in a separate thread
    threading.Timer(1.0, lambda: webbrowser.open('http://localhost:8200')).start()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
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