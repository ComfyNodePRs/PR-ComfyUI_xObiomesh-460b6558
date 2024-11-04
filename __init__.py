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
#create file and init to 0 if it doesn't exist
if not os.path.exists(f'{THIS_DIR}/.run_counter'):
    with open(f'{THIS_DIR}/.run_counter', 'w') as f:
        f.write('0')
from .init.counter import RunCounter
counter = RunCounter(THIS_DIR)
run_count_normalized = counter.increment()
# Calculate the divisor based on the run count
divisor = 10 ** (len(str(run_count_normalized)) - 1)
run_count_normalized = run_count_normalized / divisor
run_count = run_count_normalized * divisor
#make run count an integer
run_count = int(run_count)


from .xO_OllamaTextGen import OllamaGenerate
from .xO_OllamaModelSelect import OllamaModelSelector
from .xO_ShowText import ShowText_xO
from .xO_ComfyUIPortRunner import xO_ComfyUIPortRunner
from .xO_TestScriptRunner import xO_TestScriptRunner
from .xO_WorkflowRunner import xO_WorkflowRunner
from .xO_GetImageFilename import xO_GetImageFilename
from .xO_LoadRecentFile import xO_LoadRecentFile
from .init.display import display_init_info, display_ascii_art

NODE_CLASS_MAPPINGS = {
    "OllamaTextGen": OllamaGenerate,
    "OllamaModelSelect": OllamaModelSelector,
    "ShowText_xO": ShowText_xO,
    "xO_ComfyUIPortRunner": xO_ComfyUIPortRunner,
    "xO_TestScriptRunner": xO_TestScriptRunner,
    "xO_WorkflowRunner": xO_WorkflowRunner,
    "xO_GetImageFilename": xO_GetImageFilename,
    "xO_LoadRecentFile": xO_LoadRecentFile,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "OllamaTextGen": "Ollama Generator xO🤖",
    "OllamaModelSelect": "Ollama Model Selector xO🎯",
    "ShowText_xO": "Show Text xO📝",
    "xO_ComfyUIPortRunner": "🚀 ComfyUI Port Runner",
    "xO_TestScriptRunner": "🧪 Test Script Runner",
    "xO_WorkflowRunner": "🔄 Workflow Runner",
    "xO_GetImageFilename": "Get Image Filename",
    "xO_LoadRecentFile": "Load Recent File 📂",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]

# Display initialization information
display_init_info(run_count, run_count_normalized)
display_ascii_art()


__version__ = "0.1.x0"
