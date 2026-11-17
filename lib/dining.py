"""Campus Dining integration with Tech Dining Nutrislice menu API and histamine risk analysis."""
from __future__ import annotations

import gzip
import json
import re
import urllib.parse
import urllib.request
from typing import Any

# High-risk / AVOID triggers based on SIGHI food compatibility guidelines
AVOID_PATTERNS = [
    (r"\b(bacon|pepperoni|salami|prosciutto|ham|sausage|pastrami|cured|smoked|hot\s*dog|frankfurter|chorizo)\b", "Cured or smoked meat"),
    (r"\b(parmesan|cheddar|romano|blue\s*cheese|bleu|feta|swiss|provolone|gouda|asiago|brie|camembert|aged\s*cheese)\b", "Aged cheese (high histamine)"),
    (r"\b(balsamic|vinegar|vinaigrette|pickles?|pickled|sauerkraut|kimchi|relish|olives?)\b", "Vinegar / fermented food"),
    (r"\b(soy\s*sauce|tamari|miso|teriyaki|worcestershire|shoyu)\b", "Fermented soy / condiment"),
    (r"\b(tomato(es)?|marinara|ketchup|salsa|pizza\s*sauce|tomato\s*paste|sundried\s*tomato)\b", "Tomato (histamine liberator / high histamine)"),
    (r"\b(spinach|eggplant|aubergine|avocado|guacamole)\b", "High-histamine produce"),
    (r"\b(shellfish|shrimp|crab|lobster|tuna|clam|mussel|anchov(y|ies)|calamari|squid|oyster)\b", "Shellfish or canned/preserved fish"),
    (r"\b(chocolate|cocoa|cacao|fudge)\b", "Chocolate / cacao"),
    (r"\b(yeast\s*extract|autolyzed|hydrolyzed\s*protein|monosodium\s*glutamate|\bmsg\b)\b", "Yeast extract / flavor enhancer"),
]

# Moderate-risk / CAUTION triggers based on SIGHI food compatibility guidelines
CAUTION_PATTERNS = [
    (r"\b(mushroom|shiitake|portobell?o|cremini|button\s*mushroom)\b", "Mushrooms (moderate histamine)"),
    (r"\b(bbq|barbecue)\b", "BBQ sauce / slow-cooked"),
    (r"\b(citrus|lemon|lime|orange|grapefruit|tangerine|clementine)\b", "Citrus (histamine liberator)"),
    (r"\b(strawberr(y|ies)|pineapple|banana|bananas|papaya|kiwi)\b", "Histamine-liberating fruit"),
    (r"\b(egg\s*white|mayonnaise|mayo|aioli)\b", "Egg white / mayonnaise"),
    (r"\b(peanut|almond|walnut|cashew|pecan|pistachio|sunflower\s*seed)\b", "Nuts / seeds"),
    (r"\b(beans?|lentils?|chickpeas?|garbanzo|hummus|edamame|tofu|soy\s*milk)\b", "Legumes / pulses / soy"),
    (r"\b(sour\s*cream|yogurt|buttermilk|kefir)\b", "Cultured dairy"),
    (r"\b(coffee|espresso|caffeine|black\s*tea|green\s*tea|matcha)\b", "Caffeinated beverage / tea"),
    (r"\b(cracked\s*wheat|bread|bun|roll|crust|bagel|tortilla|pita)\b", "Commercial yeast-baked bread / gluten"),
]


def parse_nutrislice_url(url_or_text: str) -> dict[str, str]:
    """Parse a Nutrislice URL to extract district, school, menu_type, and date.

    Example URL:
        https://techdining.nutrislice.com/menu/brittain/lunch/2026-11-17
    """
    clean_url = url_or_text.strip()

    # Extract district (e.g. techdining from techdining.nutrislice.com)
    district_match = re.search(r"https?://([^.]+)\.(?:api\.)?nutrislice\.com", clean_url)
    district = district_match.group(1) if district_match else "techdining"

    # Match /menu/<school>/<menu-type>/<YYYY-MM-DD>
    full_match = re.search(r"/menu/([^/]+)/([^/]+)/(\d{4}-\d{2}-\d{2})", clean_url)
    if full_match:
        return {
            "district": district,
            "school": full_match.group(1),
            "menu_type": full_match.group(2),
            "date": full_match.group(3),
        }

    # Match /menu/<school>/<menu-type> (without date)
    partial_match = re.search(r"/menu/([^/]+)/([^/]+)", clean_url)
    if partial_match:
        return {
            "district": district,
            "school": partial_match.group(1),
            "menu_type": partial_match.group(2),
            "date": "2026-11-17",
        }

    # Fallback to default
    return {
        "district": "techdining",
        "school": "brittain",
        "menu_type": "lunch",
        "date": "2026-11-17",
    }


