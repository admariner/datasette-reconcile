import json

import httpx
import pytest
from datasette.app import Datasette

from tests.conftest import plugin_metadata


@pytest.mark.asyncio
async def test_plugin_is_installed():
    app = Datasette([], memory=True).app()
    async with httpx.AsyncClient(app=app) as client:
        response = await client.get("http://localhost/-/plugins.json")
        assert 200 == response.status_code
        installed_plugins = {p["name"] for p in response.json()}
        assert "datasette-reconcile" in installed_plugins


@pytest.mark.asyncio
async def test_response_not_configured(db_path):
    app = Datasette([db_path]).app()
    async with httpx.AsyncClient(app=app) as client:
        response = await client.get("http://localhost/test/dogs/-/reconcile")
        assert 404 == response.status_code


@pytest.mark.asyncio
async def test_response_without_query(db_path):
    app = Datasette([db_path], metadata=plugin_metadata({"name_field": "name"})).app()
    async with httpx.AsyncClient(app=app) as client:
        response = await client.get("http://localhost/test/dogs/-/reconcile")
        assert 200 == response.status_code
        data = response.json()
        assert "name" in data.keys()
        assert isinstance(data["defaultTypes"], list)
        assert len(data["defaultTypes"]) == 1
        assert data["defaultTypes"][0]["id"] == "object"
        assert data["defaultTypes"][0]["name"] == "Object"
        assert data["view"]["url"].startswith("http")
        assert response.headers["Access-Control-Allow-Origin"] == "*"


@pytest.mark.asyncio
async def test_servce_manifest_view_url_default(db_path):
    app = Datasette([db_path], metadata=plugin_metadata({"name_field": "name"})).app()
    async with httpx.AsyncClient(app=app) as client:
        response = await client.get("http://localhost/test/dogs/-/reconcile")
        assert 200 == response.status_code
        data = response.json()
        assert data["view"]["url"] == "http://localhost/test/dogs/{{id}}"


@pytest.mark.asyncio
async def test_servce_manifest_https(db_path):
    app = Datasette([db_path], metadata=plugin_metadata({"name_field": "name"})).app()
    async with httpx.AsyncClient(app=app) as client:
        response = await client.get("https://localhost/test/dogs/-/reconcile")
        assert 200 == response.status_code
        data = response.json()
        assert data["view"]["url"] == "https://localhost/test/dogs/{{id}}"


@pytest.mark.asyncio
async def test_servce_manifest_x_forwarded_proto_https(db_path):
    app = Datasette([db_path], metadata=plugin_metadata({"name_field": "name"})).app()
    async with httpx.AsyncClient(app=app) as client:
        response = await client.get("http://localhost/test/dogs/-/reconcile", headers={"x-forwarded-proto": "https"})
        assert 200 == response.status_code
        data = response.json()
        assert data["view"]["url"] == "https://localhost/test/dogs/{{id}}"


@pytest.mark.asyncio
async def test_servce_manifest_view_url_custom(db_path):
    custom_view_url = "https://example.com/{{id}}"
    app = Datasette(
        [db_path],
        metadata=plugin_metadata(
            {
                "name_field": "name",
                "view_url": custom_view_url,
            }
        ),
    ).app()
    async with httpx.AsyncClient(app=app) as client:
        response = await client.get("http://localhost/test/dogs/-/reconcile")
        assert 200 == response.status_code
        data = response.json()
        assert data["view"]["url"] == custom_view_url


@pytest.mark.asyncio
async def test_servce_manifest_view_extend(db_path):
    app = Datasette(
        [db_path],
        metadata=plugin_metadata({"name_field": "name"}),
    ).app()
    async with httpx.AsyncClient(app=app) as client:
        response = await client.get("http://localhost/test/dogs/-/reconcile")
        assert 200 == response.status_code
        data = response.json()
        assert "extend" in data
        assert data["extend"]["propose_properties"]["service_url"] == "http://localhost//test/dogs/-/reconcile"
        assert data["extend"]["property_settings"][3]["name"] == "status"
        assert len(data["suggest"]) == 3


@pytest.mark.asyncio
async def test_response_queries_post(db_path):
    app = Datasette([db_path], metadata=plugin_metadata({"name_field": "name"})).app()
    async with httpx.AsyncClient(app=app) as client:
        response = await client.post(
            "http://localhost/test/dogs/-/reconcile",
            data={"queries": json.dumps({"q0": {"query": "fido"}})},
        )
        assert 200 == response.status_code
        data = response.json()
        assert "q0" in data.keys()
        assert len(data["q0"]["result"]) == 1
        result = data["q0"]["result"][0]
        assert result["id"] == "3"
        assert result["name"] == "Fido"
        assert result["score"] == 100
        assert result["type"] == [
            {
                "name": "Object",
                "id": "object",
            }
        ]
        assert response.headers["Access-Control-Allow-Origin"] == "*"


