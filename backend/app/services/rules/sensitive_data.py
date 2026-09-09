"""Sensitive data exposure heuristics."""

import re

from app.services.rules.base import Finding, RuleContext
from app.services.rules.common import endpoint_for, function_source

SENSITIVE_VALUE = re.compile(
    r"\b(password|passwd|secret|api[_-]?key|access[_-]?token|ssn|"
    r"social_security|credit_card)\b",
    re.IGNORECASE,
)


class SensitiveDataExposureRule:
    """Flag routes that visibly return sensitive fields."""

    rule_id = "sensitive-data-exposure"

    def evaluate(self, context: RuleContext) -> list[Finding]:
        findings: list[Finding] = []
        for project_file in context.files:
            for route in project_file.routes:
                if route.function is None:
                    continue
                source = function_source(context, route.function)
                return_lines = [
                    (number, line.strip())
                    for number, line in enumerate(
                        source.splitlines(),
                        start=route.function.line_number,
                    )
                    if "return" in line and SENSITIVE_VALUE.search(line)
                ]
                if not return_lines:
                    continue
                line_number, evidence = return_lines[0]
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        title="Possible sensitive data exposure",
                        severity="medium",
                        confidence=0.75,
                        file=project_file.relative_path,
                        line=line_number,
                        endpoint=endpoint_for(route),
                        description=(
                            "The route appears to return a password, token, "
                            "secret, or other sensitive field."
                        ),
                        evidence=evidence[:500],
                        remediation=(
                            "Return a dedicated response schema that excludes "
                            "secrets and sensitive fields."
                        ),
                        project_file_id=project_file.id,
                        route_id=route.id,
                    )
                )
        return findings
