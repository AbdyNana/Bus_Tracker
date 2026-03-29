"""
Endpoint: POST /api/process-voice
Accepts audio file upload (any format: ogg, mp3, m4a, wav, flac).
Runs STT via Agent 1 (The Ear), then routes to intent logic.
"""
import logging
import traceback
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.agents.ear import transcribe_audio
from app.agents.brain import parse_intent
from app.agents.bulldozer import search_contacts
from app.db.supabase_client import get_supabase

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/process-voice")
async def process_voice(audio: UploadFile = File(...)):
    """
    Full pipeline: Audio → STT → Intent → Action → JSON response.
    Returns structured JSON matching /api/process-intent schema.
    """
    # --- Validation ---
    if not audio or not audio.filename:
        raise HTTPException(status_code=400, detail="No audio file provided.")

    try:
        audio_bytes = await audio.read()
    except Exception as e:
        logger.error(f"Failed to read uploaded file: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=f"Не удалось прочитать файл: {e}")

    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Загруженный аудиофайл пустой.")

    logger.info(f"Voice upload received: filename='{audio.filename}', size={len(audio_bytes)} bytes")

    # --- Agent 1: The Ear — STT ---
    try:
        text = transcribe_audio(audio_bytes, filename=audio.filename)
    except RuntimeError as e:
        # STT API error or audio conversion failure — detailed 503
        logger.error(f"STT pipeline failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=503,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected STT error: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Внутренняя ошибка STT: {e}",
        )

    if not text:
        return {
            "type": "error",
            "transcribed_text": "",
            "message": "Не удалось распознать речь. Говорите четче или повторите.",
        }

    logger.info(f"Proceeding with transcribed text: '{text}'")

    # --- Agent 2: The Brain — Intent Routing ---
    try:
        intent = parse_intent(text)
    except Exception as e:
        logger.error(f"Brain (LLM) error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Ошибка AI-обработки: {e}")

    intent_type = intent.get("type")

    # --- Scenario 1: Calendar Event ---
    if intent_type == "calendar_event":
        try:
            db = get_supabase()
            insert_data = {
                "title": intent.get("title", text),
                "datetime": intent.get("datetime"),
                "description": intent.get("description", ""),
            }
            result = db.table("tasks").insert(insert_data).execute()
            task_id = result.data[0]["id"] if result.data else None
            return {
                "type": "calendar_event",
                "transcribed_text": text,
                "status": "saved",
                "task_id": task_id,
                "event": insert_data,
                "message": f"✅ Задача «{insert_data['title']}» добавлена в календарь.",
            }
        except Exception as e:
            logger.error(f"Supabase insert error: {e}\n{traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Ошибка базы данных: {e}")

    # --- Scenario 2: Need Contact Search ---
    elif intent_type == "need_contact_search":
        query = intent.get("query", text)
        try:
            scrape_result = search_contacts(query)
        except Exception as e:
            logger.error(f"Bulldozer scraper error: {e}\n{traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Ошибка парсера: {e}")
        return {"type": "need_contact_search", "transcribed_text": text, **scrape_result}

    # --- Scenario 3: Send Message (Deep-links) ---
    elif intent_type == "send_message":
        return {
            "type": "send_message",
            "transcribed_text": text,
            "platform": intent.get("platform"),
            "text": intent.get("text"),
            "links": intent.get("links", []),
        }

    # --- Error / Off-topic from Brain ---
    return {**intent, "transcribed_text": text}
