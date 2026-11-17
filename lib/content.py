"""Load non-recipe YAML content (food table, meal plan, checklists)."""
from __future__ import annotations

from dataclasses import dataclass, field
import functools
import html
from pathlib import Path
from typing import Any
import re
import urllib.parse

import yaml

DATA = Path(__file__).resolve().parent.parent / "data"

KG_TO_LBS = 2.20462262185
LBS_TO_KG = 0.45359237

# Accessible and harmonious color palettes for each Food Group
FOOD_GROUP_COLORS: dict[str, dict[str, str]] = {
    "Meat and fish": {
        "bg": "#e0e7ff",      # Deep cool indigo (strong contrast with CAUTION yellow)
        "border": "#a5b4fc",
        "text": "#312e81",
    },
    "Eggs and dairy": {
        "bg": "#fef9c3",      # Soft amber gold
        "border": "#fef08a",
        "text": "#854d0e",
    },
    "Vegetables": {
        "bg": "#dcfce7",      # Garden green
        "border": "#bbf7d0",
        "text": "#166534",
    },
    "Fruit": {
        "bg": "#f3e8ff",      # Berry violet
        "border": "#e9d5ff",
        "text": "#6b21a8",
    },
    "Grains and starches": {
        "bg": "#ffedd5",      # Warm wheat peach
        "border": "#fed7aa",
        "text": "#9a3412",
    },
    "Drinks": {
        "bg": "#cffafe",      # Crisp ice cyan / aqua
        "border": "#67e8f9",
        "text": "#155e75",
    },
    "Flavor and extras": {
        "bg": "#ccfbf1",      # Sage teal
        "border": "#99f6e4",
        "text": "#115e59",
    },
}

# Standardized accessible color scheme for tolerance tags (WCAG AAA Conformance)
STATUS_COLORS: dict[str, dict[str, str]] = {
    "safer": {
        "bg": "#dcfce7",
        "border": "#16a34a",
        "text": "#14532d",
        "label": "SAFER",
        "emoji": "🟢",
        "aria_label": "Tolerance status: SAFER. Fresh, low-histamine foods usually well tolerated.",
    },
    "caution": {
        "bg": "#fef3c7",
        "border": "#d97706",
        "text": "#78350f",
        "label": "CAUTION",
        "emoji": "🟡",
        "aria_label": "Tolerance status: CAUTION. Moderate histamine or histamine liberators; test slowly.",
    },
    "avoid": {
        "bg": "#fee2e2",
        "border": "#dc2626",
        "text": "#7f1d1d",
        "label": "AVOID",
        "emoji": "🔴",
        "aria_label": "Tolerance status: AVOID. High histamine, aged, fermented, or cured foods.",
    },
}


def cost_per_kg_to_cost_per_lb(cost_per_kg: float | None, precision: int = 2) -> float | None:
    """Convert cost per kilogram ($/kg) to cost per pound ($/lb).

    Since 1 kg = 2.20462262185 lbs:
        Cost per lb = (Cost per kg) / 2.20462262185
    """
    if cost_per_kg is None:
        return None
    cost = float(cost_per_kg) / KG_TO_LBS
    return round(cost, precision)


def convert_cost_kg_to_lbs(cost_per_kg: float | None, precision: int = 2) -> float | None:
    """Alias for cost_per_kg_to_cost_per_lb."""
    return cost_per_kg_to_cost_per_lb(cost_per_kg, precision)


def cost_per_lb_to_cost_per_kg(cost_per_lb: float | None, precision: int = 2) -> float | None:
    """Convert cost per pound ($/lb) to cost per kilogram ($/kg)."""
    if cost_per_lb is None:
        return None
    cost = float(cost_per_lb) * KG_TO_LBS
    return round(cost, precision)


