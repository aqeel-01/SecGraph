from app.services.ast_parser import parse_python_source


ROUTE_SOURCE = """
from fastapi import APIRouter, Depends, FastAPI

app = FastAPI()
router = APIRouter(prefix="/v1")

def authenticate():
    pass

@app.post("/users")
def create_user():
    pass

@router.get("/users/{user_id}", dependencies=[Depends(authenticate)])
async def get_user(user_id: str):
    pass

@router.api_route(
    "/users/{user_id}/settings",
    methods=["GET", "PATCH"],
    dependencies=[Depends(authenticate)],
)
def user_settings(user_id: str):
    pass
"""


def test_fastapi_app_and_router_routes_are_structured() -> None:
    result = parse_python_source(ROUTE_SOURCE, "routes.py")

    routes = result.routes
    assert len(routes) == 4
    assert {(route.http_method, route.path) for route in routes} == {
        ("POST", "/users"),
        ("GET", "/users/{user_id}"),
        ("GET", "/users/{user_id}/settings"),
        ("PATCH", "/users/{user_id}/settings"),
    }

    user_route = next(route for route in routes if route.path == "/users/{user_id}")
    assert user_route.router_name == "router"
    assert user_route.function_name == "get_user"
    assert user_route.line_number > 0
    assert user_route.dependencies == ["Depends(authenticate)"]

    app_route = next(route for route in routes if route.path == "/users")
    assert app_route.router_name == "app"
    assert app_route.function_name == "create_user"
    assert app_route.dependencies == []
