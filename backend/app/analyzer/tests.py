from pathlib import Path
from typing import Dict, List, Set, Tuple
from app.models.repository import CodeEntity, Relationship


class TestAnalyzer:
    """
    Identifies test suites, test cases, and maps them to the application components
    they exercise via imports, call references, and naming conventions.
    """
    __test__ = False

    def __init__(
        self,
        test_files: List[str],
        source_files: List[str],
        entities: Dict[str, CodeEntity],
        file_dependencies: List[Relationship],
        call_relationships: List[Relationship],
    ):
        self.test_files = set(test_files)
        self.source_files = set(source_files)
        self.entities = entities
        self.file_deps = file_dependencies
        self.call_relationships = call_relationships

    def analyze(self) -> Tuple[List[Relationship], Dict[str, List[str]], List[str]]:
        """
        Returns:
            - List of Relationship objects (type='tests')
            - Map of source_file -> list of associated test_files
            - List of untested source files
        """
        test_relationships: List[Relationship] = []
        tested_by_map: Dict[str, Set[str]] = {src: set() for src in self.source_files}
        seen_test_pairs: Set[Tuple[str, str]] = set()

        # 1. Map via direct test imports
        for dep in self.file_deps:
            if dep.source in self.test_files and dep.target in self.source_files:
                pair = (dep.source, dep.target)
                if pair not in seen_test_pairs:
                    seen_test_pairs.add(pair)
                    test_relationships.append(Relationship(
                        source=dep.source,
                        target=dep.target,
                        type="tests",
                        confidence=0.90,
                        line=dep.line,
                        detail=f"Test file '{dep.source}' imports '{dep.target}'",
                    ))
                    tested_by_map[dep.target].add(dep.source)

        # 2. Map via call relationships (test entity calling source entity)
        for call_rel in self.call_relationships:
            caller = self.entities.get(call_rel.source)
            callee = self.entities.get(call_rel.target)
            if caller and callee and caller.file in self.test_files and callee.file in self.source_files:
                pair = (caller.file, callee.file)
                if pair not in seen_test_pairs:
                    seen_test_pairs.add(pair)
                    test_relationships.append(Relationship(
                        source=caller.file,
                        target=callee.file,
                        type="tests",
                        confidence=0.95,
                        line=call_rel.line,
                        detail=f"Test '{caller.name}' invokes '{callee.name}' in '{callee.file}'",
                    ))
                tested_by_map[callee.file].add(caller.file)

        # 3. Map via file naming heuristics (e.g. test_payment.py -> payment_service.py)
        for t_file in self.test_files:
            t_base = Path(t_file).stem.lower().replace("test_", "").replace("_test", "")
            if not t_base:
                continue
            for s_file in self.source_files:
                s_base = Path(s_file).stem.lower()
                if t_base == s_base or t_base in s_base:
                    pair = (t_file, s_file)
                    if pair not in seen_test_pairs:
                        seen_test_pairs.add(pair)
                        test_relationships.append(Relationship(
                            source=t_file,
                            target=s_file,
                            type="tests",
                            confidence=0.75,
                            detail=f"Test name '{Path(t_file).name}' matches source '{Path(s_file).name}'",
                        ))
                        tested_by_map[s_file].add(t_file)

        tested_map_serializable: Dict[str, List[str]] = {
            src: sorted(list(tests)) for src, tests in tested_by_map.items() if tests
        }
        untested_files = [src for src, tests in tested_by_map.items() if not tests]

        return test_relationships, tested_map_serializable, untested_files
