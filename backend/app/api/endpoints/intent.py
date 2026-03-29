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
        query = intent.get("query", req.text)
        scrape_result = search_contacts(query)
        return {
            "type": "need_contact_search",
            **scrape_result,
        }

    # --- Scenario 4: Send Message (Deep-links) ---
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
