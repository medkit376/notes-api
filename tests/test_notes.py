import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_create_note_requires_auth(client: AsyncClient):
    resp = await client.post("/api/v1/notes", json={"title": "Untitled", "content": ""})
    assert resp.status_code == 401


async def test_create_and_get_note(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/notes",
        json={"title": "Groceries", "content": "Milk, eggs", "tags": ["home", "errands"]},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    note = resp.json()
    assert note["title"] == "Groceries"
    assert note["tags"] == ["home", "errands"]

    resp = await client.get(f"/api/v1/notes/{note['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == note["id"]


async def test_get_nonexistent_note(client: AsyncClient, auth_headers: dict):
    resp = await client.get(
        "/api/v1/notes/00000000-0000-0000-0000-000000000000", headers=auth_headers
    )
    assert resp.status_code == 404


async def test_update_note(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/notes",
        json={"title": "Draft", "content": "v1", "tags": ["work"]},
        headers=auth_headers,
    )
    note_id = resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/notes/{note_id}",
        json={"content": "v2", "tags": ["work", "urgent"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["content"] == "v2"
    assert updated["title"] == "Draft"  # unchanged
    assert updated["tags"] == ["work", "urgent"]


async def test_delete_note(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/notes", json={"title": "Temp", "content": ""}, headers=auth_headers
    )
    note_id = resp.json()["id"]

    resp = await client.delete(f"/api/v1/notes/{note_id}", headers=auth_headers)
    assert resp.status_code == 204

    resp = await client.get(f"/api/v1/notes/{note_id}", headers=auth_headers)
    assert resp.status_code == 404


async def test_pagination(client: AsyncClient, auth_headers: dict):
    for i in range(15):
        await client.post(
            "/api/v1/notes",
            json={"title": f"Note {i}", "content": ""},
            headers=auth_headers,
        )

    resp = await client.get("/api/v1/notes?page=1&page_size=10", headers=auth_headers)
    body = resp.json()
    assert body["total"] == 15
    assert body["page"] == 1
    assert body["pages"] == 2
    assert len(body["items"]) == 10

    resp = await client.get("/api/v1/notes?page=2&page_size=10", headers=auth_headers)
    body = resp.json()
    assert len(body["items"]) == 5


async def test_tag_filtering(client: AsyncClient, auth_headers: dict):
    await client.post(
        "/api/v1/notes",
        json={"title": "A", "content": "", "tags": ["work"]},
        headers=auth_headers,
    )
    await client.post(
        "/api/v1/notes",
        json={"title": "B", "content": "", "tags": ["personal"]},
        headers=auth_headers,
    )
    await client.post(
        "/api/v1/notes",
        json={"title": "C", "content": "", "tags": ["work", "urgent"]},
        headers=auth_headers,
    )

    resp = await client.get("/api/v1/notes?tag=work", headers=auth_headers)
    body = resp.json()
    assert body["total"] == 2
    titles = {n["title"] for n in body["items"]}
    assert titles == {"A", "C"}


async def test_notes_are_isolated_per_user(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register", json={"email": "u1@example.com", "password": "pass12345"}
    )
    login1 = await client.post(
        "/api/v1/auth/login", data={"username": "u1@example.com", "password": "pass12345"}
    )
    headers1 = {"Authorization": f"Bearer {login1.json()['access_token']}"}

    await client.post(
        "/api/v1/auth/register", json={"email": "u2@example.com", "password": "pass12345"}
    )
    login2 = await client.post(
        "/api/v1/auth/login", data={"username": "u2@example.com", "password": "pass12345"}
    )
    headers2 = {"Authorization": f"Bearer {login2.json()['access_token']}"}

    resp = await client.post(
        "/api/v1/notes", json={"title": "User1 note", "content": ""}, headers=headers1
    )
    note_id = resp.json()["id"]

    # user2 should not be able to see user1's note
    resp = await client.get(f"/api/v1/notes/{note_id}", headers=headers2)
    assert resp.status_code == 404

    resp = await client.get("/api/v1/notes", headers=headers2)
    assert resp.json()["total"] == 0