@pytest.mark.asyncio
async def test_response_queries_get(db_path):
    app = Datasette([db_path], metadata=plugin_metadata({"name_field": "name"})).app()
    async with httpx.AsyncClient(app=app) as client:
        queries = json.dumps({"q0": {"query": "fido"}})
        response = await client.get(f"http://localhost/test/dogs/-/reconcile?queries={queries}")
        assert 200 == response.status_code
        data = response.json()
        assert "q0" in data.keys()
        assert len(data["q0"]["result"]) == 1
        result = data["q0"]["result"][0]
        assert result["id"] == "3"
        assert result["name"] == "Fido"
        assert result["score"] == 100
        assert result["type"] == [
            {
                "name": "Object",
                "id": "object",
            }
        ]
        assert response.headers["Access-Control-Allow-Origin"] == "*"


@pytest.mark.asyncio
async def test_response_queries_no_results_post(db_path):
    app = Datasette([db_path], metadata=plugin_metadata({"name_field": "name"})).app()
    async with httpx.AsyncClient(app=app) as client:
        response = await client.post(
            "http://localhost/test/dogs/-/reconcile",
            data={"queries": json.dumps({"q0": {"query": "abcdef"}})},
        )
        assert 200 == response.status_code
        data = response.json()
        assert "q0" in data.keys()
        assert len(data["q0"]["result"]) == 0
        assert response.headers["Access-Control-Allow-Origin"] == "*"


@pytest.mark.asyncio
async def test_response_queries_no_results_get(db_path):
    app = Datasette([db_path], metadata=plugin_metadata({"name_field": "name"})).app()
    async with httpx.AsyncClient(app=app) as client:
        queries = json.dumps({"q0": {"query": "abcdef"}})
        response = await client.get(f"http://localhost/test/dogs/-/reconcile?queries={queries}")
        assert 200 == response.status_code
        data = response.json()
        assert "q0" in data.keys()
        assert len(data["q0"]["result"]) == 0
        assert response.headers["Access-Control-Allow-Origin"] == "*"


@pytest.mark.asyncio
async def test_response_propose_properties(db_path):
    app = Datasette([db_path], metadata=plugin_metadata({"name_field": "name"})).app()
    async with httpx.AsyncClient(app=app) as client:
        response = await client.get("http://localhost/test/dogs/-/reconcile/extend/propose?type=object")
        assert 200 == response.status_code
        data = response.json()
        assert len(data["properties"]) == 4
        result = data["properties"][3]
        assert result["name"] == "status"
        assert result["id"] == "status"
        assert response.headers["Access-Control-Allow-Origin"] == "*"


@pytest.mark.asyncio
async def test_response_extend(db_path):
    app = Datasette([db_path], metadata=plugin_metadata({"name_field": "name"})).app()
    async with httpx.AsyncClient(app=app) as client:
        extend = {"extend": json.dumps({"ids": ["1", "2", "3", "4"], "properties": [{"id": "status"}, {"id": "age"}]})}
        response = await client.post("http://localhost/test/dogs/-/reconcile", data=extend)
        assert 200 == response.status_code
        data = response.json()

        assert "meta" in data
        assert data["meta"][0]["id"] == "status"
        assert data["meta"][0]["name"] == "status"
        assert "rows" in data

        expect = {
            "1": "good dog",
            "2": "bad dog",
            "3": "bad dog",
            "4": "good dog",
        }

        for key in expect.keys():
            assert data["rows"][key]["status"][0]["str"] == expect[key]

        expect_nums = {
            "1": 5,
            "2": 4,
            "3": 3,
            "4": 3,
        }

        for key in expect_nums.keys():
            assert data["rows"][key]["age"][0]["int"] == expect_nums[key]

        assert response.headers["Access-Control-Allow-Origin"] == "*"


@pytest.mark.asyncio
async def test_response_suggest_entity(db_path):
    app = Datasette([db_path], metadata=plugin_metadata({"name_field": "name"})).app()
    async with httpx.AsyncClient(app=app) as client:
        response = await client.get("http://localhost/test/dogs/-/reconcile/suggest/entity?prefix=f")
        assert 200 == response.status_code
        data = response.json()

        assert "result" in data
        assert data["result"][0]["id"] == 3
        assert data["result"][0]["name"] == "Fido"
        assert response.headers["Access-Control-Allow-Origin"] == "*"


@pytest.mark.asyncio
async def test_response_suggest_property(db_path):
    app = Datasette([db_path], metadata=plugin_metadata({"name_field": "name"})).app()
    async with httpx.AsyncClient(app=app) as client:
        response = await client.get("http://localhost/test/dogs/-/reconcile/suggest/property?prefix=a")
        assert 200 == response.status_code
        data = response.json()

        assert "result" in data
        assert data["result"][0]["id"] == "age"
        assert data["result"][0]["name"] == "age"
        assert response.headers["Access-Control-Allow-Origin"] == "*"


@pytest.mark.asyncio
async def test_response_suggest_type(db_path):
    app = Datasette([db_path], metadata=plugin_metadata({"name_field": "name"})).app()
    async with httpx.AsyncClient(app=app) as client:
        response = await client.get("http://localhost/test/dogs/-/reconcile/suggest/type?prefix=a")
        assert 200 == response.status_code
        data = response.json()

        assert "result" in data
        assert len(data["result"]) == 0
        assert response.headers["Access-Control-Allow-Origin"] == "*"
