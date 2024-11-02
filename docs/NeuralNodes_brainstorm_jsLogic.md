In the ComfyUI-Custom-Scripts codebase, the creation and registration of nodes follow a structured workflow. Here's a general explanation of how nodes are created and registered in the ComfyUI environment, based on the provided code snippets:
1. Node Definition and Registration:
Nodes are defined as classes that extend from a base class, typically LiteGraph.LGraphNode. This is evident in the PresetTextNode class, which is defined and registered in the presetText.js file.
The registration of nodes is done using LiteGraph.registerNodeType, where the node type and its properties are specified.
Node Initialization:
During initialization, nodes can set up their inputs, outputs, and widgets. For example, in the PresetTextNode, widgets are added using this.addWidget.
Nodes can also define their behavior when added to the graph, as seen in the onAdded method in betterCombos.js.
Node Configuration:
Nodes can have configuration methods like onConfigure to set up their state when the graph is loaded or when the node is executed.
The onConfigure method is used to restore the node's state from saved data.
Node Execution:
Nodes can define what happens when they are executed using methods like onExecuted. This is where the node's main functionality is implemented.
For example, in showText.js, the onExecuted method is used to display input text on the node.
Menu Options and Extensions:
Nodes can have additional menu options added to them using the getExtraMenuOptions method. This allows for custom actions to be performed on the node.
Extensions can be registered using app.registerExtension, which allows for additional functionality to be added to nodes or the UI.
Dynamic Behavior:
Nodes can dynamically change their behavior based on user interactions or other conditions. This is often done by modifying the node's properties or by adding/removing widgets.
Here are some specific code references that illustrate these concepts:
Node Definition and Registration:
	registerCustomNodes() {
		class PresetTextNode extends LiteGraph.LGraphNode {
			constructor() {
				super();
				this.title = "Preset Text 🐍";
				this.isVirtualNode = true;
				this.serialize_widgets = true;
				this.addOutput("text", "STRING");

				const widget = this.addWidget("combo", "value", presets[0].name, () => {}, {
					values: presets.map((p) => p.name),
				});
				this.addWidget("button", "Manage", "Manage", () => {
					const container = document.createElement("div");
					Object.assign(container.style, {
						display: "grid",
						gridTemplateColumns: "1fr 1fr",
						gap: "10px",
					});

					const addNew = document.createElement("button");
					addNew.textContent = "Add New";
					addNew.classList.add("pysssss-presettext-addnew");
					Object.assign(addNew.style, {
						fontSize: "13px",
						gridColumn: "1 / 3",
						color: "dodgerblue",
						width: "auto",
						textAlign: "center",
					});
					addNew.onclick = () => {
						addRow({ name: "", value: "" });
					};
					container.append(addNew);

					function addRow(p) {
						const name = document.createElement("input");
						const nameLbl = document.createElement("label");
						name.value = p.name;
						nameLbl.textContent = "Name:";
						nameLbl.append(name);

						const value = document.createElement("input");
						const valueLbl = document.createElement("label");
						value.value = p.value;
						valueLbl.textContent = "Value:";
						valueLbl.append(value);

						addNew.before(nameLbl, valueLbl);
					}
					for (const p of presets) {
						addRow(p);
					}

					const help = document.createElement("span");
					help.textContent = "To remove a preset set the name or value to blank";
					help.style.gridColumn = "1 / 3";
					container.append(help);

					dialog.show("");
					dialog.textElement.append(container);
				});
				const dialog = new app.ui.dialog.constructor();
				dialog.element.classList.add("comfy-settings");

				const closeButton = dialog.element.querySelector("button");
				closeButton.textContent = "CANCEL";
				const saveButton = document.createElement("button");
				saveButton.textContent = "SAVE";
				saveButton.onclick = function () {
					const inputs = dialog.element.querySelectorAll("input");
					const p = [];
					for (let i = 0; i < inputs.length; i += 2) {
						const n = inputs[i];
						const v = inputs[i + 1];
						if (!n.value.trim() || !v.value.trim()) {
							continue;
						}
						p.push({ name: n.value, value: v.value });
					}

					widget.options.values = p.map((p) => p.name);
					if (!widget.options.values.includes(widget.value)) {
						widget.value = widget.options.values[0];
					}

					presets = p;
					localStorage.setItem(id, JSON.stringify(presets));

					dialog.close();
				};

				closeButton.before(saveButton);

				this.applyToGraph = function (workflow) {
					// For each output link copy our value over the original widget value
					if (this.outputs[0].links && this.outputs[0].links.length) {
						for (const l of this.outputs[0].links) {
							const link_info = app.graph.links[l];
							const outNode = app.graph.getNodeById(link_info.target_id);
							const outIn = outNode && outNode.inputs && outNode.inputs[link_info.target_slot];
							if (outIn.widget) {
								const w = outNode.widgets.find((w) => w.name === outIn.widget.name);
								if (!w) continue;
								const preset = presets.find((p) => p.name === widget.value);
								if (!preset) {
									this[MISSING] = true;
									app.graph.setDirtyCanvas(true, true);
									const msg = `Preset text '${widget.value}' not found. Please fix this and queue again.`;
									throw new Error(msg);
								}
								delete this[MISSING];
								w.value = preset.value;
							}
						}
					}
				};
			}
		}
		LiteGraph.registerNodeType(
			"PresetText|pysssss",
			Object.assign(PresetTextNode, {
				title: "Preset Text 🐍",
			})
		);

		PresetTextNode.category = "utils";
	}
