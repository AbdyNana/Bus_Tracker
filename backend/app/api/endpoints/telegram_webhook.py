import logging
from fastapi import APIRouter, Request, HTTPException
from app.agents.brain import parse_intent
from app.db.supabase_client import get_supabase
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    try:
        update = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
        
    message = update.get("message", {})
    text = message.get("text")
    chat_id = message.get("chat", {}).get("id")
    
    if not text:
        return {"status": "ignored", "reason": "No text"}

    logger.info(f"Telegram Webhook received: {text}")

    # Forward to Brain
    try:
        intent = parse_intent(text=text)
        intent_type = intent.get("type")
        
        if intent_type in ["calendar_event", "task_creation"]:
            db = get_supabase()
            event = intent.get("event", {})
            title = event.get("title", text)
            dt_str = event.get("datetime")
            
            # Use current time if no datetime provided
            if not dt_str:
                dt_str = datetime.now().isoformat()
                
            task_data = {
                "title": title,
                "datetime": dt_str,
                "description": event.get("description", "Created via Telegram")
            }
            
            response = db.table("tasks").insert(task_data).execute()
            logger.info(f"Saved telegram task: {response.data}")
            
            # Send message back to Telegram via bot token (optional if configured)
            # We don't have python-telegram-bot set up natively yet, so just return
            return {"status": "saved", "task": response.data[0]}

        return {"status": "processed_but_not_saved", "intent": intent}
        
    except Exception as e:
        logger.error(f"Telegram Webhook error: {e}")
        return {"status": "error", "error": str(e)}
