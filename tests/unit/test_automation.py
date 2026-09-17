from __future__ import annotations
from datetime import datetime
import threading, time
from monitor_noticias.app.preferences import SharedPreferences
from monitor_noticias.automation import *

class FakeClock:
    def __init__(self, ms=0, dt=None): self.ms=ms; self.dt=dt or datetime(2026,9,12,10,0)
    def now_ms(self): return self.ms
    def local_datetime(self): return self.dt

class NewsRunnerFake:
    def __init__(self): self.calls=[]; self.block=None
    def search_news(self, *, token, progress, from_ms=None, to_ms=None):
        self.calls.append(("news",from_ms,to_ms)); progress(LiveSearchProgress(active=True, completed=1,total=2))
        if self.block:
            while not token.cancelled: time.sleep(.001)
            token.raise_if_cancelled()
        return SearchResult(foundCount=4,newCount=2,newDemandCount=1,errors=0)
    def search_all_demands(self, *, token):
        self.calls.append(("demands",)); return DemandSweepResult(checkedCount=3,foundCount=2,newCount=1,errors=0)

class VideoRunnerFake:
    def __init__(self): self.calls=[]; self.block=None
    def search_videos(self, *, token, progress, from_ms=None, to_ms=None):
        self.calls.append(("videos",from_ms,to_ms)); progress(LiveSearchProgress(active=True,completed=1,total=1))
        if self.block:
            while not token.cancelled: time.sleep(.001)
            token.raise_if_cancelled()
        return VideoSearchResult(relevantCount=5,newRelevantCount=2,errors=1,unstableSources=("x",))

def make(tmp_path, clock):
    prefs=SharedPreferences(tmp_path/"prefs"/"monitor_prefs.properties")
    s=AutomationSettings(prefs); n=NewsRunnerFake(); v=VideoRunnerFake()
    svc=AutomationService(s,n,v,clock=clock)
    return svc,s,n,v,prefs

def wait_idle(svc):
    limit=time.time()+1
    while (svc.state.newsBusy or svc.state.videoBusy) and time.time()<limit: time.sleep(.002)

def test_defaults_and_minimums(tmp_path):
    svc,s,_,_,_=make(tmp_path,FakeClock())
    assert s.automatic_monitoring and s.news_automatic and s.demand_automatic and s.video_automatic
    assert s.news_interval_minutes==30 and s.demand_interval_minutes==60
    assert s.video_schedule_times=={"08:00","12:00","15:00","19:00","21:00"}
    s.news_interval_minutes=1; s.demand_interval_minutes=2
    assert s.news_interval_minutes==15 and s.demand_interval_minutes==15
    svc.close()

def test_news_has_priority_over_due_demands(tmp_path):
    c=FakeClock(ms=4_000_000,dt=datetime(2026,9,12,10,1)); svc,s,n,_,_=make(tmp_path,c)
    svc.tick(); wait_idle(svc)
    assert n.calls[0][0]=="news" and all(x[0]!="demands" for x in n.calls)
    assert s.last_news_auto_at==4_000_000 and s.last_demand_auto_at==0
    svc.close()

def test_demand_runs_when_news_not_due(tmp_path):
    c=FakeClock(ms=4_000_000,dt=datetime(2026,9,12,10,1)); svc,s,n,_,prefs=make(tmp_path,c)
    prefs.update(desktop_auto_news_at=4_000_000, desktop_auto_demands_at=0)
    svc.tick(); wait_idle(svc)
    assert n.calls==[("demands",)] and s.last_demand_auto_at==4_000_000
    svc.close()

def test_video_exact_local_minute_and_slot_guard(tmp_path):
    c=FakeClock(ms=10_000_000,dt=datetime(2026,9,12,12,0,31)); svc,s,_,v,_=make(tmp_path,c)
    # Evita news/demand nesta asserção.
    s.automatic_monitoring=False; s.automatic_monitoring=True
    svc.settings.prefs.update(desktop_auto_news_at=c.ms, desktop_auto_demands_at=c.ms)
    svc.tick(); wait_idle(svc); svc.tick(); wait_idle(svc)
    assert len(v.calls)==1
    assert s.last_video_slot=="2026-09-12-12-00"
    svc.close()

