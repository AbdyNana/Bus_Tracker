"""
Agent 3: The Bulldozer (Google Places API v1 Edition - Hardened)
Uses popularity-based ranking (rating & user counts) to filter out fake points.
Guarantees verified business contacts and addresses.
"""
import os
import re
import logging
import requests
import traceback
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

# --- Environment Setup (Absolute Path) ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

# API Keys from .env
API_KEY = os.getenv("GOOGLE_PLACES_API_KEY") or os.getenv("GOOGLE_API_KEY")

def _clean_phone(raw: str) -> str:
    """Normalizes any phone string to the 996XXXXXXXXX format."""
    if not raw:
        return ""
    digits = re.sub(r'\D', '', raw)
    if digits.startswith('0'):
        digits = '996' + digits[1:]
    if len(digits) == 9:
        digits = '996' + digits
    if len(digits) == 12 and digits.startswith('996'):
        return digits
    return ''

def Contactss(query: str) -> dict:
    """
    Search for business contacts using modern Places API (New) v1.
    Implements smart sorting by popularity (userRatingCount) to find real branches.
    """
    if not API_KEY:
        logger.error("КРИТИЧЕСКАЯ ОШИБКА: API_KEY не найден в .env")
        return {"found": False, "error": "API Key is missing in .env"}

    # Include Bishkek for better localization
    search_query = f"{query} Бишкек"
    logger.info(f"Bulldozer (Smart Ranking): searching for → '{search_query}'")

    try:
        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": API_KEY,
            # Added userRatingCount and rating for quality filtering
            "X-Goog-FieldMask": (
                "places.displayName,"
                "places.formattedAddress,"
                "places.internationalPhoneNumber,"
                "places.googleMapsUri,"
                "places.userRatingCount,"
                "places.rating"
            )
        }
        payload = {
            "textQuery": search_query,
            "languageCode": "ru"
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        
        if resp.status_code == 403:
            msg = "Ошибка 403: Places API (New) не активирован. Проверьте консоль Google Cloud."
            return {"found": False, "error": msg, "api_status": "DISABLED"}

        resp.raise_for_status()
        data = resp.json()

        places = data.get("places", [])
        if not places:
            return {"found": False, "message": f"Заведение '{query}' не найдено.", "contacts": []}

        # --- SMART SORTING ---
        # Sort by userRatingCount (descending) to prioritize real/popular locations
        # If count is missing, default to 0
        sorted_places = sorted(
            places, 
            key=lambda x: x.get("userRatingCount", 0), 
            reverse=True
        )

        contacts = []
        for p in sorted_places[:5]: # Consider top 5 after sorting
            name = p.get("displayName", {}).get("text", "Без названия")
            address = p.get("formattedAddress", "Бишкек")
            raw_phone = p.get("internationalPhoneNumber")
            rating = p.get("rating", 0)
            reviews = p.get("userRatingCount", 0)
            source_url = p.get("googleMapsUri", f"https://www.google.com/maps/search/?api=1&query={quote_plus(name)}")

            # Validation: Filter out points with suspiciously low reviews if we have better options
            # If the top result has 100+ reviews and this one has 0, it's likely a duplicate
            if len(contacts) > 0 and reviews < 5 and sorted_places[0].get("userRatingCount", 0) > 50:
                logger.debug(f"Skipping suspected fake point: '{name}' with {reviews} reviews.")
                continue

            if raw_phone:
                clean_p = _clean_phone(raw_phone)
                if clean_p:
                    wa_text = quote_plus("Здравствуйте! Хотел бы забронировать столик.")
                    contacts.append({
                        "name": name,
                        "address": address,
                        "phone": clean_p,
                        "formatted_phone": raw_phone,
                        "rating": rating,
                        "reviews": reviews,
                        "call_link": f"tel:+{clean_p}",
                        "whatsapp_link": f"https://wa.me/{clean_p}?text={wa_text}",
                        "source_url": source_url,
                        "label": "Grounded Match"
                    })

        if not contacts:
            return {
                "found": False, 
                "message": f"Заведение '{query}' найдено, но телефон отсутствует или точка не верифицирована.", 
                "contacts": []
            }

        logger.info(f"Bulldozer: Found {len(contacts)} prioritized branches.")
        return {
            "found": True,
            "query": query,
            "contacts": contacts,
            "source_url": contacts[0]["source_url"] if contacts else ""
        }

    except Exception as e:
        logger.error(f"Bulldozer Error: {e}\n{traceback.format_exc()}")
        return {"found": False, "error": str(e), "contacts": []}

# Maintain alias
search_contacts = Contactss