from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Instala a página do Estúdio antes da inicialização da interface principal.
from monitor_noticias.ui.art_studio_integration import install_art_studio

install_art_studio()

# Evoluções incrementais do Estúdio, mantendo os projetos anteriores.
from monitor_noticias.ui.art_studio_v148 import install_art_studio_v148

install_art_studio_v148()

# Compatibilidade Qt 6: normaliza KeyboardModifier.value antes dos atalhos V149.
from monitor_noticias.ui.art_studio_v149_compat import install_art_studio_v149_shortcut_compatibility

install_art_studio_v149_shortcut_compatibility()

from monitor_noticias.ui.art_studio_v149 import install_art_studio_v149

install_art_studio_v149()

from monitor_noticias.ui.art_studio_v150 import install_art_studio_v150

install_art_studio_v150()

from monitor_noticias.ui.art_studio_v151 import install_art_studio_v151

install_art_studio_v151()

from monitor_noticias.ui.art_studio_v152 import install_art_studio_v152

install_art_studio_v152()

from monitor_noticias.ui.art_studio_v153 import install_art_studio_v153

install_art_studio_v153()

from monitor_noticias.app.application import main

if __name__ == "__main__":
    raise SystemExit(main())