@dataclass
class FoodItem:
    """Structured representation of a food item with pricing and safety attributes."""

    name: str
    group: str
    subgroup: str
    status: str
    attributes: list[str] = field(default_factory=list)
    notes: str = ""
    cost_per_kg: float | None = None

    @property
    def cost_per_lb(self) -> float | None:
        """Helper property to convert cost per kg to cost per lb."""
        return cost_per_kg_to_cost_per_lb(self.cost_per_kg)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "group": self.group,
            "subgroup": self.subgroup,
            "status": self.status,
            "attributes": self.attributes,
            "notes": self.notes,
            "cost_per_kg": self.cost_per_kg,
            "cost_per_lb": self.cost_per_lb,
        }


ATTRIBUTE_TAXONOMY: dict[str, list[str]] = {
    "Starches & Veggie Types": [
        "starches",
        "root veggies",
        "leafy green",
        "cruciferous",
        "allium",
        "squash",
        "nightshades",
        "legumes",
        "fungi",
        "herbal",
    ],
    "Fruits": [
        "berry",
        "citrus",
        "melon",
        "tropical",
        "pome fruit",
        "stone fruit",
    ],
    "Flavor Profiles": [
        "savory",
        "tart",
        "sweet",
        "earthy",
        "peppery",
        "bitter",
        "aromatic",
        "pungent",
        "mild",
    ],
    "Proteins & Dairy": [
        "poultry",
        "red meat",
        "fish",
        "shellfish",
        "organ meat",
        "eggs",
        "dairy",
    ],
    "Grains, Nuts & Seeds": [
        "grain",
        "nut",
        "seed",
        "flour",
        "gluten-free",
        "gluten",
    ],
    "Fats, Seasonings & Extras": [
        "fat",
        "oil",
        "spice",
        "sweetener",
    ],
    "Histamine & Reactions": [
        "high-histamine",
        "histamine-liberator",
        "DAO-blocker",
        "fermented",
        "cured",
        "caffeinated",
    ],
}


@functools.lru_cache(maxsize=16)
def _load(name: str) -> Any:
    path = DATA / name
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_food_reference() -> list[dict]:
    """Load the canonical food reference hierarchy from data/food_reference.yaml."""
    return _load("food_reference.yaml")


# Backward-compatible alias
load_food_recipe = load_food_reference


def _parse_cost(val: Any) -> float | None:
    if val is None:
        return None
    try:
        return round(float(val), 2)
    except (ValueError, TypeError):
        return None


def get_all_food_items(data: list[dict] | None = None) -> list[dict]:
    """Return a flat list of all food items with group, subgroup, status, attributes, notes, cost_per_kg, and cost_per_lb.

    Each item has:
        - name: str
        - group: str
        - subgroup: str
        - status: 'safer' | 'caution' | 'avoid'
        - attributes: list[str]
        - notes: str
        - cost_per_kg: float | None
        - cost_per_lb: float | None
    """
    if data is None:
        data = load_food_reference()

    items: list[dict] = []
    for g in data:
        group_name = g.get("group", "")
        for sg in g.get("subgroups", []):
            subgroup_name = sg.get("name", "")
            for item in sg.get("items", []):
                cost_kg = _parse_cost(item.get("cost_per_kg"))
                items.append(
                    {
                        "name": item.get("name", ""),
                        "group": group_name,
                        "subgroup": subgroup_name,
                        "status": item.get("status", "safer").lower(),
                        "attributes": list(item.get("attributes", [])),
                        "notes": item.get("notes", ""),
                        "cost_per_kg": cost_kg,
                        "cost_per_lb": cost_per_kg_to_cost_per_lb(cost_kg),
                    }
                )
            for status in ("safer", "caution", "avoid"):
                for entry in sg.get(status, []):
                    if isinstance(entry, dict):
                        cost_kg = _parse_cost(entry.get("cost_per_kg"))
                        items.append(
                            {
                                "name": entry.get("name", ""),
                                "group": group_name,
                                "subgroup": subgroup_name,
                                "status": status,
                                "attributes": list(entry.get("attributes", [])),
                                "notes": entry.get("notes", ""),
                                "cost_per_kg": cost_kg,
                                "cost_per_lb": cost_per_kg_to_cost_per_lb(cost_kg),
                            }
                        )
                    elif isinstance(entry, str):
                        items.append(
                            {
                                "name": entry,
                                "group": group_name,
                                "subgroup": subgroup_name,
                                "status": status,
                                "attributes": [],
                                "notes": "",
                                "cost_per_kg": None,
                                "cost_per_lb": None,
                            }
                        )
    return items


