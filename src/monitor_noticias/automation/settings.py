from __future__ import annotations
from datetime import datetime
from monitor_noticias.app.preferences import SharedPreferences


DEFAULT_VIDEO_TIMES = {"08:00", "12:00", "15:00", "19:00", "21:00"}


class AutomationSettings:
    def __init__(self, prefs: SharedPreferences) -> None:
        self.prefs = prefs

    @property
    def automatic_monitoring(self) -> bool:
        return self.prefs.get_boolean("desktop_automatic_monitoring", True)
    @automatic_monitoring.setter
    def automatic_monitoring(self, value: bool) -> None:
        self.prefs.update(desktop_automatic_monitoring=value)

    @property
    def news_automatic(self) -> bool: return self.prefs.get_boolean("desktop_news_automatic", True)
    @news_automatic.setter
    def news_automatic(self, value: bool) -> None: self.prefs.update(desktop_news_automatic=value)

    @property
    def demand_automatic(self) -> bool: return self.prefs.get_boolean("desktop_demand_automatic", True)
    @demand_automatic.setter
    def demand_automatic(self, value: bool) -> None: self.prefs.update(desktop_demand_automatic=value)

    @property
    def video_automatic(self) -> bool: return self.prefs.get_boolean("desktop_video_automatic", True)
    @video_automatic.setter
    def video_automatic(self, value: bool) -> None: self.prefs.update(desktop_video_automatic=value)

    @property
    def news_interval_minutes(self) -> int: return max(15, self.prefs.get_int("desktop_news_interval", 30))
    @news_interval_minutes.setter
    def news_interval_minutes(self, value: int) -> None: self.prefs.update(desktop_news_interval=max(15, int(value)))

    @property
    def demand_interval_minutes(self) -> int: return max(15, self.prefs.get_int("desktop_demand_interval", 60))
    @demand_interval_minutes.setter
    def demand_interval_minutes(self, value: int) -> None: self.prefs.update(desktop_demand_interval=max(15, int(value)))

    @property
    def video_schedule_times(self) -> set[str]:
        raw = self.prefs.get_string_set("desktop_video_schedule_times", DEFAULT_VIDEO_TIMES) or set()
        out: set[str] = set()
        for value in raw:
            try:
                dt = datetime.strptime(value.strip(), "%H:%M")
                if dt.strftime("%H:%M") == value.strip(): out.add(value.strip())
            except ValueError:
                pass
        return out

    @video_schedule_times.setter
    def video_schedule_times(self, values: set[str]) -> None:
        clean: set[str] = set()
        for raw in values:
            try: clean.add(datetime.strptime(raw.strip(), "%H:%M").strftime("%H:%M"))
            except ValueError: pass
        self.prefs.update(desktop_video_schedule_times=clean)

    @property
    def last_news_auto_at(self) -> int: return self.prefs.get_long("desktop_auto_news_at", 0)
    @property
    def last_demand_auto_at(self) -> int: return self.prefs.get_long("desktop_auto_demands_at", 0)
    @property
    def last_video_auto_at(self) -> int: return self.prefs.get_long("desktop_auto_video_at", 0)
    @property
    def last_video_slot(self) -> str: return self.prefs.get_string("desktop_auto_video_slot", "") or ""

    def mark_news_triggered(self, now_ms: int) -> None: self.prefs.update(desktop_auto_news_at=now_ms)
    def mark_demand_triggered(self, now_ms: int) -> None: self.prefs.update(desktop_auto_demands_at=now_ms)
    def mark_video_triggered(self, now_ms: int, slot_key: str) -> None:
        self.prefs.update(desktop_auto_video_slot=slot_key, desktop_auto_video_at=now_ms)
