from monitor_noticias.auth.models import AuthSession, AuthUser
from monitor_noticias.ui.auth_window_integration import _allowed_sections
from monitor_noticias.ui.sections import Section


def test_permissions_map_sections():
    session = AuthSession(
        token="x",
        expires_at=None,
        user=AuthUser(
            username="op",
            name="Operador",
            profile="OPERADOR",
            permissions=frozenset({"home", "news", "videos"}),
        ),
    )

    allowed = _allowed_sections(session)

    assert Section.HOME in allowed
    assert Section.NEWS in allowed
    assert Section.VIDEOS in allowed
    assert Section.SETTINGS not in allowed
