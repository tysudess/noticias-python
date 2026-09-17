from __future__ import annotations

from monitor_noticias.app.preferences import SharedPreferences
from monitor_noticias.database.default_terms import DEFAULT_MONITOR_TERMS

KEY_TERMS = "video_terms_v400"
KEY_INITIALIZED = "video_terms_v400_initialized"
KEY_DEFAULTS_V7_MIGRATED = "video_terms_v7_defaults_migrated"

def _clean(values):
    unique = {}
    for raw in values:
        value = str(raw).strip()
        if value:
            unique.setdefault(value.lower(), value)
    return sorted(unique.values(), key=str.lower)

class VideoTermStore:
    """Port do VideoTermStore.kt: termos de vídeo independentes dos de notícias."""
    def __init__(self, prefs: SharedPreferences) -> None:
        self.prefs = prefs

    def load(self, seed_terms):
        if not self.prefs.get_boolean(KEY_INITIALIZED, False):
            seed = _clean([*seed_terms, *DEFAULT_MONITOR_TERMS])
            self.prefs.update(**{KEY_TERMS:set(seed), KEY_INITIALIZED:True, KEY_DEFAULTS_V7_MIGRATED:True})
            return seed
        current = _clean(self.prefs.get_string_set(KEY_TERMS, set()) or set())
        if not self.prefs.get_boolean(KEY_DEFAULTS_V7_MIGRATED, False):
            merged = _clean([*current, *DEFAULT_MONITOR_TERMS])
            self.prefs.update(**{KEY_TERMS:set(merged), KEY_DEFAULTS_V7_MIGRATED:True})
            return merged
        return current

    def add(self, value: str, seed_terms):
        current = self.load(seed_terms)
        clean_value = value.strip()
        if clean_value and all(item.lower() != clean_value.lower() for item in current):
            current.append(clean_value)
        return self.save(current)

    def remove(self, value: str, seed_terms):
        wanted = value.strip().lower()
        return self.save([item for item in self.load(seed_terms) if item.lower() != wanted])

    def save(self, values):
        cleaned = _clean(values)
        self.prefs.update(**{KEY_TERMS:set(cleaned), KEY_INITIALIZED:True, KEY_DEFAULTS_V7_MIGRATED:True})
        return cleaned