def get_food_groups(data: list[dict] | None = None) -> list[str]:
    """Return unique food groups in original declaration order."""
    if data is None:
        data = load_food_reference()
    groups: list[str] = []
    for g in data:
        name = g.get("group", "")
        if name and name not in groups:
            groups.append(name)
    return groups


def get_food_subgroups(group: str | None = None, data: list[dict] | None = None) -> list[str]:
    """Return subgroup names, optionally filtered by food group."""
    items = get_all_food_items(data)
    subgroups: list[str] = []
    for it in items:
        if group is None or group == "All" or it["group"] == group:
            sg = it["subgroup"]
            if sg and sg not in subgroups:
                subgroups.append(sg)
    return subgroups


def get_attribute_categories() -> list[str]:
    """Return high-level attribute category names."""
    return list(ATTRIBUTE_TAXONOMY.keys())


def get_attributes_for_category(category: str | None = None) -> list[str]:
    """Return attribute tags for a given category, or all curated attributes."""
    if not category or category == "All Categories":
        all_attrs: set[str] = set()
        for cat_list in ATTRIBUTE_TAXONOMY.values():
            all_attrs.update(cat_list)
        return sorted(all_attrs)
    return ATTRIBUTE_TAXONOMY.get(category, [])


def get_all_attributes(data: list[dict] | None = None) -> list[str]:
    """Return a sorted list of all unique attribute tags across all foods."""
    items = get_all_food_items(data)
    attrs: set[str] = set()
    for it in items:
        attrs.update(it.get("attributes", []))
    return sorted(attrs)


def format_food_item(it: dict, include_attributes: bool = False, include_cost: bool = False) -> str:
    """Format an ingredient into a string with optional attributes, cost, and notes."""
    name = it["name"]
    parts: list[str] = [name]
    if include_cost and it.get("cost_per_kg") is not None:
        cost_lb = it.get("cost_per_lb")
        parts.append(f"(${it['cost_per_kg']:.2f}/kg, ${cost_lb:.2f}/lb)" if cost_lb else f"(${it['cost_per_kg']:.2f}/kg)")
    if include_attributes and it.get("attributes"):
        parts.append(f"[{', '.join(it['attributes'])}]")
    if it.get("notes"):
        parts.append(f"({it['notes']})")
    return " ".join(parts)


def render_food_box(it: dict) -> str:
    """Render a single food as an individually boxed, clickable badge colored by food group."""
    group = it.get("group", "")
    colors = FOOD_GROUP_COLORS.get(
        group, {"bg": "#f1f5f9", "border": "#cbd5e1", "text": "#1e293b"}
    )
    name = it["name"]
    notes = it.get("notes", "")
    safe_name = html.escape(name)
    encoded_name = urllib.parse.quote(name)
    notes_html = (
        f' <span style="font-size: 0.8em; opacity: 0.9; font-weight: normal;">({html.escape(notes)})</span>'
        if notes
        else ""
    )

    return (
        f'<a href="?food={encoded_name}&tab=dir" target="_self" '
        f'aria-label="View {safe_name} details and attributes in Ingredient Directory" '
        f'title="Click to view {safe_name} in Ingredient Directory" '
        f'style="display: inline-block; padding: 4px 10px; margin: 3px 4px 3px 0; '
        f'background-color: {colors["bg"]}; border: 1px solid {colors["border"]}; '
        f'color: {colors["text"]}; border-radius: 6px; font-size: 0.88rem; font-weight: 600; '
        f'text-decoration: underline; text-decoration-color: {colors["border"]}; box-shadow: 0 1px 2px rgba(0,0,0,0.04); '
        f'line-height: 1.35;">'
        f'{safe_name}{notes_html}</a>'
    )


