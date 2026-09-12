"""Parse developer tasks into searchable concepts and match against code entities."""
import re
from typing import Any, Dict, List, Optional, Set
from app.models.repository import CodeEntity, RepositoryModel


class TaskParser:
    """
    Deterministic task parser that extracts concepts from a natural-language task
    description and matches them against known code entities in the repository.
    Works entirely without an LLM.
    """

    # Common stop words to filter out
    STOP_WORDS = {
        "i", "me", "my", "we", "our", "you", "your", "the", "a", "an", "is", "are",
        "was", "were", "be", "been", "being", "have", "has", "had", "do", "does",
        "did", "will", "would", "could", "should", "may", "might", "shall", "can",
        "need", "want", "to", "of", "in", "for", "on", "with", "at", "by", "from",
        "as", "into", "through", "during", "before", "after", "above", "below",
        "between", "out", "off", "over", "under", "again", "further", "then",
        "once", "here", "there", "when", "where", "why", "how", "all", "both",
        "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not",
        "only", "same", "so", "than", "too", "very", "just", "but", "and", "or",
        "if", "it", "its", "this", "that", "these", "those", "what", "which",
    }

    # Task action verbs that indicate intent
    ACTION_VERBS = {
        "modify", "change", "update", "fix", "refactor", "add", "remove", "delete",
        "implement", "create", "build", "replace", "migrate", "upgrade", "debug",
        "test", "optimize", "improve", "rewrite", "extend", "integrate",
    }

    def __init__(self, repo: RepositoryModel):
        self.repo = repo
        self.entities = repo.entities

        # Build lookup indexes
        self._name_index: Dict[str, List[CodeEntity]] = {}
        self._file_basenames: Dict[str, str] = {}
        self._all_names: Set[str] = set()

        self._build_indexes()

    def _build_indexes(self) -> None:
        for entity in self.entities.values():
            name_lower = entity.name.lower()
            if name_lower not in self._name_index:
                self._name_index[name_lower] = []
            self._name_index[name_lower].append(entity)
            self._all_names.add(name_lower)

        for f in self.repo.files:
            basename = f.rsplit("/", 1)[-1].rsplit(".", 1)[0].lower()
            self._file_basenames[basename] = f

    def parse(self, task: str) -> Dict[str, Any]:
        """
        Parse a task description and return matched concepts and entities.

        Returns:
            {
                "task": original task string,
                "concepts": list of extracted concept keywords,
                "actions": list of detected action verbs,
                "matched_entities": list of matched entity IDs,
                "matched_files": list of matched file paths,
            }
        """
        # Tokenize and normalize
        tokens = self._tokenize(task)
        concepts = self._extract_concepts(tokens)
        actions = self._extract_actions(tokens)

        # Match against code entities
        matched_entities: List[str] = []
        matched_files: Set[str] = set()

        for concept in concepts:
            # Direct entity name match
            if concept in self._name_index:
                for entity in self._name_index[concept]:
                    if entity.id not in matched_entities:
                        matched_entities.append(entity.id)
                        matched_files.add(entity.file)

            # File basename match
            if concept in self._file_basenames:
                file_path = self._file_basenames[concept]
                matched_files.add(file_path)
                # Add file-level entity
                if file_path in self.entities:
                    if file_path not in matched_entities:
                        matched_entities.append(file_path)

            # Partial match: concept appears in entity name
            for name, entities in self._name_index.items():
                if concept in name or name in concept:
                    for entity in entities:
                        if entity.id not in matched_entities:
                            matched_entities.append(entity.id)
                            matched_files.add(entity.file)

            # Compound concept match (e.g., "payment_service" split into "payment" + "service")
            for name in self._all_names:
                name_parts = set(re.split(r'[_\-]', name))
                if concept in name_parts:
                    for entity in self._name_index.get(name, []):
                        if entity.id not in matched_entities:
                            matched_entities.append(entity.id)
                            matched_files.add(entity.file)

        return {
            "task": task,
            "concepts": concepts,
            "actions": actions,
            "matched_entities": matched_entities,
            "matched_files": sorted(matched_files),
        }

    def _tokenize(self, text: str) -> List[str]:
        # Remove punctuation except underscores
        cleaned = re.sub(r'[^\w\s]', ' ', text.lower())
        tokens = cleaned.split()
        return tokens

    def _extract_concepts(self, tokens: List[str]) -> List[str]:
        concepts = []
        for token in tokens:
            if token in self.STOP_WORDS:
                continue
            if token in self.ACTION_VERBS:
                continue
            if len(token) <= 1:
                continue
            # Split camelCase
            parts = re.sub(r'([a-z])([A-Z])', r'\1_\2', token).lower().split('_')
            for part in parts:
                if part and part not in self.STOP_WORDS and len(part) > 1:
                    if part not in concepts:
                        concepts.append(part)
        return concepts

    def _extract_actions(self, tokens: List[str]) -> List[str]:
        return [t for t in tokens if t in self.ACTION_VERBS]
