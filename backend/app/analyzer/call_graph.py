from __future__ import annotations

from typing import Any, Sequence
import networkx as nx

from .models import CallInfo, CallRelationship, ParsedFile


class CallGraph:
    """Directed graph representing caller-callee relationships constructed from AST facts."""

    def __init__(self) -> None:
        self.graph: nx.DiGraph = nx.DiGraph()
        self._defined_symbols: dict[str, str] = {}  # symbol_name -> file_path
        self._relationships: list[CallRelationship] = []

    def add_defined_function(
        self,
        name: str,
        file_path: str,
        line_number: int,
        is_method: bool = False,
        class_name: str | None = None,
    ) -> None:
        """Register a defined function or method as a node in the graph."""
        node_id = f"{class_name}.{name}" if class_name else name
        self._defined_symbols[node_id] = file_path
        self._defined_symbols[name] = file_path

        self.graph.add_node(
            node_id,
            file_path=file_path,
            line_number=line_number,
            is_method=is_method,
            class_name=class_name,
            is_defined=True,
        )

    def add_call(self, call: CallInfo) -> None:
        """Add a directed edge from caller to callee preserving call site metadata."""
        caller = call.caller
        callee = call.callee

        # Ensure caller node exists
        if not self.graph.has_node(caller):
            self.graph.add_node(
                caller,
                file_path=call.file_path,
                line_number=call.line_number,
                is_defined=False,
            )

        # Ensure callee node exists
        if not self.graph.has_node(callee):
            callee_file = self._defined_symbols.get(callee)
            self.graph.add_node(
                callee,
                file_path=callee_file,
                line_number=None,
                is_defined=callee in self._defined_symbols,
            )

        # Add or update edge
        if self.graph.has_edge(caller, callee):
            call_sites = self.graph[caller][callee].get("call_sites", [])
            call_sites.append({"file_path": call.file_path, "line_number": call.line_number})
        else:
            self.graph.add_edge(
                caller,
                callee,
                file_path=call.file_path,
                line_number=call.line_number,
                call_sites=[{"file_path": call.file_path, "line_number": call.line_number}],
            )

        self._relationships.append(
            CallRelationship(
                caller=caller,
                callee=callee,
                file_path=call.file_path,
                line_number=call.line_number,
            )
        )

    def get_callers(self, function_name: str) -> list[str]:
        """Return all functions/callers that call the specified function.

        Args:
            function_name: Identifier of the target function/method.

        Returns:
            Sorted list of caller names.
        """
        if not self.graph.has_node(function_name):
            # Check if matched by suffix (e.g. searching 'save' finds callers of 'Database.save')
            matching = [n for n in self.graph.nodes if n.endswith(f".{function_name}")]
            callers: set[str] = set()
            for m in matching:
                callers.update(self.graph.predecessors(m))
            return sorted(callers)

        return sorted(self.graph.predecessors(function_name))

    def get_callees(self, function_name: str) -> list[str]:
        """Return all functions/methods called by the specified function.

        Args:
            function_name: Identifier of the caller function/method.

        Returns:
            Sorted list of callee names.
        """
        if not self.graph.has_node(function_name):
            # Check if matched by suffix
            matching = [n for n in self.graph.nodes if n.endswith(f".{function_name}")]
            callees: set[str] = set()
            for m in matching:
                callees.update(self.graph.successors(m))
            return sorted(callees)

        return sorted(self.graph.successors(function_name))

    def get_connected_files(self) -> list[tuple[str, str]]:
        """Return distinct pairs of source files connected by function calls.

        Returns:
            Sorted list of (source_file, target_file) tuples.
        """
        connected: set[tuple[str, str]] = set()

        for u, v, data in self.graph.edges(data=True):
            source_file = data.get("file_path") or self.graph.nodes[u].get("file_path")
            target_file = self.graph.nodes[v].get("file_path") or self._defined_symbols.get(v)

            if source_file and target_file and source_file != target_file:
                connected.add((source_file, target_file))

        return sorted(connected)

    def get_relationships(self) -> list[CallRelationship]:
        """Return all recorded call relationships with file and line metadata."""
        return list(self._relationships)

    @property
    def node_count(self) -> int:
        return self.graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self.graph.number_of_edges()


class CallGraphBuilder:
    """Builds a CallGraph from structured ParsedFile instances."""

    def build(self, parsed_files: Sequence[ParsedFile]) -> CallGraph:
        """Construct a CallGraph from a sequence of parsed Python files."""
        graph = CallGraph()

        # 1. Register all defined functions and methods first
        for pf in parsed_files:
            for func in pf.functions:
                graph.add_defined_function(
                    name=func.name,
                    file_path=pf.file_path,
                    line_number=func.line_number,
                    is_method=func.is_method,
                    class_name=func.class_name,
                )

        # 2. Register all function calls
        for pf in parsed_files:
            for call in pf.calls:
                graph.add_call(call)

        return graph
