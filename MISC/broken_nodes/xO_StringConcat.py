class StringConcat:
    def __init__(self):
        self.input_count = 2  # Start with two inputs
    
    @classmethod
    def INPUT_TYPES(cls):
        inputs = {
            "required": {
                "separator1": ("STRING", {
                    "default": " ",
                    "multiline": False,
                    "tooltip": "First string to insert between concatenated strings"
                }),
                "separator2": ("STRING", {
                    "default": ", ",
                    "multiline": False,
                    "tooltip": "Second string to insert between concatenated strings"
                }),
                "string_1": ("STRING", {
                    "forceInput": True,
                    "default": "",
                }),
                "string_2": ("STRING", {
                    "forceInput": True,
                    "default": "",
                }),
            },
            "hidden": {"unique_id": "UNIQUE_ID"},
            "optional": {
                f"string_{i}": ("STRING", {
                    "forceInput": True,
                    "default": "",
                }) for i in range(3, 6)  # Add slots 3-5
            }
        }
        return inputs
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("concatenated_text",)
    FUNCTION = "concatenate"
    CATEGORY = "💦xObiomesh/Text_Editing"
    HIDE = True

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def concatenate(self, separator1, separator2, string_1, string_2, unique_id=None, **kwargs):
        strings = []
        
        # Add the required strings first
        if string_1 and string_1.strip():
            strings.append(string_1)
        if string_2 and string_2.strip():
            strings.append(string_2)
            
        # Add any additional strings from kwargs
        for i in range(3, 6):
            if f"string_{i}" in kwargs and kwargs[f"string_{i}"]:
                value = kwargs[f"string_{i}"]
                if value and value.strip():
                    strings.append(value)

        # Ensure at least two strings are provided
        if len(strings) < 2:
            return ("Error: At least two strings are required.",)
        
        # Join all strings with the first separator, then the second for the last string
        result = separator1.join(strings[:-1]) + separator2 + strings[-1]
        return (result,)