import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

app.registerExtension({
    name: "xObiomesh.ShowText_xO",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== "ShowText_xO") {
            return;
        }

        // Add separator and output_select widgets during node creation
        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function() {
            onNodeCreated?.apply(this, arguments);
            
            // Initialize widgets array if it doesn't exist
            this.widgets = this.widgets || [];
            
            // Add separator widget if it doesn't exist
            if (!this.widgets.find(w => w.name === "separator")) {
                const widget = ComfyWidgets["STRING"](this, "separator", ["STRING", { default: " " }], app);
                if (widget && widget.widget && widget.widget.inputEl) {
                    widget.widget.inputEl.style.width = "30px";
                }
            }

            // Add output select combo if it doesn't exist
            if (!this.widgets.find(w => w.name === "output_select")) {
                ComfyWidgets["COMBO"](this, "output_select", ["COMBO", {
                    default: "text1",
                    values: ["text1", "text2", "concatenated"]
                }], app);
            }
        };

        // Helper function to remove all widgets except separator and output_select
        nodeType.prototype.clearWidgets = function() {
            if (!this.widgets) return;
            
            // Remove widgets from DOM and node
            for (const w of this.widgets) {
                if (w.name !== "separator" && w.name !== "output_select") {
                    if (w.inputEl && w.inputEl.parentNode) {
                        w.inputEl.parentNode.removeChild(w.inputEl);
                    }
                    w.onRemoved?.();
                }
            }
            
            // Keep separator and output_select widgets
            const persistentWidgets = this.widgets.filter(w => 
                w.name === "separator" || w.name === "output_select"
            );
            this.widgets = persistentWidgets;
        };

        // Helper function to create a new widget
        nodeType.prototype.createWidget = function(name, value) {
            const widget = ComfyWidgets["STRING"](this, name, ["STRING", { multiline: true }], app);
            if (widget && widget.widget) {
                widget.widget.inputEl.readOnly = true;
                widget.widget.inputEl.style.opacity = 0.6;
                widget.widget.value = value;
            }
            return widget.widget;
        };

        // When the node is executed we will be sent the input text, display this in the widgets
        const onExecuted = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function(message) {
            onExecuted?.apply(this, arguments);

            // Clear all existing widgets except separator and output_select
            this.clearWidgets();

            // Create new text1 widgets
            if (message.text1) {
                message.text1.forEach((text, index) => {
                    this.createWidget(`text1_${index}`, text);
                });
            }

            // Create new text2 widgets
            if (message.text2) {
                message.text2.forEach((text, index) => {
                    this.createWidget(`text2_${index}`, text);
                });
            }

            this.setSize(this.computeSize());
        };

        // Clean up when node is removed
        const onRemoved = nodeType.prototype.onRemoved;
        nodeType.prototype.onRemoved = function() {
            this.clearWidgets();
            onRemoved?.apply(this, arguments);
        };

        // Compute proper size based on widgets
        nodeType.prototype.computeSize = function() {
            const width = Math.max(200, ...this.widgets.map(w => w.inputEl?.clientWidth || 0));
            const height = this.widgets.reduce((h, w) => h + (w.inputEl?.clientHeight || 20), 40);
            return [width + 20, height + 20];
        };
    }
}); 