def get_food_reference_html_table(items: list[dict] | None = None) -> str:
    """Generate an accessible HTML reference table where foods are individually boxed and colored by food group.

    Headers feature colored SAFER, CAUTION, and AVOID badges. Clicking any food box redirects to the ingredient category.
    """
    if items is None:
        items = get_all_food_items()

    grouped: dict[tuple[str, str], dict[str, list[dict]]] = {}
    for it in items:
        key = (it["group"], it["subgroup"])
        if key not in grouped:
            grouped[key] = {"safer": [], "caution": [], "avoid": []}
        st = it["status"] if it["status"] in ("safer", "caution", "avoid") else "safer"
        grouped[key][st].append(it)

    header_html = (
        '<div style="overflow-x: auto; width: 100%; border-radius: 8px; border: 1px solid #cbd5e1; margin: 12px 0 20px 0;">'
        '<table role="table" aria-label="Georgia Tech Food Compatibility Reference Table" '
        'style="width: 100%; border-collapse: collapse; font-family: inherit; font-size: 0.92rem; background: #ffffff;">'
        '<thead>'
        '<tr style="background: #f8fafc; border-bottom: 2px solid #cbd5e1; text-align: left;">'
        '<th scope="col" style="padding: 12px 14px; font-weight: 700; width: 14%; color: #0f172a;">Food group</th>'
        '<th scope="col" style="padding: 12px 14px; font-weight: 700; width: 18%; color: #0f172a;">Subgroup</th>'
        '<th scope="col" style="padding: 12px 14px; font-weight: 700; width: 28%; color: #0f172a;">'
        '<span role="status" aria-label="Tolerance level: SAFER" '
        'style="background-color: #dcfce7; border: 1px solid #16a34a; color: #14532d; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 0.82rem; letter-spacing: 0.04em;">🟢 SAFER</span> '
        '<span style="font-weight: 500; font-size: 0.82rem; color: #475569;">(usually well tolerated)</span></th>'
        '<th scope="col" style="padding: 12px 14px; font-weight: 700; width: 20%; color: #0f172a;">'
        '<span role="status" aria-label="Tolerance level: CAUTION" '
        'style="background-color: #fef3c7; border: 1px solid #d97706; color: #78350f; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 0.82rem; letter-spacing: 0.04em;">🟡 CAUTION</span> '
        '<span style="font-weight: 500; font-size: 0.82rem; color: #475569;">(test slowly)</span></th>'
        '<th scope="col" style="padding: 12px 14px; font-weight: 700; width: 20%; color: #0f172a;">'
        '<span role="status" aria-label="Tolerance level: AVOID" '
        'style="background-color: #fee2e2; border: 1px solid #dc2626; color: #7f1d1d; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 0.82rem; letter-spacing: 0.04em;">🔴 AVOID</span> '
        '<span style="font-weight: 500; font-size: 0.82rem; color: #475569;">(problematic)</span></th>'
        '</tr>'
        '</thead>'
        '<tbody>'
    )

    rows_html = []
    for idx, ((grp, subg), buckets) in enumerate(grouped.items()):
        grp_colors = FOOD_GROUP_COLORS.get(grp, {"bg": "#f1f5f9", "border": "#cbd5e1", "text": "#334155"})
        row_bg = "#ffffff" if idx % 2 == 0 else "#fafbfc"

        safer_content = " ".join(render_food_box(it) for it in buckets["safer"]) if buckets["safer"] else '<span style="color: #94a3b8; font-weight: 300;">—</span>'
        caution_content = " ".join(render_food_box(it) for it in buckets["caution"]) if buckets["caution"] else '<span style="color: #94a3b8; font-weight: 300;">—</span>'
        avoid_content = " ".join(render_food_box(it) for it in buckets["avoid"]) if buckets["avoid"] else '<span style="color: #94a3b8; font-weight: 300;">—</span>'

        grp_badge = (
            f'<span style="background-color: {grp_colors["bg"]}; border: 1px solid {grp_colors["border"]}; '
            f'color: {grp_colors["text"]}; padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 0.82rem; display: inline-block;">'
            f'{html.escape(grp)}</span>'
        )

        rows_html.append(
            f'<tr style="background: {row_bg}; border-bottom: 1px solid #edf2f7; vertical-align: top;">'
            f'<td style="padding: 12px 14px; font-weight: 500;">{grp_badge}</td>'
            f'<td style="padding: 12px 14px; font-weight: 600; color: #1e293b;">{html.escape(subg)}</td>'
            f'<td style="padding: 10px 14px; line-height: 1.6;">{safer_content}</td>'
            f'<td style="padding: 10px 14px; line-height: 1.6;">{caution_content}</td>'
            f'<td style="padding: 10px 14px; line-height: 1.6;">{avoid_content}</td>'
            f'</tr>'
        )

    footer_html = '</tbody></table></div>'
    return header_html + "".join(rows_html) + footer_html


