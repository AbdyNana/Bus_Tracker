"""
Agent 2: The Brain (LLM Intent Router)
Uses the NEW google-genai SDK to classify user intent.

Strictly follows the AI Constitution:
- Returns ONLY valid JSON (enforced via response_mime_type)
- Never hallucinates phone numbers
- Uses system date 2026-03-27 for all relative date calculations
"""
import os
import time
import json
import logging
import traceback
from pathlib import Path
from dotenv import load_dotenv

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# --- Environment Setup (Absolute Path) ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not api_key:
    logger.error(f"КРИТИЧЕСКАЯ ОШИБКА: Ключ API не найден. Путь: {env_path}")
    raise ValueError("API Key is missing")

# Initialize the NEW GenAI Client
client = genai.Client(api_key=api_key)

from datetime import datetime
import re

def get_constitution() -> str:
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_human = datetime.now().strftime("%d %B %Y")
    
    return f"""Ты — ядро Executive AI Concierge «SUB_Tracker» и эксперт "Spellchecker & Geo-Optimizer".
Сегодня строго: {today_human} ({today_str}), GMT+6, Бишкек.

═══ КОНСТИТУЦИЯ МАРШРУТИЗАЦИИ (INTENT CLASH RULES) ═══
1. ПРАВИЛО ПОИСКА (need_contact_search): Если запрос содержит просьбу "найти", "забронировать", "позвонить" в заведение (ресторан, кафе и т.д.), но НЕ УКАЗАНО ТОЧНОЕ ВРЕМЯ ИЛИ ДАТА — всегда возвращай need_contact_search.
2. ПРАВИЛО КАЛЕНДАРЯ (calendar_event): Возвращай этот интент ТОЛЬКО если в запросе ЯВНО присутствует время или дата (например: "сегодня к 18:00", "завтра утром").
3. ПРАВИЛО ПРОДАЖИ (sell_item): Если юзер говорит о продаже товара (например, "продал макбук за 120000"), возвращай intent sell_item с указанием имени товара, суммы и количества.

═══ ОБЩИЕ ПРАВИЛА (НАРУШЕНИЕ = СБОЙ СИСТЕМЫ) ═══
3. Отвечай ТОЛЬКО валидным JSON-объектом без markdown-оберток.
4. Включай в корень JSON ключ "transcribed_text" с точной расшифровкой.
5. ИСПРАВЛЯЙ ОПЕЧАТКИ (Spellchecker) в запросах на поиск. ("ресторан зира" -> "Zira")
6. В поле `query` возвращай ЧИСТЫЙ `target_name` (только название заведения, без "ресторан", "кафе" и БЕЗ ГЕОГРАФИИ). Например для "ресторан Чайковский" верни "Чайковский".
7. Для атрибута `city` выуживай город из контекста (по умолчанию "Бишкек").
8. НИКОГДА не придумывай телефонные номера. Возвращай need_contact_search для поиска.
9. Относительные даты (завтра, через два дня, в пятницу) вычисляй строго от {today_str}.
10. Слушай команды на удаление (например, "удали дела на 30 мая").

═══ ФОРМАТЫ ОТВЕТОВ ═══
• Календарь (создание): {{"type":"calendar_event","transcribed_text":"...","title":"...","datetime":"{today_str}T18:00:00","description":"..."}}
• Календарь (удаление): {{"type":"clear_calendar","transcribed_text":"...","date":"{today_str}"}}
• Склад (обновление): {{"type":"inventory_update","transcribed_text":"...","action":"add","item":"яблоки","quantity":10,"price":1000}}
• Касса (продажа): {{"type":"sell_item","transcribed_text":"...","item":"макбук","amount":120000,"quantity":1}}
• Отчет: {{"type":"generate_report","transcribed_text":"..."}}
• Поиск: {{"type":"need_contact_search","transcribed_text":"...","query":"Нават","city":"Бишкек"}}
• Электронная почта: {{"type":"send_email","transcribed_text":"...","to_email":"почта","subject":"тема","generated_body":"вежливый текст письма..."}}
• Сообщение: {{"type":"send_message","transcribed_text":"...","platform":"whatsapp","text":"...","links":[]}}
• Ошибка: {{"type":"error","transcribed_text":"...","message":"..."}}
"""
import re

def parse_intent(text: str = None, audio_bytes: bytes = None, mime_type: str = None) -> dict:
    """
    Send text or audio natively to Gemini 2.0 Flash (via google-genai), return parsed intent dict.
    """
    if not text and not audio_bytes:
        return {"type": "error", "message": "Пустой запрос."}

    MAX_RETRIES = 3
    RETRY_DELAY = 1 # seconds

    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"Brain (Multimodal) [Attempt {attempt+1}]: processing...")
            
            parts = []
            if audio_bytes:
                if not mime_type:
                    mime_type = "audio/ogg"
                # Defaulting to popular audio mime types or raw audio input
                parts.append(types.Part.from_bytes(data=audio_bytes, mime_type=mime_type))
            if text:
                parts.append(text)
            
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=parts,
                config=types.GenerateContentConfig(
                    system_instruction=get_constitution(),
                    temperature=0.1,
                    response_mime_type="application/json"
                )
            )
            
            raw = response.text.strip()
            
            # Clean potential Markdown backticks added by LLM
            if raw.startswith("```json"):
                raw = raw[7:]
            elif raw.startswith("```"):
                raw = raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()
            
            logger.info(f"Brain: raw response → {raw}")
            
            result = json.loads(raw)
            if isinstance(result, list) and len(result) > 0:
                result = result[0]
            return result

        except Exception as e:
            err_str = str(e)
            logger.error(f"Brain Error: {err_str}")
            
            # 🚨 PRESENTATION RESCUE MODE (DEMO FALLBACK) 🚨
            if "429" in err_str or "quota" in err_str.lower() or "exhausted" in err_str.lower() or "limit" in err_str.lower() or "503" in err_str:
                logger.warning("Brain: API Quota exhausted or Service Unavailable. Activating DEMO FALLBACK MODE!")
                return {
                    "type": "error",
                    "message": "Система перегружена или исчерпан лимит нейросети. Попробуйте еще раз позже."
                }
                    
            if "503" in err_str and attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                logger.warning(f"Brain: Service spike detected ({err_str}). Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            
            if isinstance(e, json.JSONDecodeError):
                logger.error(f"Brain: Invalid JSON from AI — {e}")
                return {"type": "error", "message": "Ошибка формата ответа ИИ."}
            
            logger.error(f"Brain: Critical Error (Not a quota issue) — {e}")
            return {"type": "error", "message": "Внутренняя ошибка сервера (проверьте консоль)."}

    return {"type": "error", "message": "Непредвиденная ошибка обработки интента."}
