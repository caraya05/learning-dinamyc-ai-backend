import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from .routers import router

app = FastAPI()
app.include_router(router)

client = TestClient(app)

def test_create_item():
    response = client.post("/model-test/items", json={"name": "Test", "description": "Desc"})
    assert response.status_code == 201
    assert response.json()["name"] == "Test"

def test_list_items():
    client.post("/model-test/items", json={"name": "Test2", "description": "Desc2"})
    response = client.get("/model-test/items")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
