from typing import Dict, List, Optional, Set, Tuple
from app.models.repository import CodeEntity, Relationship


class CallGraphBuilder:
    """
    Builds a practical static Python call graph by resolving caller entities
    to callee entities using AST call expressions and import scopes.
    """

    def __init__(
        self,
        entities: Dict[str, CodeEntity],
        file_dependencies: List[Relationship],
    ):
        self.entities = entities
        self.file_deps = file_dependencies

        # Lookup maps
        # 1. file -> list of entities in that file
        self._file_entities: Dict[str, List[CodeEntity]] = {}
        # 2. (file, entity_name) -> entity
        self._name_in_file: Dict[Tuple[str, str], CodeEntity] = {}
        # 3. entity_name -> list of entities with this name across codebase
        self._name_global: Dict[str, List[CodeEntity]] = {}
        # 4. file -> set of directly imported internal files
        self._file_imports: Dict[str, Set[str]] = {}

        self._build_indexes()

    def _build_indexes(self) -> None:
        for entity in self.entities.values():
            f = entity.file
            if f not in self._file_entities:
                self._file_entities[f] = []
            self._file_entities[f].append(entity)

            self._name_in_file[(f, entity.name)] = entity

            if entity.name not in self._name_global:
                self._name_global[entity.name] = []
            self._name_global[entity.name].append(entity)

        for dep in self.file_deps:
            if dep.type == "imports":
                if dep.source not in self._file_imports:
                    self._file_imports[dep.source] = set()
                self._file_imports[dep.source].add(dep.target)

    def build(self) -> List[Relationship]:
        """
        Resolve all function calls into caller -> callee relationships.
        """
        call_relationships: List[Relationship] = []
        seen_edges: Set[Tuple[str, str]] = set()

        for caller in self.entities.values():
            if caller.type not in ["function", "method"]:
                continue

            for call_name in caller.calls:
                target_entity, confidence = self._resolve_call(caller, call_name)
                if target_entity and target_entity.id != caller.id:
                    edge_key = (caller.id, target_entity.id)
                    if edge_key not in seen_edges:
                        seen_edges.add(edge_key)
                        call_relationships.append(Relationship(
                            source=caller.id,
                            target=target_entity.id,
                            type="calls",
                            confidence=confidence,
                            line=caller.line_start,
                            detail=f"{caller.name}() invokes {call_name}",
                        ))

        return call_relationships

    def _resolve_call(self, caller: CodeEntity, call_expr: str) -> Tuple[Optional[CodeEntity], float]:
        """
        Resolves a call expression into a target CodeEntity and confidence score.
        """
        clean_name = call_expr.strip()
        parts = clean_name.split(".")
        last_name = parts[-1]

        # Case 1: self.method_name() inside a method
        if parts[0] == "self" and caller.type == "method":
            parent_class = caller.id.split(":")[-1].split(".")[0]
            target_id = f"{caller.file}:{parent_class}.{last_name}"
            if target_id in self.entities:
                return self.entities[target_id], 0.95

        # Case 2: Direct call to function/class in the same file
        if len(parts) == 1:
            local_target = self._name_in_file.get((caller.file, clean_name))
            if local_target and local_target.id != caller.id:
                return local_target, 0.90

        # Case 3: Target in an explicitly imported file
        imported_files = self._file_imports.get(caller.file, set())
        for imp_file in imported_files:
            # Check for Class.method
            if len(parts) >= 2:
                cls_name = parts[-2]
                target_id = f"{imp_file}:{cls_name}.{last_name}"
                if target_id in self.entities:
                    return self.entities[target_id], 0.85

            # Check direct name in imported file
            target = self._name_in_file.get((imp_file, last_name))
            if target:
                return target, 0.80

        # Case 4: Unique symbol name globally across the codebase
        matches = self._name_global.get(last_name, [])
        # Filter out self
        matches = [m for m in matches if m.id != caller.id]
        if len(matches) == 1:
            return matches[0], 0.65

        # Case 5: Class name match (e.g. AuthService())
        if len(parts) == 1:
            cls_matches = [m for m in matches if m.type == "class"]
            if len(cls_matches) == 1:
                return cls_matches[0], 0.70

        return None, 0.0
