from fastapi import APIRouter, HTTPException
from app.db.supabase_client import get_supabase
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/finance/balance")
async def get_balance():
    db = get_supabase()
    try:
        response = db.table("transactions").select("*").order("created_at", desc=True).execute()
        transactions = response.data or []
        balance = 0.0
        for t in transactions:
            if t["type"] == "income":
                balance += float(t["amount"])
            elif t["type"] == "expense":
                balance -= float(t["amount"])
                
        return {"status": "success", "balance": balance, "transactions": transactions}
    except Exception as e:
        logger.error(f"Error fetching balance: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
