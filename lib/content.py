"""Load non-recipe YAML content (food table, meal plan, checklists)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DATA = Path(__file__).resolve().parent.parent / "data"

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


def _load(name: str) -> Any:
    path = DATA / name
    if not path.exists() and name == "food_reference.yaml":
        alt = DATA / "food_recipe.yaml"
        if alt.exists():
            path = alt
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_food_reference() -> list[dict]:
    """Load the raw food reference hierarchy from data/food_reference.yaml."""
    return _load("food_reference.yaml")


def get_all_food_items(data: list[dict] | None = None) -> list[dict]:
    """Return a flat list of all food items with group, subgroup, status, attributes, and notes.

    Each item has:
        - name: str
        - group: str
        - subgroup: str
        - status: 'safer' | 'caution' | 'avoid'
        - attributes: list[str]
        - notes: str
    """
    if data is None:
        data = load_food_reference()

    items: list[dict] = []
    for g in data:
        group_name = g.get("group", "")
        for sg in g.get("subgroups", []):
            subgroup_name = sg.get("name", "")
            for item in sg.get("items", []):
                items.append(
                    {
                        "name": item.get("name", ""),
                        "group": group_name,
                        "subgroup": subgroup_name,
                        "status": item.get("status", "safer").lower(),
                        "attributes": list(item.get("attributes", [])),
                        "notes": item.get("notes", ""),
                    }
                )
            for status in ("safer", "caution", "avoid"):
                for entry in sg.get(status, []):
                    if isinstance(entry, dict):
                        items.append(
                            {
                                "name": entry.get("name", ""),
                                "group": group_name,
                                "subgroup": subgroup_name,
                                "status": status,
                                "attributes": list(entry.get("attributes", [])),
                                "notes": entry.get("notes", ""),
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


def format_food_item(it: dict, include_attributes: bool = False) -> str:
    """Format an ingredient into a string with optional attributes and notes."""
    name = it["name"]
    parts: list[str] = [name]
    if include_attributes and it.get("attributes"):
        parts.append(f"[{', '.join(it['attributes'])}]")
    if it.get("notes"):
        parts.append(f"({it['notes']})")
    return " ".join(parts)


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
            searchable = (
                f"{it['name']} {it['group']} {it['subgroup']} "
                f"{' '.join(it.get('attributes', []))} {it.get('notes', '')}"
            ).lower()
            if q not in searchable:
                continue
        filtered.append(it)
    return filtered


def get_food_reference_table_rows(
    items: list[dict] | None = None,
    include_attributes: bool = False,
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
        grouped[key][status].append(format_food_item(it, include_attributes=include_attributes))

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


def load_meal_plan() -> list[dict]:
    return _load("meal_plan.yaml")


def load_checklists() -> dict:
    return _load("checklists.yaml")
