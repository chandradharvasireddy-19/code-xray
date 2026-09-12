import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class DocumentedRule:
    def __init__(self, rule_text: str, source_doc: str, allowed_flow: Optional[List[str]] = None):
        self.rule_text = rule_text
        self.source_doc = source_doc
        self.allowed_flow = allowed_flow or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_text": self.rule_text,
            "source_doc": self.source_doc,
            "allowed_flow": self.allowed_flow,
        }


class DocsAnalyzer:
    """
    Analyzes markdown and text documentation in the repository to extract
    architectural rules, contracts, and layer conventions.
    """

    def __init__(self, repo_path: str, doc_files: List[str]):
        self.repo_path = Path(repo_path).resolve()
        self.doc_files = doc_files

    def extract_rules(self) -> List[DocumentedRule]:
        rules: List[DocumentedRule] = []

        # Standard default layered rule if no docs found
        default_rule = DocumentedRule(
            rule_text="Controllers must delegate to Services; Controllers must NOT directly access Repositories/Database.",
            source_doc="default_architecture_policy",
            allowed_flow=["controller", "service", "repository"],
        )
        rules.append(default_rule)

        for rel_doc in self.doc_files:
            full_doc_path = self.repo_path / rel_doc
            if not full_doc_path.exists():
                continue

            try:
                with open(full_doc_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()

                # Look for layer arrows: e.g. Controller -> Service -> Repository
                matches = re.findall(
                    r"([A-Za-z0-9_]+)\s*(?:->|-->|→)\s*([A-Za-z0-9_]+)(?:\s*(?:->|-->|→)\s*([A-Za-z0-9_]+))?",
                    content,
                    re.IGNORECASE,
                )
                for m in matches:
                    flow = [part.strip().lower() for part in m if part.strip()]
                    if len(flow) >= 2:
                        flow_str = " -> ".join([p.capitalize() for p in flow])
                        rules.append(DocumentedRule(
                            rule_text=f"Layered flow contract: {flow_str}",
                            source_doc=rel_doc,
                            allowed_flow=flow,
                        ))

                # Look for forbidden patterns: e.g. "must not import repository", "no direct database"
                prohibitions = re.findall(
                    r"(?:must not|should not|cannot|do not)\s+([^\n\.\;]+)",
                    content,
                    re.IGNORECASE,
                )
                for p in prohibitions:
                    rules.append(DocumentedRule(
                        rule_text=f"Prohibition rule: Must not {p.strip()}",
                        source_doc=rel_doc,
                    ))

            except Exception:
                pass

        return rules
