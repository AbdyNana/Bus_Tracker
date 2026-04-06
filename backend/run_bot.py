import os
import sys
import io
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# Adjust python path to be able to import app package
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from app.agents.brain import parse_intent
from app.db.supabase_client import get_supabase

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StandaloneBot")

bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
if not bot_token:
    logger.error("TELEGRAM_BOT_TOKEN is not set in environment or .env file.")
    sys.exit(1)

bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

def process_intent_with_db(result: dict) -> str:
    """Processes the Brain's intent by making structural changes exactly like the API."""
    intent_type = result.get("type", "")
    db = get_supabase()
    
    if intent_type == "calendar_event":
        db.table("tasks").insert({
            "title": result.get("title", "Новая задача"),
            "datetime": result.get("datetime", ""),
            "description": result.get("description", "")
        }).execute()
        return f"✅ Событие \"{result.get('title', '')}\" добавлено на {result.get('datetime', '')}."
        
    elif intent_type == "clear_calendar":
        date = result.get("date", "")
        db.table("tasks").delete().gte("datetime", f"{date}T00:00:00").lte("datetime", f"{date}T23:59:59").execute()
        return f"🗑 Сброшен календарь на {date}."
        
    elif intent_type == "inventory_update":
        action = result.get("action", "add")
        item_name = result.get("item", "")
        qty = result.get("quantity", 0)
        
        # Check if item exists
        existing = db.table("inventory").select("*").ilike("name", item_name).execute()
        if existing.data and len(existing.data) > 0:
            target = existing.data[0]
            new_qty = target["quantity"] + qty if action == "add" else target["quantity"] - qty
            new_qty = max(0, new_qty)
            
            update_data = {"quantity": new_qty}
            if action == "add" and "price" in result:
                update_data["price"] = result.get("price", 0.0)
                
            db.table("inventory").update(update_data).eq("id", target["id"]).execute()
            return f"📦 Склад обновлен ({item_name}: теперь {new_qty} шт)."
        else:
            if action == "add":
                db.table("inventory").insert({
                    "name": item_name.capitalize(),
                    "category": "Автосоздано (Бот)",
                    "quantity": qty,
                    "price": result.get("price", 0.0)
                }).execute()
                return f"📦 Склад: добавлен новый товар ({item_name} - {qty} шт)."
            else:
                return f"📦 Списание отменено: товар {item_name} не найден в базе."
                
    elif intent_type == "sell_item":
        item_name = result.get("item", "")
        amount = result.get("amount", 0)
        qty = result.get("quantity", 1)
        
        # 1. Списать со склада
        existing = db.table("inventory").select("*").ilike("name", item_name).execute()
        if existing.data and len(existing.data) > 0:
            target = existing.data[0]
            new_qty = max(0, target["quantity"] - qty)
            db.table("inventory").update({"quantity": new_qty}).eq("id", target["id"]).execute()
        
        # 2. Добавить в кассу (транзакцию)
        db.table("transactions").insert({
            "type": "income",
            "amount": amount,
            "description": f"Продажа: {item_name} ({qty} шт)"
        }).execute()
        
        return f"💰 Продажа: {item_name} на {amount} сом. Товар списан, касса пополнена."
                
    elif intent_type == "error":
        return f"❌ Ошибка ИИ: {result.get('message', 'Неизвестная ошибка')}"
    
    return "Команда обработана: " + intent_type

@dp.message(F.text)
async def handle_text(message: types.Message):
    """Standalone message handler processing natural language via Brain's native multimodal function."""
    try:
        logger.info(f"Bot received text: {message.text}")
        result = parse_intent(text=message.text)
        reply_text = process_intent_with_db(result)
        await message.answer(reply_text)
    except Exception as e:
        logger.error(f"Error handling Telegram text message: {e}")
        await message.answer("⛔ Произошла системная ошибка при обработке БД или ИИ.")

@dp.message(F.voice)
async def handle_voice(message: types.Message):
    """Processes Voice commands flawlessly."""
    try:
        logger.info("Bot received Voice Message. Downloading...")
        
        # Download voice file natively using aiogram directly into memory
        file_io = io.BytesIO()
        await bot.download(message.voice, destination=file_io)
        audio_bytes = file_io.getvalue()
        
        logger.info(f"Downloaded {len(audio_bytes)} bytes of audio. Sending to Brain...")
        
        # The AI Brain knows how to natively stream this audio
        result = parse_intent(audio_bytes=audio_bytes, mime_type="audio/ogg")
        reply_text = process_intent_with_db(result)
        
        # Small contextual attachment
        transcription = result.get('transcribed_text', '')
        if transcription:
            reply_text = f"<i>«{transcription}»</i>\n\n{reply_text}"
            
        await message.answer(reply_text)
    except Exception as e:
        logger.error(f"Error handling Telegram voice message: {e}")
        await message.answer("⛔ Ошибка при расшифровке голосового сообщения.")

async def main():
    logger.info("Starting standalone Telegram bot polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
