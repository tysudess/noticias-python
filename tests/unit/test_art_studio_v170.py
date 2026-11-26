from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_run_installs_v170_after_v169_and_before_application_main():
    source = _read("run.py")
    assert source.index("install_art_studio_v169()") < source.index("install_art_studio_v170()")
    assert source.index("install_art_studio_v170()") < source.index(
        "from monitor_noticias.app.application import main"
    )


def test_delete_key_is_centralized_and_duplicate_delete_actions_are_disabled():
    source = _read("src/monitor_noticias/ui/art_studio_v170.py")
    assert "class _DeleteKeyFilter(QObject)" in source
    assert "event.key() != Qt.Key.Key_Delete" in source
    assert "action.setShortcuts([])" in source
    assert "app.installEventFilter(key_filter)" in source


def test_delete_uses_canvas_or_layers_selection_and_filters_canvas_background():
    source = _read("src/monitor_noticias/ui/art_studio_v170.py")
    assert "_selected_layer_items(page, fallback=False)" in source
    assert "page.scene.selectedItems()" in source
    assert "item.data(ITEM_KIND_KEY) != CANVAS_BG_KEY" in source


def test_delete_preserves_text_editing_and_form_field_behaviour():
    source = _read("src/monitor_noticias/ui/art_studio_v170.py")
    assert "QLineEdit, QTextEdit, QPlainTextEdit, QAbstractSpinBox" in source
    assert "focus.isEditable()" in source
    assert "Qt.TextInteractionFlag.NoTextInteraction" in source
    assert "if _is_text_entry_focus(page, focus):" in source


def test_delete_handles_multiple_roots_locked_items_groups_history_and_autosave():
    source = _read("src/monitor_noticias/ui/art_studio_v170.py")
    assert "deletion_plan(" in source
    assert "is_locked=lambda item: bool(item.data(LOCKED_KEY))" in source
    assert "page.scene.removeItem(item)" in source
    assert "page._v154_layer_selection = list(preserved)" in source
    assert "_schedule_layer_history(page)" in source
    assert "_schedule_autosave(page)" in source


def test_delete_button_and_layers_tab_share_the_same_safe_handler():
    source = _read("src/monitor_noticias/ui/art_studio_v170.py")
    assert 'delete_button.clicked.connect(lambda _checked=False: _delete_active_selection(page))' in source
    assert 'button.clicked.connect(lambda _checked=False: _delete_active_selection(page))' in source
    assert 'layout.insertWidget(min(2, layout.count()), button)' in source


def test_header_compaction_hides_all_six_requested_widgets_without_disabling_features():
    source = _read("src/monitor_noticias/ui/art_studio_v170.py")
    for name in (
        '"proxy_chip"', '"auto_chip"', '"clock"',
        '"_auth_user_label"', '"_auth_account_button"', '"_auth_logout_button"',
    ):
        assert name in source
    assert 'widget.hide()' in source
    assert 'runtime.logout' not in source
    assert 'proxy_config' not in source
    assert 'automatic_monitoring' not in source


def test_header_compaction_is_deferred_until_after_auth_widgets_are_added():
    source = _read("src/monitor_noticias/ui/art_studio_v170.py")
    assert "QTimer.singleShot(0, lambda window=self: _compact_main_header(window))" in source
    assert "_v170_header_compacted" in source


def test_visual_design_uses_original_central_studio_identity_and_both_themes():
    source = _read("src/monitor_noticias/ui/art_studio_v170.py")
    assert '_DARK =' in source and '_LIGHT =' in source
    assert '"CENTRAL STUDIO"' in source
    assert '"DESIGN  •  COMPOSIÇÃO  •  PUBLICAÇÃO"' in source
    assert "_style_for_theme(theme)" in source
    assert "_wrap_v161_skin()" in source


def test_visual_refinement_preserves_existing_splitter_and_tabs():
    source = _read("src/monitor_noticias/ui/art_studio_v170.py")
    assert 'getattr(page, "_v162_workspace_splitter", None)' in source
    assert "bar.setUsesScrollButtons(True)" in source
    assert "bar.setElideMode(Qt.TextElideMode.ElideRight)" in source


def test_installer_is_idempotent():
    source = _read("src/monitor_noticias/ui/art_studio_v170.py")
    assert "_v170_delete_installed" in source
    assert "_v170_visual_refinement_done" in source
    assert "_v170_integration_installed" in source