def filter_food_items(
    items: list[dict] | None = None,
    group_filter: str | None = None,
    subgroup_filter: str | None = None,
    status_filters: list[str] | None = None,
    attribute_filters: list[str] | None = None,
    query: str = "",
) -> list[dict]:
    """Filter food items by group, subgroup, status, attribute tags, and text search."""
    if items is None:
        items = get_all_food_items()
    q = query.strip().lower()
    attr_set = {a.lower() for a in (attribute_filters or [])}
    allowed_statuses = set(status_filters) if status_filters else None

    filtered: list[dict] = []
    for it in items:
        if group_filter and group_filter != "All" and it["group"] != group_filter:
            continue
        if subgroup_filter and subgroup_filter != "All" and it["subgroup"] != subgroup_filter:
            continue
        if allowed_statuses is not None and it["status"] not in allowed_statuses:
            continue
        if attr_set:
            it_attrs = {a.lower() for a in it.get("attributes", [])}
            if not attr_set.issubset(it_attrs):
                continue
        if q:
            cost_str = f"{it.get('cost_per_kg', '')} {it.get('cost_per_lb', '')}"
            searchable = (
                f"{it['name']} {it['group']} {it['subgroup']} "
                f"{' '.join(it.get('attributes', []))} {it.get('notes', '')} {cost_str}"
            ).lower()
            if q not in searchable:
                continue
        filtered.append(it)
    return filtered


def get_food_reference_table_rows(
    items: list[dict] | None = None,
    include_attributes: bool = False,
    include_cost: bool = False,
) -> list[dict]:
    """Return grouped table rows formatted for Streamlit table/dataframe display."""
    if items is None:
        items = get_all_food_items()

    grouped: dict[tuple[str, str], dict[str, list[str]]] = {}
    for it in items:
        key = (it["group"], it["subgroup"])
        if key not in grouped:
            grouped[key] = {"safer": [], "caution": [], "avoid": []}
        status = it["status"] if it["status"] in ("safer", "caution", "avoid") else "safer"
        grouped[key][status].append(
            format_food_item(it, include_attributes=include_attributes, include_cost=include_cost)
        )

    rows: list[dict] = []
    for (grp, subg), buckets in grouped.items():
        rows.append(
            {
                "Food group": grp,
                "Subgroup": subg,
                "SAFER (usually well tolerated)": ", ".join(buckets["safer"]) if buckets["safer"] else "—",
                "CAUTION (varies; test slowly)": ", ".join(buckets["caution"]) if buckets["caution"] else "—",
                "AVOID (commonly problematic)": ", ".join(buckets["avoid"]) if buckets["avoid"] else "—",
            }
        )
    return rows


