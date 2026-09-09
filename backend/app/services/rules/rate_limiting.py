"""Basic missing rate-limiting heuristics."""

import re

from app.services.rules.base import Finding, RuleContext
from app.services.rules.common import endpoint_for, function_source

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
RATE_LIMIT_MARKER = re.compile(
    r"(?:rate[_-]?limit|ratelimit|throttle|limiter)",
    re.IGNORECASE,
)


class MissingRateLimitingRule:
    """Flag mutating routes with no visible rate-limit marker."""

    rule_id = "missing-rate-limiting"

    def evaluate(self, context: RuleContext) -> list[Finding]:
        findings: list[Finding] = []
        for project_file in context.files:
            for route in project_file.routes:
                if route.http_method not in MUTATING_METHODS:
                    continue
                function_text = (
                    function_source(context, route.function)
                    if route.function is not None
                    else ""
                )
                inspected = f"{route.decorator_expression}\n{function_text}"
                if RATE_LIMIT_MARKER.search(inspected):
                    continue
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        title="Possible missing rate limiting",
                        severity="low",
                        confidence=0.60,
                        file=project_file.relative_path,
                        line=route.line_number,
                        endpoint=endpoint_for(route),
                        description=(
                            "This mutating API route has no visible rate-limiting "
                            "or throttling marker."
                        ),
                        evidence=route.decorator_expression,
                        remediation=(
                            "Review abuse expectations and apply a suitable "
                            "rate-limiting policy at the route or gateway."
                        ),
                        project_file_id=project_file.id,
                        route_id=route.id,
                    )
                )
        return findings
