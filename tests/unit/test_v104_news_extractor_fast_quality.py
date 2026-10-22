from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_v104_bootstrap_is_the_built_entrypoint_on_both_platforms():
    package = json.loads(read("tools/news_extractor/package.json"))
    assert package["main"] == "monitor-bootstrap.js"
    assert "monitor-bootstrap.js" in package["build"]["files"]
    assert package["build"]["win"]["artifactName"] == "ExtratorMateriasPortable-V1.25.19.exe"


def test_v104_fast_mode_caps_network_wait_and_reuses_duplicate_html_reads():
    text = read("tools/news_extractor/monitor-bootstrap.js")
    assert "FAST_TIMEOUT_MS = 8500" in text
    assert "AbortSignal.timeout = function centralNewsFastTimeout" in text
    assert "htmlCache.set(key" in text
    assert "responseFromCache(ResponseCtor, htmlCache.get(key))" in text
    assert "Math.min(retries, 2)" in text


def test_v104_keeps_existing_proxy_and_headless_one_shot_worker():
    bootstrap = read("tools/news_extractor/monitor-bootstrap.js")
    assert "require('./monitor-main.js')" in bootstrap
    assert "CENTRAL_NEWS_FAST_MODE" in bootstrap
    assert "monitor-main.js" in bootstrap
    assert "MONITOR_PERSISTENT" not in bootstrap


def test_v104_quality_guard_deduplicates_noise_and_flags_short_uol_previews():
    bootstrap = read("tools/news_extractor/monitor-bootstrap.js")
    quality = read("tools/news_extractor/article-quality.js")
    assert "function cleanArticleBody(text)" in quality
    assert "seen.has(key)" in quality
    assert "isStandaloneNoise(paragraph)" in quality
    assert "cleanArticleBody" in bootstrap
    assert "materia.avisoCompletude" in bootstrap
    assert "não vai apresentar esse trecho como matéria completa" in bootstrap


def test_v104_diagnostic_contains_required_v101_regression_markers():
    text = read("portable/linux/TESTAR-PORTABLE.sh")
    assert "libx264" in text
    assert "rawvideo pipe" in text
    assert "FFmpeg não precisa mais abrir o DISPLAY via x11grab" in text
    assert "-frames:v 1" not in text
    assert "timeout 8" not in text
