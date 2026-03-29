"""
Endpoint: GET /api/tasks
Returns scheduled tasks for a specific date from Supabase.
Used by the calendar widget on the frontend/mobile.
"""
import logging
from fastapi import APIRouter, Query, HTTPException
from app.db.supabase_client import get_supabase

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/tasks")
async def get_tasks(date: str = Query(..., description="Date in YYYY-MM-DD format")):
    """
    Returns all tasks for a given date.
    Example: GET /api/tasks?date=2026-03-28
    """
    if not date or len(date) != 10:
        raise HTTPException(status_code=400, detail="Date must be in YYYY-MM-DD format")

    try:
        db = get_supabase()
        # Filter tasks where datetime starts with the given date
        result = (
            db.table("tasks")
            .select("*")
            .gte("datetime", f"{date}T00:00:00")
            .lte("datetime", f"{date}T23:59:59")
            .order("datetime")
            .execute()
        )
        tasks = result.data or []
        logger.info(f"Fetched {len(tasks)} tasks for {date}")
        return {
            "date": date,
            "count": len(tasks),
            "tasks": tasks,
        }
    except Exception as e:
        logger.error(f"Error fetching tasks: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

from pydantic import BaseModel
class TaskCreate(BaseModel):
    title: str
    datetime: str
    description: str = ""

@router.post("/tasks")
async def create_task(task: TaskCreate):
    """
    Creates a new task manually.
    """
    try:
        db = get_supabase()
        result = db.table("tasks").insert({
            "title": task.title,
            "datetime": task.datetime,
            "description": task.description
        }).execute()
        return {"status": "success", "task": result.data[0] if result.data else None}
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.delete("/tasks")
async def delete_tasks(date: str = Query(..., description="Date in YYYY-MM-DD format")):
    """
    Deletes all tasks for a specific date.
    """
    if not date or len(date) != 10:
        raise HTTPException(status_code=400, detail="Date must be in YYYY-MM-DD format")
        
    try:
        db = get_supabase()
        result = (
            db.table("tasks")
            .delete()
            .gte("datetime", f"{date}T00:00:00")
            .lte("datetime", f"{date}T23:59:59")
            .execute()
        )
        return {"status": "success", "message": f"Tasks for {date} deleted.", "data": result.data}
    except Exception as e:
        logger.error(f"Error deleting tasks: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.put("/tasks/{task_id}")
async def update_task(task_id: int, task: TaskCreate):
    """
    Updates an existing task manually.
    """
    try:
        db = get_supabase()
        result = db.table("tasks").update({
            "title": task.title,
            "datetime": task.datetime,
            "description": task.description
        }).eq("id", task_id).execute()
        return {"status": "success", "task": result.data[0] if result.data else None}
    except Exception as e:
        logger.error(f"Error updating task: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
