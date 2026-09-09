"""Hardcoded secret heuristics."""

import re

from app.services.rules.base import Finding, RuleContext

SECRET_ASSIGNMENT = re.compile(
    r"\b(password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token)"
    r"\b\s*[:=]\s*([\"'])([^\"']+)\2",
    re.IGNORECASE,
)
PLACEHOLDER = re.compile(
    r"(?:change[_-]?me|example|placeholder|your[_-]?|<[^>]+>)",
    re.IGNORECASE,
)


class HardcodedSecretsRule:
    """Flag non-placeholder credentials assigned to string literals."""

    rule_id = "hardcoded-secret"

    def evaluate(self, context: RuleContext) -> list[Finding]:
        findings: list[Finding] = []
        for project_file in context.files:
            source = context.source_for(project_file.id)
            for line_number, line in enumerate(source.splitlines(), start=1):
                match = SECRET_ASSIGNMENT.search(line)
                if match is None or PLACEHOLDER.search(match.group(3)):
                    continue
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        title="Possible hardcoded secret",
                        severity="high",
                        confidence=0.90,
                        file=project_file.relative_path,
                        line=line_number,
                        endpoint=None,
                        description=(
                            "A credential-like value appears to be assigned "
                            "directly from a source-code string literal."
                        ),
                        evidence=f"{match.group(1)} = '<redacted>'",
                        remediation=(
                            "Move the secret to a managed environment or secret "
                            "store and rotate any exposed credential."
                        ),
                        project_file_id=project_file.id,
                    )
                )
        return findings
