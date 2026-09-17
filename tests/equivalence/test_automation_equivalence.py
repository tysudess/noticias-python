from datetime import datetime
from monitor_noticias.app.preferences import SharedPreferences
from monitor_noticias.automation import AutomationSettings, DEFAULT_VIDEO_TIMES


def test_kotlin_default_schedule_equivalence(tmp_path):
    s=AutomationSettings(SharedPreferences(tmp_path/"monitor_prefs.properties"))
    assert (s.news_interval_minutes,s.demand_interval_minutes,s.video_schedule_times)==(30,60,DEFAULT_VIDEO_TIMES)


def test_kotlin_due_math_equivalence(tmp_path):
    p=SharedPreferences(tmp_path/"monitor_prefs.properties"); s=AutomationSettings(p)
    now=10_000_000; p.update(desktop_auto_news_at=now-30*60_000,desktop_auto_demands_at=now-60*60_000)
    assert now-s.last_news_auto_at >= s.news_interval_minutes*60_000
    assert now-s.last_demand_auto_at >= s.demand_interval_minutes*60_000


def test_kotlin_video_slot_key_equivalence():
    dt=datetime(2026,9,12,19,0,45)
    assert dt.strftime("%H:%M")=="19:00"
    assert dt.strftime("%Y-%m-%d-%H-%M")=="2026-09-12-19-00"
