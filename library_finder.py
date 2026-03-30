import os
import re

NODE_CATEGORY = "riversidenodes"

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _get_custom_nodes_dir():
    """Return the custom_nodes directory (parent of this node's folder)."""
    this_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(this_dir), os.path.basename(this_dir)


def _check_requirements(req_path: str, libs: list[str]) -> set[str]:
    """Return the subset of libs mentioned in a requirements.txt file."""
    found = set()
    try:
        with open(req_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        for lib in libs:
            pattern = re.compile(
                r"(?:^|[^a-zA-Z0-9_-])" + re.escape(lib) + r"(?:[^a-zA-Z0-9_-]|$)",
                re.IGNORECASE,
            )
            if any(pattern.search(line) for line in lines):
                found.add(lib)
    except Exception:
        pass
    return found


def _check_py_file(filepath: str, libs: list[str]) -> set[str]:
    """Return the subset of libs imported in a .py file."""
    found = set()
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        for lib in libs:
            escaped = re.escape(lib)
            patterns = [
                rf"^\s*import\s+{escaped}(?:[\s,.]|$)",   # import lib  /  import lib.x
                rf"^\s*from\s+{escaped}(?:[\s.]|$)",       # from lib import  /  from lib.x
            ]
            if any(re.search(p, content, re.MULTILINE) for p in patterns):
                found.add(lib)
    except Exception:
        pass
    return found


# ---------------------------------------------------------------------------
# The node
# ---------------------------------------------------------------------------

class LibraryFinderNode:
    CATEGORY = NODE_CATEGORY
    """
    Scans every custom node folder for .py imports and requirements.txt
    entries matching the supplied comma-separated library names.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "libraries": (
                    "STRING",
                    {
                        "default": "torch, numpy",
                        "multiline": False,
                        "placeholder": "e.g., torch, opencv-python, requests",
                    },
                ),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("result",)
    FUNCTION = "find"
    CATEGORY = "utils"
    OUTPUT_NODE = True

    # ------------------------------------------------------------------

    def find(self, libraries: str):
        custom_nodes_dir, self_folder = _get_custom_nodes_dir()

        # Parse library list – normalise to lowercase for matching
        lib_names = [l.strip().lower() for l in libraries.split(",") if l.strip()]
        if not lib_names:
            return ("⚠️  No library names provided.",)

        # results[lib] = {node_folder: [source_file, ...]}
        results: dict[str, dict[str, list[str]]] = {lib: {} for lib in lib_names}

        for entry in sorted(os.listdir(custom_nodes_dir)):
            node_path = os.path.join(custom_nodes_dir, entry)
            if not os.path.isdir(node_path):
                continue
            if entry == self_folder:
                continue  # skip ourselves

            # --- requirements.txt ---
            req_path = os.path.join(node_path, "requirements.txt")
            if os.path.isfile(req_path):
                for lib in _check_requirements(req_path, lib_names):
                    results[lib].setdefault(entry, [])
                    results[lib][entry].append("requirements.txt")

            # --- .py files (walk subdirectories too) ---
            for root, dirs, files in os.walk(node_path):
                # Skip hidden dirs and __pycache__
                dirs[:] = [
                    d for d in dirs
                    if not d.startswith(".") and d != "__pycache__"
                ]
                for fname in files:
                    if not fname.endswith(".py"):
                        continue
                    fpath = os.path.join(root, fname)
                    rel = os.path.relpath(fpath, node_path)
                    for lib in _check_py_file(fpath, lib_names):
                        results[lib].setdefault(entry, [])
                        if rel not in results[lib][entry]:
                            results[lib][entry].append(rel)

        # ------------------------------------------------------------------
        # Format output
        # ------------------------------------------------------------------
        lines: list[str] = []
        lines.append(f"Scanned: {custom_nodes_dir}")
        lines.append("=" * 60)

        for lib in lib_names:
            lines.append(f"\n📦 Library: {lib}")
            if not results[lib]:
                lines.append("   (not found in any custom node)")
            else:
                for folder, sources in sorted(results[lib].items()):
                    lines.append(f"\n   🔹 {folder}")
                    for src in sorted(sources):
                        lines.append(f"        → {src}")

        lines.append("\n" + "=" * 60)
        total = sum(len(v) for v in results.values())
        lines.append(f"Total custom-node matches: {total}")

        return ("\n".join(lines),)