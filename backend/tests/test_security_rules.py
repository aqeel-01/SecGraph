from app.models import APIRoute, CodeFunction, Project, ProjectFile
from app.services.rules.base import RuleContext
from app.services.rules.hardcoded_secrets import HardcodedSecretsRule
from app.services.rules.idor import PossibleIDORRule
from app.services.rules.missing_authentication import MissingAuthenticationRule
from app.services.rules.rate_limiting import MissingRateLimitingRule
from app.services.rules.sensitive_data import SensitiveDataExposureRule
from app.services.rules.sql_injection import SQLInjectionRule


def make_context(
    source: str,
    *,
    method: str = "GET",
    path: str = "/items",
    dependencies: list[str] | None = None,
) -> RuleContext:
    project = Project(
        name="Rules test",
        source_type="upload",
        storage_path="/tmp/rules-test",
    )
    project_file = ProjectFile(
        relative_path="app/main.py",
        size_bytes=len(source),
        sha256="a" * 64,
        language="python",
    )
    function = CodeFunction(
        name="handler",
        qualname="handler",
        line_number=1,
        end_line=len(source.splitlines()),
        is_async=False,
    )
    route = APIRoute(
        http_method=method,
        path=path,
        function_name="handler",
        router_name="app",
        decorator_expression=f"@app.{method.lower()}('{path}')",
        dependencies=dependencies or [],
        line_number=1,
        function=function,
    )
    project_file.functions.append(function)
    project_file.routes.append(route)
    project.files.append(project_file)
    return RuleContext(project=project, sources={None: source})


def test_missing_authentication_rule() -> None:
    finding = MissingAuthenticationRule().evaluate(
        make_context("def handler():\n    return {'ok': True}\n")
    )[0]

    assert finding.rule_id == "missing-authentication"
    assert finding.endpoint == "GET /items"
    assert finding.confidence < 1


def test_possible_idor_rule() -> None:
    findings = PossibleIDORRule().evaluate(
        make_context(
            "def handler(user_id):\n    return load_user(user_id)\n",
            path="/users/{user_id}",
        )
    )

    assert len(findings) == 1
    assert findings[0].rule_id == "possible-idor"


def test_sql_injection_rule() -> None:
    findings = SQLInjectionRule().evaluate(
        make_context(
            'def handler(user_id):\n'
            '    db.execute(f"SELECT * FROM users WHERE id = {user_id}")\n'
        )
    )

    assert len(findings) == 1
    assert findings[0].rule_id == "sql-injection-pattern"


def test_hardcoded_secret_rule() -> None:
    findings = HardcodedSecretsRule().evaluate(
        make_context('api_key = "live-api-key-value"\n')
    )

    assert len(findings) == 1
    assert "<redacted>" in findings[0].evidence
    assert "live-api-key-value" not in findings[0].evidence


def test_sensitive_data_exposure_rule() -> None:
    findings = SensitiveDataExposureRule().evaluate(
        make_context(
            "def handler():\n"
            "    return {'password': user.password}\n"
        )
    )

    assert len(findings) == 1
    assert findings[0].rule_id == "sensitive-data-exposure"


def test_missing_rate_limiting_rule() -> None:
    findings = MissingRateLimitingRule().evaluate(
        make_context(
            "def handler():\n    return {'created': True}\n",
            method="POST",
            path="/items",
        )
    )

    assert len(findings) == 1
    assert findings[0].rule_id == "missing-rate-limiting"
