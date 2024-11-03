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

# Handle run counter
from .init.counter import RunCounter
counter = RunCounter(THIS_DIR)
run_count = counter.increment()

from .xO_OllamaTextGen import OllamaGenerate
from .xO_OllamaModelSelect import OllamaModelSelector
from .xO_ShowText import ShowText_xO
from .xO_ComfyUIPortRunner import xO_ComfyUIPortRunner
from .xO_TestScriptRunner import xO_TestScriptRunner
from .xO_WorkflowRunner import xO_WorkflowRunner
from .init.display import display_init_info

NODE_CLASS_MAPPINGS = {
    "OllamaTextGen": OllamaGenerate,
    "OllamaModelSelect": OllamaModelSelector,
    "ShowText_xO": ShowText_xO,
    "xO_ComfyUIPortRunner": xO_ComfyUIPortRunner,
    "xO_TestScriptRunner": xO_TestScriptRunner,
    "xO_WorkflowRunner": xO_WorkflowRunner,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "OllamaTextGen": "Ollama Generator xO🤖",
    "OllamaModelSelect": "Ollama Model Selector xO🎯",
    "ShowText_xO": "Show Text xO📝",
    "xO_ComfyUIPortRunner": "🚀 ComfyUI Port Runner",
    "xO_TestScriptRunner": "🧪 Test Script Runner",
    "xO_WorkflowRunner": "🔄 Workflow Runner",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]

# Display initialization information
display_init_info(run_count, 'elephant')

__version__ = "0.2.1"
