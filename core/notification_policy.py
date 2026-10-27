"""Outgoing delivery preferences, independent of incident creation and feed display."""
import re
import unicodedata

CATEGORY_LABELS = {"person": "People", "vehicle": "Cars / vehicles", "animal": "Animals", "motion": "Motion"}
_ALIASES = {
    "person": {"person", "persons", "people", "human", "intruder", "om", "persoana", "persoane"},
    "vehicle": {"vehicle", "vehicles", "car", "truck", "bus", "motorcycle", "bicycle", "van", "masina", "auto", "vehicul"},
    "animal": {"animal", "animals", "dog", "cat", "bird", "chicken", "horse", "sheep", "cow", "bear", "elephant", "zebra", "giraffe", "wildlife", "caine", "pisica", "gaina", "pasare"},
    "motion": {"motion", "miscare"},
}


def _words(value):
    value = unicodedata.normalize("NFKD", str(value or "").casefold())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return set(re.findall(r"[a-z]+", value))


def notification_category(entry):
    # Structured detection data is authoritative. Never infer an object from
    # camera names, descriptions, filenames or trigger prose.
    value = entry.get("category") or entry.get("label", "")
    words = _words(value)
    matches = [category for category, aliases in _ALIASES.items() if words & aliases]
    return matches[0] if len(matches) == 1 else None


def notification_categories(settings):
    if "outgoing_notification_categories" in settings:
        selected = settings["outgoing_notification_categories"]
        return [category for category in CATEGORY_LABELS if isinstance(selected, list) and category in selected]
    # Preserve existing choices until the independent outgoing filter is saved.
    return [category for category in CATEGORY_LABELS
            if settings.get("notify_" + category, category == "person")]


def allows_notification(settings, entry):
    return notification_category(entry) in notification_categories(settings)
