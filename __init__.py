from .xO_OllamaTextGen import OllamaGenerate
from .xO_OllamaModelSelect import OllamaModelSelector
#from .MISC.broken_nodes.xO_StringConcat import StringConcat

NODE_CLASS_MAPPINGS = {
    "OllamaTextGen": OllamaGenerate,
    "OllamaModelSelect": OllamaModelSelector,
 #   "StringConcat": StringConcat
    
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "OllamaTextGen": "Ollama Generator xO🤖",
    "OllamaModelSelect": "Ollama Model Selector xO🎯",
 #   "StringConcat": "String Concatenator xO🔗"
}

ascii_art = """
                   YAao,
                    Y8888b,
                  ,oA8888888b,
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
        
        >> Naughty Nodes by xObiomesh v.0.1 <<
"""
print(ascii_art)

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]