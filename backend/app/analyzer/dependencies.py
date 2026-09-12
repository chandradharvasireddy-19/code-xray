import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from app.models.repository import Relationship
from app.analyzer.parser import ImportStatement


# Common Python standard library modules for filtering
STDLIB_MODULES = {
    "abc", "argparse", "array", "ast", "asyncio", "base64", "binascii", "bisect",
    "builtins", "calendar", "cmath", "collections", "concurrent", "contextlib",
    "copy", "csv", "ctypes", "dataclasses", "datetime", "decimal", "difflib",
    "dis", "enum", "errno", "faulthandler", "fcntl", "fnmatch", "fractions",
    "functools", "gc", "glob", "gzip", "hashlib", "heapq", "hmac", "html",
    "http", "imaplib", "inspect", "io", "itertools", "json", "logging", "math",
    "mimetypes", "multiprocessing", "numbers", "operator", "os", "pathlib",
    "pickle", "platform", "pprint", "queue", "random", "re", "secrets", "select",
    "shlex", "shutil", "signal", "socket", "sqlite3", "ssl", "stat", "string",
    "struct", "subprocess", "sys", "tempfile", "textwrap", "threading", "time",
    "tokenize", "traceback", "types", "typing", "unittest", "urllib", "uuid",
    "warnings", "weakref", "zipfile", "zlib"
}


class DependencyAnalyzer:
    """
    Resolves AST import statements into internal code relationships (file -> file)
    and external package dependencies.
    """

    def __init__(self, all_files: List[str]):
        self.all_files = all_files
        self.file_set = set(all_files)
        # Create module lookup maps (e.g., 'services.payment_service' -> 'services/payment_service.py')
        self._module_to_file: Dict[str, str] = {}
        self._build_module_map()

    def _build_module_map(self) -> None:
        for f in self.all_files:
            if not f.endswith(".py"):
                continue
            # Strip .py
            no_ext = f[:-3]
            # Convert slash to dot: e.g. "app/services/payment.py" -> "app.services.payment"
            mod_dot = no_ext.replace("/", ".")
            self._module_to_file[mod_dot] = f

            # Also support without root folder (e.g. "services.payment" if in "app/services/payment.py" or "src/...")
            parts = mod_dot.split(".")
            for i in range(1, len(parts)):
                sub_mod = ".".join(parts[i:])
                if sub_mod not in self._module_to_file:
                    self._module_to_file[sub_mod] = f

    def analyze_file_imports(
        self,
        rel_file: str,
        imports: List[ImportStatement],
    ) -> Tuple[List[Relationship], Dict[str, Set[str]]]:
        """
        Analyze imports in a file.
        Returns:
            - List of internal relationships (Relationship objects)
            - Map of external packages -> set of files importing them
        """
        internal_relationships: List[Relationship] = []
        external_imports: Dict[str, Set[str]] = {}

        for imp in imports:
            # Case 1: Relative import (level > 0)
            if imp.level > 0:
                target_file = self._resolve_relative_import(rel_file, imp.module, imp.level, imp.names)
                if target_file:
                    internal_relationships.append(Relationship(
                        source=rel_file,
                        target=target_file,
                        type="imports",
                        confidence=1.0,
                        line=imp.line,
                        detail=f"from {'.' * imp.level}{imp.module or ''} import {', '.join(imp.names)}",
                    ))
                continue

            # Case 2: from x import y
            if imp.is_from and imp.module:
                target_file = self._resolve_module(imp.module)
                if target_file and target_file != rel_file:
                    internal_relationships.append(Relationship(
                        source=rel_file,
                        target=target_file,
                        type="imports",
                        confidence=1.0,
                        line=imp.line,
                        detail=f"from {imp.module} import {', '.join(imp.names)}",
                    ))
                elif not target_file:
                    # Check if imp.module is external
                    pkg = imp.module.split(".")[0].lower().replace("-", "_")
                    if pkg not in STDLIB_MODULES:
                        if pkg not in external_imports:
                            external_imports[pkg] = set()
                        external_imports[pkg].add(rel_file)

            # Case 3: import x, y
            elif not imp.is_from:
                for name in imp.names:
                    target_file = self._resolve_module(name)
                    if target_file and target_file != rel_file:
                        internal_relationships.append(Relationship(
                            source=rel_file,
                            target=target_file,
                            type="imports",
                            confidence=1.0,
                            line=imp.line,
                            detail=f"import {name}",
                        ))
                    elif not target_file:
                        pkg = name.split(".")[0].lower().replace("-", "_")
                        if pkg not in STDLIB_MODULES:
                            if pkg not in external_imports:
                                external_imports[pkg] = set()
                            external_imports[pkg].add(rel_file)

        return internal_relationships, external_imports

    def _resolve_module(self, mod_name: str) -> Optional[str]:
        # Direct match in map
        if mod_name in self._module_to_file:
            return self._module_to_file[mod_name]

        # Check if mod_name is a package directory containing __init__.py
        as_dir_init = mod_name.replace(".", "/") + "/__init__.py"
        if as_dir_init in self.file_set:
            return as_dir_init

        # Check prefixes if submodule
        parts = mod_name.split(".")
        for i in range(len(parts) - 1, 0, -1):
            parent = ".".join(parts[:i])
            if parent in self._module_to_file:
                return self._module_to_file[parent]

        return None

    def _resolve_relative_import(
        self,
        current_file: str,
        module: Optional[str],
        level: int,
        names: List[str],
    ) -> Optional[str]:
        curr_path = Path(current_file).parent
        # Ascend levels
        for _ in range(level - 1):
            curr_path = curr_path.parent

        if module:
            target_candidate = (curr_path / module.replace(".", "/")).as_posix()
        else:
            target_candidate = curr_path.as_posix()

        # Check .py
        py_cand = f"{target_candidate}.py"
        if py_cand in self.file_set:
            return py_cand

        # Check __init__.py
        init_cand = f"{target_candidate}/__init__.py"
        if init_cand in self.file_set:
            return init_cand

        # Check if first name in names is a submodule
        if names:
            name_cand = f"{target_candidate}/{names[0]}.py"
            if name_cand in self.file_set:
                return name_cand

        return None
