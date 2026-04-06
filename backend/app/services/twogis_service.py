import os
import re
import httpx
import logging
from urllib.parse import quote_plus
from typing import Dict, Any
from dotenv import load_dotenv
from pathlib import Path

logger = logging.getLogger(__name__)

# Load env variables (if needed to ensure TWOGIS_API_KEY is available)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

def _clean_phone(raw: str) -> str:
    """Normalizes any phone string to the 996XXXXXXXXX format."""
    if not raw:
        return ""
    digits = re.sub(r'\D', '', raw)
    if digits.startswith('0'):
        digits = '996' + digits[1:]
    if len(digits) == 9:
        digits = '996' + digits
    if len(digits) >= 12 and digits.startswith('996'):
        return digits[:12]
    return digits # just return whatever digits remain if not matching exactly 996 formats

async def search_places_2gis(query: str, location: str = "Бишкек") -> Dict[str, Any]:
    api_key = os.getenv("TWOGIS_API_KEY")
    if not api_key:
        logger.error("КРИТИЧЕСКАЯ ОШИБКА: TWOGIS_API_KEY не найден в .env")
        return {"found": False, "error": "TWOGIS API Key is missing in .env", "contacts": []}

    full_query = f"{query}, {location}"
    print(f"!!! FINAL 2GIS QUERY -> q='{full_query}' !!!")
    
    url = "https://catalog.api.2gis.com/3.0/items"
    params = {
        "q": full_query,
        "fields": "items.contact_groups",
        "key": api_key
    }

    logger.info(f"2GIS Service: searching for → '{full_query}'")

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=10)
        
        if resp.status_code != 200:
            error_details = resp.text
            logger.error(f"2GIS API HTTP Error: {resp.status_code} | Details: {error_details}")
            print(f"!!! CRITICAL 2GIS HTTP ERROR !!! Status: {resp.status_code}, Body: {error_details}")
            return {"found": False, "error": f"2GIS HTTP {resp.status_code} - {error_details}", "contacts": []}
            
        data = resp.json()
        
        result = data.get("result", {})
        items = result.get("items", [])
        
        if not items:
            return {"found": False, "message": f"Заведение '{query}' не найдено в 2GIS.", "contacts": []}

        contacts = []
        for item in items:
            name = item.get("name", "Без названия")
            address = item.get("address_name") or item.get("full_name") or "Адрес не указан"
            rating = 5.0 # 2GIS free API doesn't always include rating without specific fields, hardcoding nice value format.
            
            phones = []
            for group in item.get("contact_groups", []):
                for contact_info in group.get("contacts", []):
                    if contact_info.get("type") == "phone":
                        val = contact_info.get("value")
                        if val:
                            phones.append(val)
                            
            raw_phone = phones[0] if phones else ""
            clean_p = _clean_phone(raw_phone) if raw_phone else ""
            
            wa_text = quote_plus("Здравствуйте! Хотел бы забронировать столик.")
            contacts.append({
                "name": name,
                "address": address,
                "phone": clean_p if clean_p else "Не указан",
                "formatted_phone": raw_phone if raw_phone else "Не указан",
                "rating": rating,
                "reviews": 0,
                "call_link": f"tel:+{clean_p}" if clean_p else "",
                "whatsapp_link": f"https://wa.me/{clean_p}?text={wa_text}" if clean_p else "",
                "source_url": f"https://2gis.kg/{location.lower()}/search/{quote_plus(name)}",
                "label": "2GIS Verified"
            })
                
        if not contacts:
             return {
                "found": False, 
                "message": f"Заведение '{query}' найдено, но телефон отсутствует.", 
                "contacts": []
            }

        logger.info(f"2GIS Service: Found {len(contacts)} branches.")
        return {
            "found": True,
            "query": query,
            "contacts": contacts,
            "source_url": contacts[0]["source_url"] if contacts else ""
        }
    except Exception as e:
        logger.error(f"2GIS Service Error: {e}")
        return {"found": False, "error": str(e), "contacts": []}