def analyze_histamine_risk(name: str, ingredients: str = "", description: str = "") -> dict[str, Any]:
    """Evaluate a dish and its ingredients for histamine intolerance risk."""
    haystack = f"{name} {description} {ingredients}".lower()

    avoid_reasons = []
    for pat, label in AVOID_PATTERNS:
        match = re.search(pat, haystack, re.IGNORECASE)
        if match:
            # Avoid duplicate labels
            reason = f"{match.group(0).title()} ({label})"
            if reason not in avoid_reasons:
                avoid_reasons.append(reason)

    if avoid_reasons:
        return {
            "level": "avoid",
            "badge": "🔴 AVOID",
            "score": 3,
            "reasons": avoid_reasons,
        }

    caution_reasons = []
    for pat, label in CAUTION_PATTERNS:
        match = re.search(pat, haystack, re.IGNORECASE)
        if match:
            reason = f"{match.group(0).title()} ({label})"
            if reason not in caution_reasons:
                caution_reasons.append(reason)

    if caution_reasons:
        return {
            "level": "caution",
            "badge": "🟡 CAUTION",
            "score": 2,
            "reasons": caution_reasons,
        }

    return {
        "level": "safer",
        "badge": "🟢 SAFER",
        "score": 1,
        "reasons": ["Fresh, simple preparation without common high-histamine triggers detected."],
    }


def fetch_nutrislice_menu(
    school: str = "brittain",
    menu_type: str = "lunch",
    date_str: str = "2026-11-17",
    district: str = "techdining",
    timeout_sec: int = 10,
) -> tuple[list[dict], str | None]:
    """Fetch and parse daily menu items from Nutrislice API.

    Returns (dishes, error_message).
    """
    parts = date_str.split("-")
    if len(parts) != 3:
        return [], f"Invalid date format '{date_str}', expected YYYY-MM-DD"
    year, month, day = parts

    api_url = (
        f"https://{district}.api.nutrislice.com/menu/api/weeks/school/"
        f"{school}/menu-type/{menu_type}/{year}/{month}/{day}/?format=json"
    )

    req = urllib.request.Request(
        api_url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read()
            if raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            payload = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        return [], f"Error connecting to Nutrislice ({exc})"

    days = payload.get("days", [])
    target_day = None
    for d in days:
        if d.get("date") == date_str:
            target_day = d
            break

    if not target_day:
        return [], f"No menu data found for date {date_str} at {school} ({menu_type})."

    menu_items = target_day.get("menu_items", [])
    current_station = "General"
    dishes = []

    for it in menu_items:
        if it.get("is_section_title"):
            title_text = it.get("text") or (it.get("food") or {}).get("name")
            if title_text:
                current_station = title_text.strip()
            continue

        food = it.get("food")
        if not food:
            continue

        dish_name = food.get("name") or it.get("text")
        if not dish_name:
            continue

        ingredients = food.get("ingredients") or ""
        description = food.get("description") or ""
        calories = (food.get("rounded_nutrition_info") or {}).get("calories")

        icons_raw = food.get("icons") or []
        icons = [i if isinstance(i, str) else i.get("name", "") for i in icons_raw if i]

        risk_eval = analyze_histamine_risk(dish_name, ingredients, description)

        dishes.append(
            {
                "name": dish_name,
                "station": current_station,
                "ingredients": ingredients.strip(),
                "description": description.strip(),
                "calories": calories,
                "icons": icons,
                "risk": risk_eval["level"],
                "badge": risk_eval["badge"],
                "reasons": risk_eval["reasons"],
            }
        )

    return dishes, None
