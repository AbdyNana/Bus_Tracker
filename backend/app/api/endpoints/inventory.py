from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.db.supabase_client import get_supabase
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class InventoryItem(BaseModel):
    name: str
    category: Optional[str] = "Без категории"
    quantity: int = 0
    price: Optional[float] = 0.0

@router.get("/inventory")
async def get_inventory():
    db = get_supabase()
    try:
        response = db.table("inventory").select("*").order("name").execute()
        return {"items": response.data}
    except Exception as e:
        logger.error(f"Error fetching inventory: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/inventory")
async def add_inventory(item: InventoryItem):
    db = get_supabase()
    try:
        response = db.table("inventory").insert({
            "name": item.name,
            "category": item.category,
            "quantity": item.quantity,
            "price": item.price
        }).execute()
        return {"status": "success", "item": response.data[0]}
    except Exception as e:
        logger.error(f"Error adding inventory: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/inventory/{item_id}")
async def update_inventory(item_id: int, item: InventoryItem):
    db = get_supabase()
    try:
        response = db.table("inventory").update({
            "name": item.name,
            "category": item.category,
            "quantity": item.quantity,
            "price": item.price
        }).eq("id", item_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Item not found")
            
        return {"status": "success", "item": response.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating inventory: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/inventory/{item_id}")
async def delete_inventory(item_id: int):
    db = get_supabase()
    try:
        response = db.table("inventory").delete().eq("id", item_id).execute()
        return {"status": "deleted", "id": item_id}
    except Exception as e:
        logger.error(f"Error deleting inventory: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