def singularize(w: str) -> str:
    """Normalize simple English plurals for food ingredient matching."""
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith("oes") and len(w) > 4:
        return w[:-2]
    if w.endswith("s") and not w.endswith("ss") and len(w) > 2:
        return w[:-1]
    return w


def pluralize(w: str) -> str:
    """Pluralize simple English food names."""
    if w.endswith(("s", "x", "z", "ch", "sh", "o")):
        return w + "es"
    if w.endswith("y") and len(w) > 1 and w[-2].lower() not in "aeiou":
        return w[:-1] + "ies"
    return w + "s"


def match_ingredient_to_food(ing_str: str, foods: list[dict] | None = None) -> dict | None:
    """Match a recipe ingredient string to a canonical food reference item.

    Handles measurements, preparations (diced, sliced, ground), and pluralization.
    """
    if foods is None:
        foods = get_all_food_items()

    ing_lower = ing_str.lower()
    cleaned_ing = re.sub(
        r"[\d\./]+|\b(cup|cups|tbsp|tsp|clove|cloves|lb|lbs|oz|large|small|medium|fresh|plain|ground|diced|sliced|cubed|grated|squeezed|dry|cooked)\b",
        " ",
        ing_lower,
    )
    ing_words = set(re.findall(r"[a-z]+", cleaned_ing))
    ing_singles = {singularize(w) for w in ing_words}

    sorted_foods = sorted(foods, key=lambda f: len(f["name"]), reverse=True)
    best_match = None
    best_score = 0

    for f in sorted_foods:
        fname = f["name"].lower()
        clean_name = re.sub(r"\(.*?\)", "", fname).strip()
        f_words = set(re.findall(r"[a-z]+", clean_name))
        f_singles = {singularize(w) for w in f_words}
        if f_singles and f_singles.issubset(ing_singles):
            score = len(f_singles) * 10
            if score > best_score:
                best_score = score
                best_match = f

    if best_match:
        return best_match

    for f in sorted_foods:
        fname = f["name"].lower()
        clean_name = re.sub(r"\(.*?\)", "", fname).strip()
        f_words = set(re.findall(r"[a-z]+", clean_name))
        f_singles = {singularize(w) for w in f_words}
        if f_singles and f_singles.intersection(ing_singles):
            common = f_singles.intersection(ing_singles)
            meaningful = {w for w in common if w not in ("whole", "fresh", "raw", "plain", "extra", "virgin")}
            if meaningful:
                score = len(meaningful) * 5
                if score > best_score:
                    best_score = score
                    best_match = f

    return best_match


def get_foods_by_attributes(
    attributes: list[str],
    match_mode: str = "all",
    foods: list[dict] | None = None,
) -> list[dict]:
    """Return all food items matching a collection of attribute tags.

    match_mode='all' requires every attribute in `attributes` to be present (intersection).
    match_mode='any' requires at least one attribute to be present (union).
    """
    if foods is None:
        foods = get_all_food_items()
    if not attributes:
        return []
    target_set = {a.lower().strip() for a in attributes if a.strip()}
    if not target_set:
        return []

    result = []
    for it in foods:
        it_attrs = {a.lower().strip() for a in it.get("attributes", [])}
        if match_mode == "all":
            if target_set.issubset(it_attrs):
                result.append(it)
        else:
            if target_set & it_attrs:
                result.append(it)
    return result


def get_foods_by_attribute(attribute: str, foods: list[dict] | None = None) -> list[dict]:
    """Return all food items containing a specific attribute tag."""
    return get_foods_by_attributes([attribute], match_mode="all", foods=foods)


def load_meal_plan() -> list[dict]:
    return _load("meal_plan.yaml")


def load_checklists() -> dict:
    return _load("checklists.yaml")
