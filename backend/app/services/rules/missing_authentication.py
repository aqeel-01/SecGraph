"""Missing authentication checks for detected API routes."""

import re

from app.services.rules.base import Finding, RuleContext
from app.services.rules.common import endpoint_for

AUTH_DECORATOR = re.compile(
    r"(?:auth|required|authenticated|login|permission)",
    re.IGNORECASE,
)


class MissingAuthenticationRule:
    """Flag routes without an obvious authentication dependency."""

    rule_id = "missing-authentication"

    def evaluate(self, context: RuleContext) -> list[Finding]:
        findings: list[Finding] = []
        for project_file in context.project.files:
            for route in project_file.routes:
                function = route.function
                decorators = (
                    function.project_file.decorators
                    if function is not None
                    else []
                )
                has_auth_decorator = any(
                    decorator.target_name == route.function_name
                    and AUTH_DECORATOR.search(decorator.expression)
                    for decorator in decorators
                )
                if route.dependencies or has_auth_decorator:
                    continue
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        title="Possible missing authentication",
                        severity="medium",
                        confidence=0.80,
                        file=project_file.relative_path,
                        line=route.line_number,
                        endpoint=endpoint_for(route),
                        description=(
                            "This API route has no detected authentication "
                            "dependency or authentication decorator."
                        ),
                        evidence=route.decorator_expression,
                        remediation=(
                            "Review the route's access requirements and add "
                            "an explicit authentication dependency if needed."
                        ),
                        project_file_id=project_file.id,
                        route_id=route.id,
                    )
                )
        return findings
