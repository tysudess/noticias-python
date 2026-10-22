from __future__ import annotations

from pathlib import Path

from monitor_noticias.matching.video_defense_term_patch import (
    strict_phrase_decision,
    strict_phrase_matches,
)

ROOT = Path(__file__).resolve().parents[2]


def _fallback(text: str, phrase: str) -> bool:
    return phrase.lower() in text.lower()


def test_ministro_da_defesa_does_not_match_another_minister_and_distant_defense_mention():
    text = (
        "Ministro da Fazenda anuncia medidas econômicas. "
        "Em outro assunto, o Ministério da Defesa divulgou uma nota."
    )
    assert strict_phrase_decision(text, "MINISTRO DA DEFESA") is False
    assert strict_phrase_matches(text, "MINISTRO DA DEFESA", _fallback) is False


def test_ministro_da_saude_or_educacao_does_not_match_defense_minister():
    for text in (
        "Ministro da Saúde anuncia novas medidas.",
        "Ministro da Educação participa de reunião com autoridades.",
        "Ministro da Fazenda e Ministro da Justiça falam sobre orçamento.",
    ):
        assert strict_phrase_matches(text, "Ministro da Defesa", _fallback) is False


def test_defense_minister_query_accepts_masculine_and_feminine_role_forms():
    assert strict_phrase_decision("Ministro da Defesa anuncia operação", "Ministro da Defesa") is True
    assert strict_phrase_decision("Ministra da Defesa anuncia operação", "Ministro da Defesa") is True
    assert strict_phrase_decision("MINISTRO DA DEFESA", "ministra da defesa") is True


def test_ministerio_da_defesa_is_a_separate_strict_term():
    assert strict_phrase_decision("O Ministério da Defesa publicou uma nota", "MINISTÉRIO DA DEFESA") is True
    assert strict_phrase_decision("O Ministro da Defesa publicou uma nota", "MINISTÉRIO DA DEFESA") is False
    assert strict_phrase_decision("Ministro da Fazenda; Ministério da Defesa", "Ministro da Defesa") is False


def test_unrelated_video_terms_keep_existing_flexible_matcher():
    assert strict_phrase_decision("Ministro da Fazenda comenta operação da Marinha", "MARINHA") is None
    assert strict_phrase_matches("Ministro da Fazenda comenta operação da Marinha", "MARINHA", _fallback) is True


def test_runtime_installs_guard_in_the_active_video_search_path():
    composition = (ROOT / "src/monitor_noticias/app/composition.py").read_text(encoding="utf-8")
    patch = (ROOT / "src/monitor_noticias/matching/video_defense_term_patch.py").read_text(encoding="utf-8")
    assert "install_video_defense_term_patch()" in composition
    assert 'search_module.phrase_matches = guarded_rules' in patch
    assert 'rules_module.phrase_matches = guarded_rules' in patch


def test_installer_patches_the_function_used_by_video_search(monkeypatch):
    import sys
    from types import ModuleType

    import monitor_noticias.matching as matching_package
    import monitor_noticias.matching.video_defense_term_patch as patch_module

    def legacy_matcher(text: str, phrase: str) -> bool:
        # Reproduz o tipo de falso positivo: palavras significativas em posições
        # independentes no texto, sem validar que o cargo é uma expressão.
        normalized_text = " ".join(text.lower().split())
        wanted = [word for word in phrase.lower().split() if word not in {"da", "de", "do", "das", "dos"}]
        return bool(wanted) and all(word in normalized_text for word in wanted)

    rules = ModuleType("monitor_noticias.matching.video_rules")
    rules.phrase_matches = legacy_matcher
    policy = ModuleType("monitor_noticias.matching.video_match_policy")
    policy.phrase_matches = legacy_matcher
    search = ModuleType("monitor_noticias.repositories.video_search")
    search.phrase_matches = legacy_matcher

    monkeypatch.setitem(sys.modules, rules.__name__, rules)
    monkeypatch.setitem(sys.modules, policy.__name__, policy)
    monkeypatch.setitem(sys.modules, search.__name__, search)
    monkeypatch.setattr(patch_module, "_PATCHED", False)
    monkeypatch.setattr(matching_package, "phrase_matches", getattr(matching_package, "phrase_matches", None), raising=False)
    monkeypatch.setattr(matching_package, "repository_video_phrase_matches", getattr(matching_package, "repository_video_phrase_matches", None), raising=False)

    patch_module.install_video_defense_term_patch()

    unrelated = "Ministro da Fazenda anuncia cortes; Ministério da Defesa divulgou nota."
    relevant = "Ministro da Defesa anuncia nova operação."
    assert search.phrase_matches(unrelated, "MINISTRO DA DEFESA") is False
    assert search.phrase_matches(relevant, "MINISTRO DA DEFESA") is True
