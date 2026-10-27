"""Filesystem maintenance called by a background worker, never the UI timer."""
from datetime import datetime


def startup_maintenance(manager, settings):
    clean = settings.get("auto_clean_on_startup", True)
    if clean:
        manager.prune_orphaned_snapshots(max_age_days=3, max_count=1000)
    quota = settings.get("storage_quota_gb", 0)
    if quota > 0 and settings.get("auto_purge_on_quota", False):
        manager.enforce_quota(quota)
    days = int(settings.get("retention_days", 7))
    if clean and days > 0:
        snooze = settings.get("retention_snooze_until")
        if snooze:
            try:
                if datetime.now() < datetime.fromisoformat(snooze):
                    return False
            except (TypeError, ValueError):
                pass
        if settings.get("retention_prompt_before_delete", True):
            return True  # Ask on the UI thread after filesystem work is done.
        expired = manager.get_alerts_older_than(days=days)
        ids = [entry["id"] for entry in expired if entry.get("id")]
        if ids:
            manager.remove_alerts(ids)
    return False
