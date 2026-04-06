import os
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from google import genai
from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter()

class LawyerRequest(BaseModel):
    query: str

@router.get("/daily-briefing")
async def get_daily_briefing():
    db = get_supabase()
    
    # 1. Fetch 5 active tasks
    tasks_res = db.table("tasks").select("*").limit(5).execute()
    tasks = tasks_res.data or []
    
    # 2. Fetch inventory shortages (< 5)
    inv_res = db.table("inventory").select("*").lt("quantity", 5).execute()
    shortages = inv_res.data or []
    
    # 3. Calculate latest balance
    trans_res = db.table("transactions").select("amount", "type").execute()
    balance = 0.0
    for t in (trans_res.data or []):
        if t["type"] == "income":
            balance += float(t["amount"])
        elif t["type"] == "expense":
            balance -= float(t["amount"])
    
    prompt = (
        "Ты - бизнес-наставник. Посмотри на эти данные:\n"
        f"Текущий баланс пользователя: {balance} сом.\n"
        f"Нерешенные задачи: {tasks}\n"
        f"Заканчиваются товары: {shortages}\n"
        "Выдай ОДИН короткий, жесткий совет на сегодня без форматирования и воды. "
        "Говори как опытный предприниматель. До 2 предложений."
    )
    
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        advice = response.text.replace("\n", " ").strip()
        # Clean up any potential markdown
        advice = advice.replace("*", "").replace("#", "")
        return {"advice": advice}
    except Exception as e:
        logger.error(f"Error getting daily briefing: {e}")
        return {"advice": "Оглянитесь вокруг: контроль склада и выполнение задач - залог стабильного роста. Приступайте к делам."}


@router.post("/ask-lawyer")
async def ask_lawyer_bot(req: LawyerRequest):
    prompt = (
        "Ты профессиональный юрист и налоговый консультант для бизнеса в СНГ (Кыргызстан). "
        "Отвечай ТОЛЬКО в контексте налогов, лицензий, законов и бизнес-рисков. Если вопрос не про бизнес "
        "или не про законы, откажись отвечать. Отвечай кратко, без лишней воды и форматирования.\n"
        f"Вопрос предпринимателя: {req.query}"
    )
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        text = response.text.replace("\n", " ").strip()
        return {"answer": text}
    except Exception as e:
        logger.error(f"Error asking lawyer bot: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервиса ИИ-юриста.")
