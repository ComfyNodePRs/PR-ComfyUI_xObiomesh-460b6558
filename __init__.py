import os
import shutil

# Get the paths
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DIR_DEV_JS = os.path.abspath(f'{THIS_DIR}/js')
DIR_WEB_JS = os.path.abspath(f'{THIS_DIR}/../../web/extensions/xObiomesh')

# Create web extensions directory if it doesn't exist
if not os.path.exists(DIR_WEB_JS):
    os.makedirs(DIR_WEB_JS)

# Copy JS files to web extensions
shutil.copytree(DIR_DEV_JS, DIR_WEB_JS, dirs_exist_ok=True)

from .xO_OllamaTextGen import OllamaGenerate
from .xO_OllamaModelSelect import OllamaModelSelector
from .xO_ShowText import ShowText_xO

NODE_CLASS_MAPPINGS = {
    "OllamaTextGen": OllamaGenerate,
    "OllamaModelSelect": OllamaModelSelector,
    "ShowText_xO": ShowText_xO,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "OllamaTextGen": "Ollama Generator xO🤖",
    "OllamaModelSelect": "Ollama Model Selector xO🎯",
    "ShowText_xO": "Show Text xO📝",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]

ascii_art = """
                   YAao,
                    Y8888b,
                  ,oA888888b,
            ,aaad8888888888888888bo,
         ,d888888888888888888888888888b,
       ,888888888888888888888888888888888b,
      d8888888888888888888888888888888888888,
     d888888888888888888888888888888888888888b
    d888888P'                    `Y888888888888,
    88888P'                    Ybaaaa8888888888l
   a8888'                      `Y8888P' `V888888
 d8888888a                                `Y8888
AY/'' `\Y8b                                 ``Y8b
Y'      `YP                                    ~~
        
        >> Neural Nodes by xObiomesh v.0.1 <<
"""
print(ascii_art)