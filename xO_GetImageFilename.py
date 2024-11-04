import logging
import torch

class xO_GetImageFilename:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("filename",)
    FUNCTION = "get_filename"
    CATEGORY = "💦xObiomesh/Utils"

    # Match the color scheme of other xO nodes
    COLOR_TYPES = ["#322", "#322"]  # Dark red background
    TITLE_COLOR = "#DDD"  # Light gray title

    def get_filename(self, images):
        try:
            # Handle tensor input
            if isinstance(images, torch.Tensor):
                # Get image information
                batch_size, height, width = images.shape[:3]
                channels = images.shape[3] if len(images.shape) > 3 else 1
                
                # Try to get metadata from tensor
                if hasattr(images, 'image_path'):
                    return (str(images.image_path),)
                if hasattr(images, 'filename'):
                    return (str(images.filename),)
                if hasattr(images, 'name'):
                    return (str(images.name),)
                
                # If we can't get a filename, return a default with image info
                return (f"image_{width}x{height}_{channels}ch_{str(hash(str(images.shape)))[:4]}",)
            
            return ("unknown_image",)
            
        except Exception as e:
            logging.error(f"Error getting image filename: {str(e)}")
            return ("generated_image",)  # Return a valid string even in case of error