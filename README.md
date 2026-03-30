# comfyui-library-finder
This repo ocntains a custom node which helps you find which custom nodes are importing a particular library.

# Library Finder

After wanting to remove some libraries but wondering which of my custom nodes were still using it, I have created a custom node that might help find the answer from within ComfyUI.

The Library Finder node allows as input a single library or multiple libraries separated by a comma. It will check through both .py and requirements.txt files in your ComfyUI/custom_nodes folder. The node provides its output as a string, so attach your favorite text display node to see the result of your search. 

## Installation

### Manual
1. Clone this repo into your `ComfyUI/custom_nodes/` folder:
```bash
git clone https://github.com/RiverSide71/comfyui-library-finder.git
```

2. Restart ComfyUI

## Preview

![Library Finder Node](library_finder.png)  

**Known limitations**:
  - None yet, but please reach out and let me know.
