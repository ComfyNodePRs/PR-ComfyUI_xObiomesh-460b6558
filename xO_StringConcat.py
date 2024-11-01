class StringConcat:
    def __init__(self):
        self.input_count = 1
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "separator": ("STRING", {
                    "default": " ",
                    "multiline": False,
                    "tooltip": "String to insert between concatenated strings"
                }),
            },
            "hidden": {"unique_id": "UNIQUE_ID"},
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("concatenated_text",)
    FUNCTION = "concatenate"
    CATEGORY = "⚜ xObiomesh/Text_Editing"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def concatenate(self, separator, unique_id=None, **kwargs):
        # Get all connected string inputs
        strings = []
        i = 1
        while f"string_{i}" in kwargs:
            value = kwargs[f"string_{i}"]
            if value is not None and value != "":
                strings.append(value)
            i += 1
        
        # Update input count for next execution if all current inputs are used
        if i - 1 == self.input_count and len(strings) == self.input_count:
            self.input_count += 1
        
        # Join all strings with the separator
        result = separator.join(strings)
        return (result,)

    @property
    def OPTIONAL_INPUTS(self):
        return {
            f"string_{i}": ("STRING", {"default": "", "multiline": True})
            for i in range(1, self.input_count + 1)
        }