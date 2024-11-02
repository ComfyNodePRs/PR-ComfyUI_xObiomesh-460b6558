
I'll help you create a function decider node for ComfyUI that can intelligently route inputs to different functions based on content analysis. Based on the workflow examples in the codebase, we'll need to create a node that integrates well with the existing Ollama nodes and ComfyUI's node system.
Here's how we can implement this:
This implementation:
Creates a FunctionDecider node that takes text input and analyzes it to determine the appropriate function to call
Provides configurable options:
Required text input
Customizable system prompt
Optional custom functions configuration via JSON
Returns three outputs:
The decided function name
The original text (passed through)
Metadata about the decision in JSON format
Uses a simple rule-based system to make decisions, which can be extended or modified
To use this node in a workflow:
You can then connect the outputs to different nodes based on the function decision:
function output can be used to control workflow routing
text output can be passed to the chosen function
metadata output can be used for logging or additional processing
To extend this further, you could:
Add more sophisticated decision-making logic using an LLM
Implement custom routing rules
Add support for more function types
Include confidence scores for decisions
Add validation for custom function configurations
Let me know if you'd like me to explain any part in more detail or help with additional features!
Add more sophisticated decision-making logic using an LLM
ose the other available nodes

I'll help enhance the function decider by integrating Ollama LLM for more sophisticated decision-making. We'll modify the xO_FunctionDecider.py to use the Ollama model for analysis.
Here's the improved version:
Key improvements made:
Added LLM-based decision making using Ollama:
Takes model_name as input (defaults to dolphin-mixtral)
Uses a more detailed system prompt for better analysis
Queries Ollama API for sophisticated decision making
Enhanced system prompt:
More detailed function descriptions
Includes consideration points for analysis
Clearer instructions for response format
Improved fallback mechanism:
Uses LLM as primary decision maker
Falls back to rule-based system if LLM fails
Maintains backward compatibility
Enhanced metadata:
Includes LLM decision
Shows which model was used
Indicates whether decision was LLM or rule-based
To use this in a workflow:
This enhanced version provides more accurate function routing by leveraging the LLM's understanding of context and intent, while maintaining reliability through the rule-based fallback system.
add new node to the init file

I'll help you add the new xO_FunctionDecider node to the init.py file. Here's how we can update it:
This update:
Imports the new xO_FunctionDecider class
Adds it to the NODE_CLASS_MAPPINGS dictionary
Adds a display name for it in NODE_DISPLAY_NAME_MAPPINGS with an appropriate emoji
The node will now be available in ComfyUI with the display name "Function Router xO🔀" and can be used in workflows as shown in the example_workflow.json.
@show_text.py rename function to mqtch workspace

I'll help you modify the show_text.py to match the workspace naming convention and integrate it with the existing nodes. Here's the updated version:
And let's update the init.py to include the new node:
Key changes made:
Renamed the class from ShowText to xO_ShowText to match naming convention
Updated the CATEGORY to match the xObiomesh namespace: "💦xObiomesh/Utils📝"
Added the node to NODE_CLASS_MAPPINGS and NODE_DISPLAY_NAME_MAPPINGS
Kept all the original functionality but aligned with the workspace style
Added appropriate emoji for consistency with other nodes
The node will now appear in the ComfyUI interface under the xObiomesh category with other nodes in the collection.
