"""Execution and persistence of deterministic security rules."""

from collections.abc import Iterable

from sqlalchemy.orm import Session

from app.models import SecurityFinding
from app.services.rules.base import Finding, RuleContext, SecurityRule
from app.services.rules.common import build_rule_context, endpoint_for
from app.services.rules.hardcoded_secrets import HardcodedSecretsRule
from app.services.rules.idor import PossibleIDORRule
from app.services.rules.missing_authentication import MissingAuthenticationRule
from app.services.rules.rate_limiting import MissingRateLimitingRule
from app.services.rules.sensitive_data import SensitiveDataExposureRule
from app.services.rules.sql_injection import SQLInjectionRule
from app.services.context_builder import SecurityContextBuilder

DEFAULT_RULES: tuple[SecurityRule, ...] = (
    MissingAuthenticationRule(),
    PossibleIDORRule(),
    SQLInjectionRule(),
    HardcodedSecretsRule(),
    SensitiveDataExposureRule(),
    MissingRateLimitingRule(),
)


def evaluate_rules(
    context: RuleContext,
    rules: Iterable[SecurityRule] = DEFAULT_RULES,
) -> list[Finding]:
    """Run each rule and return normalized findings."""

    findings: list[Finding] = []
    for rule in rules:
        findings.extend(rule.evaluate(context))
    return findings


def run_static_analysis(
    project,
    db: Session,
    rules: Iterable[SecurityRule] = DEFAULT_RULES,
) -> list[Finding]:
    """Evaluate and persist the current project's static findings."""

    context = build_rule_context(project)
    findings = evaluate_rules(context, rules)
    context_builder = SecurityContextBuilder(db)

    db.query(SecurityFinding).filter(
        SecurityFinding.project_id == project.id
    ).delete(synchronize_session=False)

    files_by_path = {
        project_file.relative_path: project_file
        for project_file in project.files
    }
    routes_by_key = {
        (project_file.relative_path, endpoint_for(route)): route
        for project_file in project.files
        for route in project_file.routes
    }
    for finding in findings:
        project_file = files_by_path.get(finding.file)
        route = routes_by_key.get((finding.file, finding.endpoint))
        db.add(
            SecurityFinding(
                project_id=project.id,
                project_file_id=(
                    finding.project_file_id
                    or (project_file.id if project_file is not None else None)
                ),
                route_id=finding.route_id or (route.id if route is not None else None),
                rule_id=finding.rule_id,
                title=finding.title,
                severity=finding.severity,
                confidence=max(0.0, min(1.0, finding.confidence)),
                file=finding.file,
                line=finding.line,
                endpoint=finding.endpoint,
                description=finding.description,
                evidence=finding.evidence,
                remediation=finding.remediation,
                context_package=context_builder.build(project, finding),
            )
        )
    return findings
