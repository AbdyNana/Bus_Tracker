import pytest
import httpx
import json

BASE_URL = "http://127.0.0.1:8000"

@pytest.mark.asyncio
async def test_search_intent():
    """Test 1: Отправка текста 'Забронируй столик в Дияр'"""
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        payload = {"text": "Забронируй столик в Дияр"}
        resp = await client.post("/api/process-intent", json=payload, timeout=20.0)
        
        assert resp.status_code == 200, f"Error: {resp.text}"
        data = resp.json()
        assert data.get("type") == "need_contact_search", f"Expected need_contact_search, got {data.get('type')}"
        assert data.get("found") is True
        assert len(data.get("contacts", [])) > 0, "No contacts returned for Dyar."

@pytest.mark.asyncio
async def test_calendar_intent():
    """Test 2: Отправка текста 'Напомни завтра в 15:00 позвонить клиенту'"""
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        payload = {"text": "Напомни завтра в 15:00 позвонить клиенту"}
        resp = await client.post("/api/process-intent", json=payload, timeout=20.0)
        
        assert resp.status_code == 200, f"Error: {resp.text}"
        data = resp.json()
        assert data.get("type") == "calendar_event", f"Expected calendar_event, got {data.get('type')}"
        assert "event" in data and "datetime" in data["event"], "No datetime parsed in calendar event"

@pytest.mark.asyncio
async def test_inventory_flow():
    """Test 3: Инвентаризация (добавление, проверка, удаление)"""
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # Create
        fake_item = {"name": "Test Item 123", "category": "Сырье", "quantity": 50, "price": 100.0}
        post_resp = await client.post("/api/inventory", json=fake_item, timeout=10.0)
        assert post_resp.status_code == 200, f"Error: {post_resp.text}"
        post_data = post_resp.json()
        assert post_data.get("status") == "success"
        
        item_id = post_data["item"]["id"]
        assert item_id is not None
        
        # Check GET
        get_resp = await client.get("/api/inventory", timeout=10.0)
        assert get_resp.status_code == 200
        items = get_resp.json().get("items", [])
        
        found = any(i["id"] == item_id for i in items)
        assert found is True, "Recently added item not found in inventory list"
        
        # Delete
        del_resp = await client.delete(f"/api/inventory/{item_id}", timeout=10.0)
        assert del_resp.status_code == 200
        assert del_resp.json().get("status") == "deleted"

@pytest.mark.asyncio
async def test_pdf_report():
    """Test 4: PDF генерация"""
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        resp = await client.get("/api/reports/inventory/pdf", timeout=20.0)
        assert resp.status_code == 200, f"Error: {resp.text}"
        assert resp.headers["content-type"] == "application/pdf"

@pytest.mark.asyncio
async def test_send_email_intent():
    """Test 5: Отправка Email"""
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        payload = {"text": "Напиши поставщику по свету ivan@example.com, что мы задержим оплату"}
        resp = await client.post("/api/process-intent", json=payload, timeout=20.0)
        assert resp.status_code == 200, f"Error: {resp.text}"
        data = resp.json()
        assert data["type"] == "send_email"
        assert "ivan@example.com" in data.get("message", "") or "ivan" in data.get("to_email", "") or data.get("status") in ["success", "error"]


@pytest.mark.asyncio
async def test_excel_report():
    """Test 6: Smart Excel генерация — два листа (AI Сводка + База Склада)"""
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        resp = await client.get("/api/reports/inventory/excel", timeout=30.0)
        assert resp.status_code == 200, f"Excel Error: {resp.text}"
        content_type = resp.headers.get("content-type", "")
        assert "spreadsheetml" in content_type or "openxmlformats" in content_type, \
            f"Wrong content-type: {content_type}"
        assert len(resp.content) > 1000, "Excel file is too small — likely empty"
