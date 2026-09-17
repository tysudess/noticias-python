from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace

from PySide6.QtWidgets import QApplication
import pytest

from monitor_noticias.app.paths import AppPaths
from monitor_noticias.app.preferences import SharedPreferences
from monitor_noticias.automation import AutomationSettings, AutomationState
from monitor_noticias.database import NewsDb, VideoDb
from monitor_noticias.models import News, VideoItem
from monitor_noticias.networking.proxy import ProxyConfig
from monitor_noticias.ui.catalog import NEWS_SOURCES, SPECIALIZED, VIDEO_SOURCES
from monitor_noticias.ui.controller import MainUiController
from monitor_noticias.ui.main_window import MainWindow
from monitor_noticias.ui.sections import SECTION_ORDER, Section


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


class FakeSecretStore:
    def __init__(self): self.value=""
    def exists(self): return bool(self.value)
    def save(self,text): self.value=text
    def load(self): return self.value
    def delete(self): self.value=""; return True


class FakeProxy:
    def __init__(self): self.cfg=ProxyConfig()
    def load(self): return self.cfg
    def save(self,*,enabled,host,port,username,password):
        self.cfg=ProxyConfig(enabled=enabled,host=host.strip() or "proxy-7dn.mb",port=max(1,min(65535,int(port))),username=username.strip(),password=password); return self.cfg
    def test_connection(self): return True,"Conexão pelo proxy realizada com sucesso."


class FakeStartup:
    def __init__(self): self.calls=[]
    def configure(self,enabled,**kwargs): self.calls.append(enabled); return True


class FakeAutomation:
    def __init__(self,prefs):
        self.settings=AutomationSettings(prefs); self.state=AutomationState(); self.calls=[]
    def search_news(self,from_ms=None,to_ms=None): self.calls.append(("news",from_ms,to_ms)); self.state.newsBusy=True; self.state.status="Buscando notícias..."; return True
    def search_videos(self,from_ms=None,to_ms=None): self.calls.append(("videos",from_ms,to_ms)); self.state.videoBusy=True; self.state.videoStatus="Buscando vídeos..."; return True
    def search_all_demands(self): self.calls.append(("demands",)); self.state.newsBusy=True; self.state.status="Buscando todas as demandas..."; return True
    def stop_news_search(self): self.calls.append(("stop_news",)); self.state.newsBusy=False
    def stop_video_search(self): self.calls.append(("stop_video",)); self.state.videoBusy=False
    def stop_all_searches(self): self.calls.append(("stop_all",)); self.state.newsBusy=False; self.state.videoBusy=False
    def close(self): self.calls.append(("close",))


def make_controller(tmp_path,with_automation=False):
    paths=AppPaths(tmp_path); paths.ensure_runtime_dirs(); prefs=SharedPreferences(paths.data/"prefs"/"monitor_prefs.properties"); auto=FakeAutomation(prefs) if with_automation else None
    return MainUiController(paths=paths,prefs=prefs,news_db=NewsDb(paths.news_db),video_db=VideoDb(paths.videos_db),proxy=FakeProxy(),startup=FakeStartup(),automation=auto,news_sources=NEWS_SOURCES,video_sources=VIDEO_SOURCES,specialized_sources=SPECIALIZED)


def test_main_window_contract_and_all_navigation(app,tmp_path):
    c=make_controller(tmp_path); w=MainWindow(c,c.paths)
    assert w.windowTitle()=="Monitor de Notícias - Windows Portable v4.0.2"
    assert w.width()==1600 and w.height()==960
    assert len(w.nav_buttons)==len(SECTION_ORDER)==12
    for section in SECTION_ORDER:
        w.navigate(section); assert w.stack.currentWidget() is w.pages[section]; assert w.nav_buttons[section].isChecked()
    w.exit_application()


def test_close_hides_instead_of_exiting(app,tmp_path):
    c=make_controller(tmp_path); w=MainWindow(c,c.paths); w.show(); app.processEvents(); w.close(); app.processEvents(); assert not w.isVisible(); assert w._allow_close is False
    w.exit_application()


def test_terms_and_demands_crud_refresh(app,tmp_path):
    c=make_controller(tmp_path); initial=len(c.state.terms); c.add_term("Termo Step 9"); assert "Termo Step 9" in c.state.terms and len(c.state.terms)>=initial+1; c.remove_term("Termo Step 9"); assert "Termo Step 9" not in c.state.terms
    c.add_demand("Veículo teste","Assunto teste"); assert any(d.vehicle=="Veículo teste" and d.subject=="Assunto teste" for d in c.state.demands); did=next(d.id for d in c.state.demands if d.vehicle=="Veículo teste"); c.remove_demand(did); assert all(d.id!=did for d in c.state.demands); c.close()


def test_news_video_history_and_filters(app,tmp_path):
    c=make_controller(tmp_path); now=1_800_000_000_000
    c.news_db.insertNews([News(title="Marinha em operação",source="Fonte X",date=now,link="https://example.test/n",snippet="Resumo",matchedTerm="Marinha",capturedAt=now)])
    c.video_db.insert([VideoItem(title="Vídeo naval",sourceId="x",sourceName="Fonte Y",publishedAt=now,link="https://example.test/v",summary="Resumo",matchedTerm="Naval",capturedAt=now)])
    # listNews/listAll são o contrato do histórico; refresh de 24h/7d depende do relógio real.
    assert c.news_db.listNews(10)[0].title=="Marinha em operação"; assert c.video_db.listAll(10)[0].title=="Vídeo naval"; c.clear_news_history(); c.clear_video_history(); assert not c.news_db.listNews(10) and not c.video_db.listAll(10); c.close()


def test_manual_actions_use_automation_port(app,tmp_path):
    c=make_controller(tmp_path,with_automation=True); assert c.search_news(); assert c.search_videos(); c.automation.state.newsBusy=False; assert c.search_all_demands(); assert [x[0] for x in c.automation.calls[:3]]==["news","videos","demands"]; c.stop_all_searches(); assert c.automation.calls[-1][0]=="stop_all"; c.close()


def test_missing_business_repositories_not_faked(app,tmp_path):
    c=make_controller(tmp_path,with_automation=False); assert c.search_available is False; assert c.search_news() is False; assert "ainda não foram migrados" in c.state.status; assert c.search_videos() is False; assert "ainda não foram migrados" in c.state.video_status; c.close()


def test_settings_proxy_startup_and_secure_password_field(app,tmp_path):
    c=make_controller(tmp_path); w=MainWindow(c,c.paths); page=w.pages[Section.SETTINGS]; assert page.password.echoMode()==page.password.EchoMode.Password; page.proxy_enabled.setChecked(True); page.host.setText("proxy.test"); page.port.setValue(6060); page.user.setText("usuario"); page.password.setText("senha-ficticia"); page._save_proxy(); assert c.proxy_config.password=="senha-ficticia"; assert page.password.text()==""; page.startup.setChecked(True); assert c.startup.calls[-1] is True; w.exit_application()


def test_source_catalog_news_exact_count_and_video_gap_is_explicit():
    assert len(NEWS_SOURCES)==160
    assert len(SPECIALIZED)==12
    assert {x.id for x in VIDEO_SOURCES}=={"youtube-g1","youtube-domingo-espetacular"}
