"""Display categories are independent of detection and recording preferences."""
import re

CATEGORIES = {"motion": "Motion", "person": "Person", "animal": "Animal", "vehicle": "Car / vehicle"}


def alert_category(entry):
    category = str(entry.get("category", "")).lower()
    if category in CATEGORIES:
        return category
    words = set(re.findall(r"[a-z]+", str(entry.get("label", "")).lower()))
    if words & {"person", "human", "people"}:
        return "person"
    if words & {"car", "vehicle", "truck", "bus", "motorcycle", "bicycle"}:
        return "vehicle"
    if words & {"animal", "dog", "cat", "bird", "horse", "sheep", "cow", "bear", "elephant"}:
        return "animal"
    return "motion"


def visible_alert(entry, selected):
    return alert_category(entry) in selected
