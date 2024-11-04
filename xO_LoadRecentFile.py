import os
import logging
from pathlib import Path
import folder_paths
from PIL import Image, ImageOps
import numpy as np
import torch
import time
import re

class xO_LoadRecentFile:
    def __init__(self):
        self.output_dir = folder_paths.output_directory

    @classmethod
    def INPUT_TYPES(cls):
        output_dir = folder_paths.output_directory
        try:
            output_folders = [name for name in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, name))]
        except:
            output_folders = []
        
        if not output_folders:
            output_folders = [""]
            
        return {
            "required": {
                "trigger": ("*", {
                    "tooltip": "Connect to node output that should trigger this node"
                }),
                "output_folder": (sorted(output_folders), {
                    "default": output_folders[0],
                    "tooltip": "Select folder to load from"
                }),
                "file_types": (["images", "text", "all"], {
                    "default": "images",
                    "tooltip": "Type of files to look for"
                }),
            },
            "optional": {
                "custom_path": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "tooltip": "Optional: Custom directory path (overrides output_folder if provided)"
                })
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK", "STRING", "STRING", "INT", "INT",)
    RETURN_NAMES = ("image", "mask", "filepath", "filename", "width", "height",)
    FUNCTION = "load_recent"
    CATEGORY = "💦xObiomesh/Utils"

    COLOR_TYPES = ["#322", "#322"]
    TITLE_COLOR = "#DDD"

    @classmethod
    def VALIDATE_INPUTS(cls, trigger, output_folder, file_types, custom_path=None):
        if custom_path and not os.path.exists(custom_path):
            return False
        if not custom_path and (not output_folder or output_folder == ""):
            return False
        return True

    def pil2tensor(self, image):
        """Convert PIL image to tensor in BCHW format"""
        img_tensor = torch.from_numpy(np.array(image).astype(np.float32) / 255.0)
        if len(img_tensor.shape) == 2:  # Grayscale
            img_tensor = img_tensor.unsqueeze(0).unsqueeze(0)
        else:  # RGB/RGBA
            img_tensor = img_tensor.permute(2, 0, 1).unsqueeze(0)
        return img_tensor

    def load_recent(self, trigger, output_folder, file_types, custom_path=None):
        try:
            # Wait a short moment to ensure file is fully written
            time.sleep(0.5)
            
            if custom_path and os.path.exists(custom_path):
                directory = custom_path
            else:
                directory = os.path.join(self.output_dir, output_folder)

            if not os.path.exists(directory):
                raise ValueError(f"Directory does not exist: {directory}")

            if file_types == "images":
                extensions = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")
            elif file_types == "text":
                extensions = (".txt", ".json", ".csv")
            else:  # "all"
                extensions = None

            files = []
            for file in os.listdir(directory):
                if extensions is None or file.lower().endswith(extensions):
                    full_path = os.path.join(directory, file)
                    if os.path.isfile(full_path):
                        files.append((full_path, os.path.getmtime(full_path)))

            if not files:
                raise ValueError(f"No matching files found in {directory}")

            most_recent = max(files, key=lambda x: x[1])
            filepath = most_recent[0]
            filename = os.path.basename(filepath)

            # Load image if it's an image file
            if file_types == "images":
                try:
                    img = Image.open(filepath)
                    img = ImageOps.exif_transpose(img)
                    width, height = img.size
                    
                    # Convert to RGB and get image tensor
                    rgb_image = img.convert("RGB")
                    image_tensor = self.pil2tensor(rgb_image)
                    
                    # Create mask tensor
                    if img.mode == 'RGBA':
                        alpha = img.split()[3]
                        mask = self.pil2tensor(alpha)
                    else:
                        mask = torch.ones((1, 1, height, width), dtype=torch.float32)
                    
                    return (image_tensor, mask, filepath, filename, width, height)
                except Exception as e:
                    logging.error(f"Error loading image: {str(e)}")
                    # Return empty tensors in BCHW format
                    return (torch.zeros(1, 3, 64, 64), torch.ones(1, 1, 64, 64), filepath, filename, 64, 64)
            else:
                # Return empty tensors for non-image files
                return (torch.zeros(1, 3, 64, 64), torch.ones(1, 1, 64, 64), filepath, filename, 64, 64)

        except Exception as e:
            logging.error(f"Error loading recent file: {str(e)}")
            return (torch.zeros(1, 3, 64, 64), torch.ones(1, 1, 64, 64), "", "", 64, 64)

    @classmethod
    def IS_CHANGED(cls, trigger, output_folder, file_types, custom_path=None):
        try:
            if custom_path and os.path.exists(custom_path):
                directory = custom_path
            else:
                directory = os.path.join(folder_paths.output_directory, output_folder)
            
            if not os.path.exists(directory):
                return ""
                
            files = [(f, os.path.getmtime(os.path.join(directory, f))) 
                    for f in os.listdir(directory) 
                    if os.path.isfile(os.path.join(directory, f))]
            
            if not files:
                return ""
                
            most_recent = max(files, key=lambda x: x[1])
            return f"{most_recent[1]}_{trigger}"
        except:
            return ""