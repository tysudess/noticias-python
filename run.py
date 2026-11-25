from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Instala a nova página antes da inicialização da interface principal.
from monitor_noticias.ui.art_studio_integration import install_art_studio

install_art_studio()

# Evoluções do Estúdio são aplicadas depois da integração V143–V147,
# mantendo as versões anteriores e seus projetos compatíveis.
from monitor_noticias.ui.art_studio_v148 import install_art_studio_v148

install_art_studio_v148()

from monitor_noticias.app.application import main

if __name__ == "__main__":
    raise SystemExit(main())
