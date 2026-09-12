import os
from typing import Any, Dict, Optional
from app.privacy.context_filter import ContextFilter
from app.privacy.redactor import SecretRedactor
from app.ai.prompts import (
    SYSTEM_PROMPT_FINDING,
    SYSTEM_PROMPT_IMPACT,
    build_finding_user_prompt,
    build_impact_user_prompt,
)


class ForensicExplainer:
    """
    Produces evidence-backed natural language explanations for forensic findings
    and change impact reports.
    Uses OpenAI if OPENAI_API_KEY is configured; otherwise provides a reliable,
    structured deterministic fallback without failing or stalling.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.context_filter = ContextFilter(SecretRedactor())

    def explain_finding(self, finding_dict: Dict[str, Any]) -> str:
        """
        Explain a single ForensicFinding.
        """
        filtered_ctx = self.context_filter.filter_finding_context(finding_dict)

        if self.api_key:
            try:
                explanation = self._call_llm(
                    system_prompt=SYSTEM_PROMPT_FINDING,
                    user_prompt=build_finding_user_prompt(filtered_ctx),
                )
                if explanation:
                    return explanation
            except Exception:
                pass  # Fall through to deterministic fallback

        return self._generate_finding_fallback(filtered_ctx)

    def explain_impact(self, impact_dict: Dict[str, Any]) -> str:
        """
        Explain a Change Impact Analysis result.
        """
        filtered_ctx = self.context_filter.filter_impact_context(impact_dict)

        if self.api_key:
            try:
                explanation = self._call_llm(
                    system_prompt=SYSTEM_PROMPT_IMPACT,
                    user_prompt=build_impact_user_prompt(filtered_ctx),
                )
                if explanation:
                    return explanation
            except Exception:
                pass  # Fall through to deterministic fallback

        return self._generate_impact_fallback(filtered_ctx)

    def _call_llm(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        # Minimal HTTP call using httpx or urllib to avoid hard requirement on openai sdk
        import urllib.request
        import json

        url = "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 500,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()

    def _generate_finding_fallback(self, ctx: Dict[str, Any]) -> str:
        f_type = ctx.get("finding_type", "issue")
        title = ctx.get("title", "Forensic Finding")
        file_path = ctx.get("affected_file", "unknown")
        symbol = ctx.get("affected_symbol")
        evidence = ctx.get("evidence", "No evidence recorded")
        severity = ctx.get("severity", "medium").upper()
        confidence = ctx.get("confidence", 0.8)

        target = f"'{symbol}' in '{file_path}'" if symbol else f"file '{file_path}'"

        lines = [
            f"### Forensic Analysis: {title}",
            "",
            f"**[FACT] Status & Severity**: {severity} severity (Confidence: {int(confidence * 100)}%)",
            f"**[FACT] Target Location**: {target}",
            f"**[FACT] Direct Evidence**: {evidence}",
            "",
            "**[INFERENCE] Impact Assessment**:",
        ]

        if "architecture" in f_type.lower():
            lines.append(
                f"- This bypasses established architectural boundaries, creating direct coupling between layers."
            )
            lines.append("- Downstream refactoring or database migrations risk cascading breakages into controller layers.")
        elif "dead" in f_type.lower():
            lines.append(
                f"- No callers, imports, or test invocations were found pointing to {target}."
            )
            lines.append("- Retaining unused code increases cognitive load and maintenance drag without providing value.")
        elif "ghost" in f_type.lower():
            lines.append(
                f"- Dependency '{symbol}' is declared in project manifests but has no corresponding import references."
            )
            lines.append("- Unused dependencies bloat build artifacts, slow installation times, and expose unnecessary supply-chain attack surface.")
        elif "knowledge" in f_type.lower():
            lines.append(
                f"- Git history demonstrates strong author concentration on '{file_path}'."
            )
            lines.append("- High bus factor risk exists if team members unfamiliar with this module need to alter it.")
        else:
            lines.append(f"- Code inspection identified an irregularity in {target} warranting verification.")

        lines.extend([
            "",
            "**[RECOMMENDED ACTION] Next Steps**:",
            f"1. Inspect `{file_path}` around the referenced symbols.",
            "2. Run associated test suites to ensure behavior is covered before modifying.",
            "3. If this finding represents legacy drift, refactor to adhere to target architecture.",
        ])

        return "\n".join(lines)

    def _generate_impact_fallback(self, ctx: Dict[str, Any]) -> str:
        task = ctx.get("task", "Proposed change")
        risk_score = ctx.get("risk_score", 50)
        risk_level = ctx.get("risk_level", "MEDIUM")
        factors = ctx.get("risk_factors", [])
        entities = ctx.get("affected_entities", [])
        total_affected = ctx.get("total_affected_count", len(entities))
        tests = ctx.get("related_tests", [])
        total_tests = ctx.get("total_tests_count", len(tests))

        lines = [
            f"### Change Impact Assessment",
            f"**Task**: *\"{task}\"*",
            "",
            f"**[FACT] Overall Risk Level**: **{risk_level}** ({risk_score}/100)",
            f"**[FACT] Affected Components**: {total_affected} entities detected across the dependency chain.",
        ]

        if factors:
            lines.append(f"**[FACT] Primary Risk Factors**: {', '.join(factors)}")

        lines.extend([
            "",
            "**[INFERENCE] Architectural Blast Radius**:",
            f"- Modifying this flow directly touches primary business logic and cascades into dependent validation, service, and data access layers.",
        ])

        if total_tests > 0:
            test_suites_str = f" ({', '.join(tests[:3])})" if tests else ""
            lines.append(f"- **[FACT] Relevant Test Coverage**: {total_tests} test mapping(s) across {len(tests)} test suite(s){test_suites_str}.")
        else:
            lines.append("- **[INFERENCE] Test Gap Warning**: No direct unit tests were identified covering this flow.")

        lines.extend([
            "",
            "**[RECOMMENDED ACTION] Safe Execution Path**:",
            "1. Review entry point controller schemas and request validators.",
            "2. Update service layer business logic and coordinate with token validation logic.",
            "3. Run identified unit tests locally before and after applying code modifications.",
        ])

        return "\n".join(lines)
