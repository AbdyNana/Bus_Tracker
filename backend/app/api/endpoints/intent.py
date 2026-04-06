"""
Endpoint: POST /api/process-intent
The core orchestrator. Receives text, routes through Agents 2 & 3,
saves to Supabase if needed, returns structured JSON for the UI.
"""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.agents.brain import parse_intent
from app.agents.bulldozer import search_contacts
from app.db.supabase_client import get_supabase
from app.services.twogis_service import search_places_2gis
from app.services.email_service import send_generated_email
import asyncio

router = APIRouter()
logger = logging.getLogger(__name__)


class IntentRequest(BaseModel):
    text: str


@router.post("/process-intent")
async def process_intent(req: IntentRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    # Agent 2: The Brain — parse intent
    intent = parse_intent(req.text)
    intent_type = intent.get("type")

    # --- Scenario 1: Calendar Event ---
    if intent_type == "calendar_event":
        try:
            db = get_supabase()
            insert_data = {
                "title": intent.get("title", req.text),
                "datetime": intent.get("datetime"),
                "description": intent.get("description", ""),
            }
            result = db.table("tasks").insert(insert_data).execute()
            task_id = result.data[0]["id"] if result.data else None
            return {
                "type": "calendar_event",
                "status": "saved",
                "task_id": task_id,
                "event": insert_data,
                "message": f"✅ Задача «{insert_data['title']}» добавлена в календарь.",
            }
        except Exception as e:
            logger.error(f"Supabase insert error: {e}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    # --- Scenario 2: Clear Calendar ---
    elif intent_type == "clear_calendar":
        try:
            date = intent.get("date")
            if not date:
                return {"type": "error", "message": "Не удалось определить дату для очистки."}
                
            db = get_supabase()
            db.table("tasks").delete().gte("datetime", f"{date}T00:00:00").lte("datetime", f"{date}T23:59:59").execute()
            
            return {
                "type": "clear_calendar",
                "date": date,
                "message": f"🗑 Расписание на {date} очищено."
            }
        except Exception as e:
            logger.error(f"Supabase delete error: {e}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    # --- Scenario 3: Need Contact Search ---
    elif intent_type == "need_contact_search":
        # Gemini puts location context directly via Geo-Optimizer
        query = intent.get("query", req.text)
        city = intent.get("city", "Бишкек")
        
        twogis_task = search_places_2gis(query=query, location=city)
        google_task = asyncio.to_thread(search_contacts, query)
        
        twogis_res, google_res = await asyncio.gather(twogis_task, google_task, return_exceptions=True)
        
        combined_contacts = []
        if isinstance(twogis_res, dict) and twogis_res.get("found"):
            combined_contacts.extend(twogis_res.get("contacts", []))
        if isinstance(google_res, dict) and google_res.get("found"):
            combined_contacts.extend(google_res.get("contacts", []))
            
        found = len(combined_contacts) > 0
        
        return {
            "type": "need_contact_search",
            "found": found,
            "query": query,
            "contacts": combined_contacts,
            "message": "Aggregated results." if found else f"Заведение '{query}' не найдено.",
            "source_url": combined_contacts[0]["source_url"] if found and "source_url" in combined_contacts[0] else ""
        }

    # --- Scenario 3.5: Inventory Update ---
    elif intent_type == "inventory_update":
        db = get_supabase()
        action = intent.get("action")
        item_name = intent.get("item")
        quantity = intent.get("quantity", 0)
        
        try:
            res = db.table("inventory").select("*").ilike("name", item_name).execute()
            if res.data:
                item = res.data[0]
                new_qty = item["quantity"] or 0
                if action == "add":
                    new_qty += quantity
                elif action == "remove":
                    new_qty = max(0, new_qty - quantity)
                elif action == "set":
                    new_qty = quantity
                
                db.table("inventory").update({"quantity": new_qty}).eq("id", item["id"]).execute()
                return {"type": "inventory_update", "status": "success", "message": f"Остаток '{item_name}' обновлен. Теперь на складе: {new_qty}."}
            else:
                if action in ["add", "set"]:
                    db.table("inventory").insert({"name": item_name, "quantity": quantity}).execute()
                    return {"type": "inventory_update", "status": "success", "message": f"Товар '{item_name}' добавлен на склад. Количество: {quantity}."}
                else:
                    return {"type": "inventory_update", "status": "error", "message": f"Товар '{item_name}' не найден на складе."}
        except Exception as e:
            logger.error(f"Inventory Update Error: {e}")
            return {"type": "error", "message": str(e)}

    # --- Scenario 3.8: Analytics Report ---
    elif intent_type == "generate_report":
        return {
            "type": "generate_report",
            "status": "success",
            "message": "Генерирую PDF-отчет аналитики. Ожидайте загрузку."
        }
        
    # --- Scenario 4: Send Email ---
    elif intent_type == "send_email":
        to_email = intent.get("to_email", "")
        subject = intent.get("subject", "Бизнес-уведомление (SUB_Tracker)")
        body = intent.get("generated_body", "")
        
        if not to_email:
            return {"type": "error", "message": "Email адрес не распознан. Пожалуйста, укажите почту."}

        success = await send_generated_email(to_email, subject, body)
        if success:
            return {"type": "send_email", "status": "success", "message": f"Письмо успешно отправлено на {to_email}"}
        else:
            return {"type": "send_email", "status": "error", "message": "Не удалось отправить письмо. Проверьте настройки SMTP (см. .env).", "generated_body": body}

    # --- Scenario 5: Send Message (Deep-links) ---
    elif intent_type == "send_message":
        return {
            "type": "send_message",
            "platform": intent.get("platform"),
            "text": intent.get("text"),
            "links": intent.get("links", []),
        }

    # --- Error / Off-topic ---
    elif intent_type == "error":
        return intent

    else:
        logger.warning(f"Unknown intent type: {intent_type}")
        return {"type": "error", "message": "Не удалось распознать намерение."}
