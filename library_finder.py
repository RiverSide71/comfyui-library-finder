import os
import re
from importlib.metadata import version as pkg_version, PackageNotFoundError

NODE_CATEGORY = "riversidenodes"

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _get_installed_version(lib: str) -> str:
    """Return the installed version string, or 'not installed' if absent."""
    # Strip any version specifier (>=1.0, ==2.3, etc.) to get the bare package name
    bare = re.split(r"[><=!~\s;@]", lib, maxsplit=1)[0].strip()
    try:
        return pkg_version(bare)
    except PackageNotFoundError:
        return "not installed"


def _get_custom_nodes_dir():
    """Return the custom_nodes directory (parent of this node's folder)."""
    this_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(this_dir), os.path.basename(this_dir)


def _check_requirements(req_path: str, libs: list[str]) -> dict[str, str]:
    """
    Return a dict of {lib: version_specifier} for every lib found in a
    requirements.txt file.  version_specifier is an empty string when the
    requirement carries no version constraint (e.g. bare `torch`).
    """
    found: dict[str, str] = {}
    VERSION_RE = re.compile(
        r"(\s*(?:[><!~]=|===|[><!~=]=?)\s*[^\s,;#]+(?:\s*,\s*(?:[><!~]=|===|[><!~=]=?)\s*[^\s,;#]+)*)"
    )
    try:
        with open(req_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        for lib in libs:
            # Separate the bare name from any user-supplied specifier
            bare = re.split(r"[><=!~\s;@]", lib, maxsplit=1)[0].strip()
            user_spec = lib[len(bare):].strip()  # e.g. ">=10.3.0" or ""
            for raw_line in lines:
                line = raw_line.split("#")[0].strip()
                if not line:
                    continue
                normalised_line = re.sub(r"[-_]", "-", line.lower())
                normalised_lib  = re.sub(r"[-_]", "-", bare.lower())
                pattern = re.compile(
                    r"^" + re.escape(normalised_lib) + r"(?=[^a-zA-Z0-9_-]|$)"
                )
                if not pattern.match(normalised_line):
                    continue
                # Slice using bare name length to correctly extract version
                remainder = line[len(bare):].strip()
                version_match = VERSION_RE.match(remainder)
                file_spec = version_match.group(1).strip() if version_match else ""
                # If user specified a version, only include if it matches the file
                if user_spec and file_spec != user_spec:
                    break
                found[lib] = file_spec
                break
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
            # Strip any version specifier — Python imports never contain them
            bare = re.split(r"[><=!~\s;@]", lib, maxsplit=1)[0].strip()
            escaped = re.escape(bare)
            patterns = [
                rf"^\s*import\s+{escaped}(?:[\s,.]|$)",
                rf"^\s*from\s+{escaped}(?:[\s.]|$)",
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

        # Keep full specifier intact — filtering in _check_requirements depends on it
        lib_names = [l.strip().lower() for l in libraries.split(",") if l.strip()]
        if not lib_names:
            return ("⚠️  No library names provided.",)

        # results[lib][node_folder] = {"sources": [str, ...], "version": str | None}
        results: dict[str, dict[str, dict]] = {lib: {} for lib in lib_names}

        for entry in sorted(os.listdir(custom_nodes_dir)):
            node_path = os.path.join(custom_nodes_dir, entry)
            if not os.path.isdir(node_path):
                continue
            if entry == self_folder:
                continue

            # --- requirements.txt ---
            req_path = os.path.join(node_path, "requirements.txt")
            if os.path.isfile(req_path):
                for lib, version in _check_requirements(req_path, lib_names).items():
                    entry_data = results[lib].setdefault(entry, {"sources": [], "version": None})
                    entry_data["sources"].append("requirements.txt")
                    entry_data["version"] = version if version else None

            # --- .py files (walk subdirectories too) ---
            for root, dirs, files in os.walk(node_path):
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
                        entry_data = results[lib].setdefault(entry, {"sources": [], "version": None})
                        if rel not in entry_data["sources"]:
                            entry_data["sources"].append(rel)

        # ------------------------------------------------------------------
        # Format output
        # ------------------------------------------------------------------
        lines: list[str] = []
        lines.append(f"Scanned: {custom_nodes_dir}")
        lines.append("=" * 60)

        for lib in lib_names:
            installed = _get_installed_version(lib)
            lines.append(f"\n📦 Library: {lib}  (installed: {installed})")
            if not results[lib]:
                lines.append("   (not found in any custom node)")
            else:
                for folder, data in sorted(results[lib].items()):
                    version_tag = f"  [version: {data['version']}]" if data["version"] else "  [no version pinned]"
                    lines.append(f"\n   🔹 {folder}{version_tag}")
                    for src in sorted(data["sources"]):
                        lines.append(f"        → {src}")

        lines.append("\n" + "=" * 60)
        total = sum(len(v) for v in results.values())
        lines.append(f"Total custom-node matches: {total}")

        return ("\n".join(lines),)