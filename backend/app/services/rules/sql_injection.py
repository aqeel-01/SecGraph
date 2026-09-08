"""Deterministic heuristics for possible SQL injection patterns."""

import re

from app.services.rules.base import Finding, RuleContext

SQL_PATTERN = re.compile(
    r"\b(?:select|insert|update|delete|from|where)\b",
    re.IGNORECASE,
)
UNSAFE_SQL_PATTERN = re.compile(
    r"(?:execute|executemany|text)\s*\([^)]*(?:f['\"]|['\"][^'\"]*['\"]\s*\+|\.format\s*\()",
    re.IGNORECASE,
)
UNSAFE_SQL_CONSTRUCTION = re.compile(
    r"(?:f['\"]|['\"][^'\"]*(?:select|insert|update|delete|where)"
    r"[^'\"]*['\"]\s*\+|\.format\s*\()",
    re.IGNORECASE,
)


class SQLInjectionRule:
    """Flag SQL execution using interpolation or string concatenation."""

    rule_id = "sql-injection-pattern"

    def evaluate(self, context: RuleContext) -> list[Finding]:
        findings: list[Finding] = []
        for project_file in context.project.files:
            source = context.source_for(project_file.id)
            for line_number, line in enumerate(source.splitlines(), start=1):
                if not SQL_PATTERN.search(line):
                    continue
                if not (
                    UNSAFE_SQL_PATTERN.search(line)
                    or UNSAFE_SQL_CONSTRUCTION.search(line)
                ):
                    continue
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        title="Possible SQL injection pattern",
                        severity="high",
                        confidence=0.85,
                        file=project_file.relative_path,
                        line=line_number,
                        endpoint=None,
                        description=(
                            "SQL-like text appears to reach an execution "
                            "function through interpolation or concatenation."
                        ),
                        evidence=line.strip()[:500],
                        remediation=(
                            "Use bound parameters or the ORM query builder "
                            "instead of constructing SQL with user-controlled "
                            "values."
                        ),
                        project_file_id=project_file.id,
                    )
                )
        return findings