Node Initialization:

	async beforeRegisterNodeDef(nodeType, nodeData, app) {
		const isCkpt = nodeType.comfyClass === CHECKPOINT_LOADER;
		const isLora = nodeType.comfyClass === LORA_LOADER;
		if (isCkpt || isLora) {
			const onAdded = nodeType.prototype.onAdded;
			nodeType.prototype.onAdded = function () {
				onAdded?.apply(this, arguments);
				const { widget: exampleList } = ComfyWidgets["COMBO"](this, "example", [[""]], app);

				let exampleWidget;

				const get = async (route, suffix) => {
					const url = encodeURIComponent(`${getType(nodeType)}${suffix || ""}`);
					return await api.fetchApi(`/pysssss/${route}/${url}`);
				};

				const getExample = async () => {
					if (exampleList.value === "[none]") {
						if (exampleWidget) {
							exampleWidget.inputEl.remove();
							exampleWidget = null;
							this.widgets.length -= 1;
						}
						return;
					}

					const v = this.widgets[0].value.content;
					const pos = v.lastIndexOf(".");
					const name = v.substr(0, pos);
					let exampleName = exampleList.value;
					let viewPath = `/${name}`;
					if (exampleName === "notes") {
						viewPath += ".txt";
					} else {
						viewPath += `/${exampleName}`;
					}
					const example = await (await get("view", viewPath)).text();
					if (!exampleWidget) {
						exampleWidget = ComfyWidgets["STRING"](this, "prompt", ["STRING", { multiline: true }], app).widget;
						exampleWidget.inputEl.readOnly = true;
						exampleWidget.inputEl.style.opacity = 0.6;
					}
					exampleWidget.value = example;
				};
				const exampleCb = exampleList.callback;
				exampleList.callback = function () {
					getExample();
					return exampleCb?.apply(this, arguments) ?? exampleList.value;
				};


				const listExamples = async () => {
					exampleList.disabled = true;
					exampleList.options.values = ["[none]"];
					exampleList.value = "[none]";
					let examples = [];
					if (this.widgets[0].value?.content) {
						try {
							examples = await (await get("examples", `/${this.widgets[0].value.content}`)).json();
						} catch (error) {}
					}
					exampleList.options.values = ["[none]", ...examples];
					exampleList.value = exampleList.options.values[+!!examples.length];
					exampleList.callback();
					exampleList.disabled = !examples.length;
					app.graph.setDirtyCanvas(true, true);
				};

				// Expose function to update examples
				nodeType.prototype["pysssss.updateExamples"] = listExamples;

				const modelWidget = this.widgets[0];
				const modelCb = modelWidget.callback;
				let prev = undefined;
				modelWidget.callback = function () {
					const ret = modelCb?.apply(this, arguments) ?? modelWidget.value;
					let v = ret;
					if (ret?.content) {
						v = ret.content;
					}
					if (prev !== v) {
						listExamples();
						prev = v;
					}
					return ret;
				};
				setTimeout(() => {
					modelWidget.callback();
				}, 30);
			};
Node Initialization:

	async beforeRegisterNodeDef(nodeType, nodeData, app) {
		const isCkpt = nodeType.comfyClass === CHECKPOINT_LOADER;
		const isLora = nodeType.comfyClass === LORA_LOADER;
		if (isCkpt || isLora) {
			const onAdded = nodeType.prototype.onAdded;
			nodeType.prototype.onAdded = function () {
				onAdded?.apply(this, arguments);
				const { widget: exampleList } = ComfyWidgets["COMBO"](this, "example", [[""]], app);

				let exampleWidget;

				const get = async (route, suffix) => {
					const url = encodeURIComponent(`${getType(nodeType)}${suffix || ""}`);
					return await api.fetchApi(`/pysssss/${route}/${url}`);
				};

				const getExample = async () => {
					if (exampleList.value === "[none]") {
						if (exampleWidget) {
							exampleWidget.inputEl.remove();
							exampleWidget = null;
							this.widgets.length -= 1;
						}
						return;
					}

					const v = this.widgets[0].value.content;
					const pos = v.lastIndexOf(".");
					const name = v.substr(0, pos);
					let exampleName = exampleList.value;
					let viewPath = `/${name}`;
					if (exampleName === "notes") {
						viewPath += ".txt";
					} else {
						viewPath += `/${exampleName}`;
					}
					const example = await (await get("view", viewPath)).text();
					if (!exampleWidget) {
						exampleWidget = ComfyWidgets["STRING"](this, "prompt", ["STRING", { multiline: true }], app).widget;
						exampleWidget.inputEl.readOnly = true;
						exampleWidget.inputEl.style.opacity = 0.6;
					}
					exampleWidget.value = example;
				};
				const exampleCb = exampleList.callback;
				exampleList.callback = function () {
					getExample();
					return exampleCb?.apply(this, arguments) ?? exampleList.value;
				};


				const listExamples = async () => {
					exampleList.disabled = true;
					exampleList.options.values = ["[none]"];
					exampleList.value = "[none]";
					let examples = [];
					if (this.widgets[0].value?.content) {
						try {
							examples = await (await get("examples", `/${this.widgets[0].value.content}`)).json();
						} catch (error) {}
					}
					exampleList.options.values = ["[none]", ...examples];
					exampleList.value = exampleList.options.values[+!!examples.length];
					exampleList.callback();
					exampleList.disabled = !examples.length;
					app.graph.setDirtyCanvas(true, true);
				};

				// Expose function to update examples
				nodeType.prototype["pysssss.updateExamples"] = listExamples;

				const modelWidget = this.widgets[0];
				const modelCb = modelWidget.callback;
				let prev = undefined;
				modelWidget.callback = function () {
					const ret = modelCb?.apply(this, arguments) ?? modelWidget.value;
					let v = ret;
					if (ret?.content) {
						v = ret.content;
					}
					if (prev !== v) {
						listExamples();
						prev = v;
					}
					return ret;
				};
				setTimeout(() => {
					modelWidget.callback();
				}, 30);
			};
Node Execution:

import { app } from "../../../scripts/app.js";
import { ComfyWidgets } from "../../../scripts/widgets.js";

// Displays input text on a node
app.registerExtension({
	name: "pysssss.ShowText",
	async beforeRegisterNodeDef(nodeType, nodeData, app) {
		if (nodeData.name === "ShowText|pysssss") {
			function populate(text) {
				if (this.widgets) {
					for (let i = 1; i < this.widgets.length; i++) {
						this.widgets[i].onRemove?.();
					}
					this.widgets.length = 1;
				}

				const v = [...text];
				if (!v[0]) {
					v.shift();
				}
				for (const list of v) {
					const w = ComfyWidgets["STRING"](this, "text2", ["STRING", { multiline: true }], app).widget;
					w.inputEl.readOnly = true;
					w.inputEl.style.opacity = 0.6;
					w.value = list;
				}

				requestAnimationFrame(() => {
					const sz = this.computeSize();
					if (sz[0] < this.size[0]) {
						sz[0] = this.size[0];
					}
					if (sz[1] < this.size[1]) {
						sz[1] = this.size[1];
					}
					this.onResize?.(sz);
					app.graph.setDirtyCanvas(true, false);
				});
			}

			// When the node is executed we will be sent the input text, display this in the widget
			const onExecuted = nodeType.prototype.onExecuted;
			nodeType.prototype.onExecuted = function (message) {
				onExecuted?.apply(this, arguments);
				populate.call(this, message.text);
			};

			const onConfigure = nodeType.prototype.onConfigure;
			nodeType.prototype.onConfigure = function () {
				onConfigure?.apply(this, arguments);
				if (this.widgets_values?.length) {
					populate.call(this, this.widgets_values.slice(+this.widgets_values.length > 1));
				}
			};
		}
	},
Menu Options and Extensions

	beforeRegisterNodeDef(nodeType) {
		const getExtraMenuOptions = nodeType.prototype.getExtraMenuOptions;
		nodeType.prototype.getExtraMenuOptions = function (_, options) {
			if (this.widgets) {
				for (const type in lookups) {
					addTypeOptions(this, type, options);
				}
			}

			return getExtraMenuOptions?.apply(this, arguments);
		};
