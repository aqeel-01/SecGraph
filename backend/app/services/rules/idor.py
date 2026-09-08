"""Heuristics for possible IDOR and missing ownership validation."""

import re

from app.services.rules.base import Finding, RuleContext
from app.services.rules.common import endpoint_for, function_source

RESOURCE_PARAMETER = re.compile(
    r"\{(?:id|.*_id|user|account|owner|resource)\}",
    re.IGNORECASE,
)
OWNERSHIP_CHECK = re.compile(
    r"(?:owner|ownership|current_user|authorize|permission|belongs_to)",
    re.IGNORECASE,
)


class PossibleIDORRule:
    """Flag resource routes lacking visible ownership checks."""

    rule_id = "possible-idor"

    def evaluate(self, context: RuleContext) -> list[Finding]:
        findings: list[Finding] = []
        for project_file in context.project.files:
            for route in project_file.routes:
                if not RESOURCE_PARAMETER.search(route.path):
                    continue
                if route.function is None:
                    continue
                source = function_source(context, route.function)
                if OWNERSHIP_CHECK.search(source):
                    continue
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        title="Possible IDOR or missing ownership validation",
                        severity="high",
                        confidence=0.65,
                        file=project_file.relative_path,
                        line=route.line_number,
                        endpoint=endpoint_for(route),
                        description=(
                            "The route accepts a resource identifier but no "
                            "obvious ownership or authorization check was found "
                            "in the indexed function body."
                        ),
                        evidence=source[:500] or route.decorator_expression,
                        remediation=(
                            "Verify that the authenticated principal is allowed "
                            "to access the requested resource before returning "
                            "or modifying it."
                        ),
                        project_file_id=project_file.id,
                        route_id=route.id,
                    )
                )
        return findings
