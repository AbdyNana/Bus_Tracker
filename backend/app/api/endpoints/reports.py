import os
from fastapi import APIRouter
from fastapi.responses import FileResponse, StreamingResponse
from app.services.report_service import generate_inventory_pdf, generate_inventory_excel

router = APIRouter()


@router.get("/reports/inventory/pdf")
async def get_inventory_pdf():
    pdf_path = generate_inventory_pdf()
    return FileResponse(pdf_path, media_type="application/pdf", filename="inventory_report.pdf")


@router.get("/reports/inventory/excel")
async def get_inventory_excel():
    """Smart Excel report: Sheet 1 = AI Сводка, Sheet 2 = База Склада."""
    excel_buffer = generate_inventory_excel()
    return StreamingResponse(
        excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="inventory_report.xlsx"'},
    )