def test_missed_video_minute_is_not_caught_up(tmp_path):
    c=FakeClock(ms=10_000_000,dt=datetime(2026,9,12,12,1)); svc,s,_,v,p=make(tmp_path,c)
    p.update(desktop_auto_news_at=c.ms,desktop_auto_demands_at=c.ms)
    svc.tick(); wait_idle(svc); assert v.calls==[]
    svc.close()

def test_news_and_video_can_run_independently(tmp_path):
    c=FakeClock(ms=10_000_000,dt=datetime(2026,9,12,12,0)); svc,s,n,v,_=make(tmp_path,c)
    n.block=True; v.block=True; svc.tick(); time.sleep(.02)
    assert svc.state.newsBusy and svc.state.videoBusy
    svc.stop_all_searches(); wait_idle(svc); svc.close()

def test_duplicate_manual_news_is_guarded(tmp_path):
    svc,_,n,_,_=make(tmp_path,FakeClock()); n.block=True
    assert svc.search_news() is True; time.sleep(.01); assert svc.search_all_demands() is False; assert svc.search_news() is False
    svc.stop_news_search(); wait_idle(svc); svc.close()

def test_manual_and_automatic_use_same_news_method(tmp_path):
    svc,_,n,_,_=make(tmp_path,FakeClock())
    assert svc.search_news(100,200); wait_idle(svc)
    assert n.calls==[("news",100,200)]
    assert svc.state.status=="✓ 2 nova(s) notícia(s) • 1 demanda(s) • 0 falha(s)"
    svc.close()

def test_cancel_status_and_cleanup(tmp_path):
    svc,_,n,_,_=make(tmp_path,FakeClock()); n.block=True
    svc.search_news(); time.sleep(.01); svc.stop_news_search(); wait_idle(svc)
    assert svc.state.newsBusy is False
    assert svc.state.status=="⏹ Busca de notícias interrompida pelo usuário."
    svc.close()

def test_no_automation_retry_layer(tmp_path):
    class FailNews(NewsRunnerFake):
        def search_news(self, **kw): self.calls.append(("news",)); raise RuntimeError("boom")
    prefs=SharedPreferences(tmp_path/"p.properties"); s=AutomationSettings(prefs); n=FailNews(); v=VideoRunnerFake(); c=FakeClock(ms=2_000_000,dt=datetime(2026,9,12,10,1))
    svc=AutomationService(s,n,v,clock=c); svc.tick(); wait_idle(svc)
    assert n.calls==[("news",)]
    assert s.last_news_auto_at==2_000_000
    assert svc.state.status=="Falha na busca de notícias: boom"
    svc.close()

def test_progress_fraction_exact():
    assert LiveSearchProgress(completed=2,total=4).fraction==0.5
    assert LiveSearchProgress(completed=5,total=4).fraction==1.0
    assert LiveSearchProgress(total=0).fraction==0.0

def test_shared_preferences_scalars_and_string_set_roundtrip(tmp_path):
    path = tmp_path / "data" / "prefs" / "monitor_prefs.properties"
    prefs = SharedPreferences(path)
    prefs.update(flag=True, count=30, stamp=1234567890123, label="ok", slots={"08:00", "21:00"})
    reloaded = SharedPreferences(path)
    assert reloaded.get_boolean("flag", False) is True
    assert reloaded.get_int("count", 0) == 30
    assert reloaded.get_long("stamp", 0) == 1234567890123
    assert reloaded.get_string("label", "") == "ok"
    assert reloaded.get_string_set("slots", set()) == {"08:00", "21:00"}
    raw = path.read_text(encoding="utf-8")
    assert "08:00" not in raw and "21:00" not in raw
