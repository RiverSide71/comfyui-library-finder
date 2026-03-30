# A ComfyUI node for finding the custom nodes that use an installed python library
# --------------------------------------------------------------------------------
# Node Registration
# --------------------------------------------------------------------------------

from .library_finder import LibraryFinderNode

NODE_CLASS_MAPPINGS = {
    "LibraryFinder": LibraryFinderNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LibraryFinder": "Library Finder 🔍",
}