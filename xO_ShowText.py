class ShowText_xO:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text1": ("STRING", {"forceInput": True}),
                "separator": ("STRING", {"default": " "}),
                "output_select": (["text1", "text2", "concatenated"], {"default": "text1"}),
            },
            "optional": {
                "text2": ("STRING", {"forceInput": True}),
            }
        }
    
    INPUT_IS_LIST = True
    RETURN_TYPES = ("STRING", "STRING",)
    RETURN_NAMES = ("text", "concatenated",)
    FUNCTION = "show_value"
    CATEGORY = "💦xObiomesh/Utils"
    OUTPUT_NODE = True
    OUTPUT_IS_LIST = (True, True,)

    def show_value(self, text1, separator, output_select, text2=None):
        print(f"show text1 in console: {text1}")
        if text2:
            print(f"show text2 in console: {text2}")
        
        # Ensure text1 is properly formatted
        if isinstance(text1, str):
            text1_list = [text1]
        elif isinstance(text1, list):
            text1_list = [str(item).strip("[]'\"") for item in text1]
        else:
            text1_list = [str(text1)]
        
        if text2 is None:
            # If no text2, return text1 for both outputs
            return {"ui": {"text1": text1_list}, 
                    "result": (text1_list, text1_list)}
        
        # Ensure text2 is properly formatted
        if isinstance(text2, str):
            text2_list = [text2]
        elif isinstance(text2, list):
            text2_list = [str(item).strip("[]'\"") for item in text2]
        else:
            text2_list = [str(text2)]
        
        # Create concatenated list with proper separator
        concat_list = []
        for t1, t2 in zip(text1_list, text2_list):
            # Clean and concatenate the strings
            t1_clean = str(t1).strip("[]'\"")
            t2_clean = str(t2).strip("[]'\"")
            concat_list.append(f"{t1_clean}{separator}{t2_clean}")
        
        # Ensure output_select is valid
        if output_select not in ["text1", "text2", "concatenated"]:
            output_select = "text1"  # Default to text1 if invalid selection
        
        # Select output based on user choice
        if output_select == "text1":
            selected_output = text1_list
        elif output_select == "text2":
            selected_output = text2_list
        else:  # concatenated
            selected_output = concat_list
        
        # Always return concatenated list as second output
        return {"ui": {"text1": text1_list, "text2": text2_list}, 
                "result": (selected_output, concat_list)}