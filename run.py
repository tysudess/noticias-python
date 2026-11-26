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

from monitor_noticias.ui.art_studio_v154 import install_art_studio_v154

install_art_studio_v154()

from monitor_noticias.ui.art_studio_v155 import install_art_studio_v155

install_art_studio_v155()

from monitor_noticias.ui.art_studio_v156 import install_art_studio_v156

install_art_studio_v156()

from monitor_noticias.ui.art_studio_v157 import install_art_studio_v157

install_art_studio_v157()

from monitor_noticias.ui.art_studio_v158 import install_art_studio_v158

install_art_studio_v158()

from monitor_noticias.ui.art_studio_v159 import install_art_studio_v159

install_art_studio_v159()

# V160: contraste dos ícones da navegação e espaçamento entre caracteres.
from monitor_noticias.ui.art_studio_v160 import install_art_studio_v160

install_art_studio_v160()

# Correção: disponibiliza weakref da biblioteca padrão antes da importação V161.
from monitor_noticias.ui.art_studio_v161_compat import install_art_studio_v161_weakref_compatibility

install_art_studio_v161_weakref_compatibility()

# V161: reformulação profissional dos painéis e da área de trabalho do Estúdio.
from monitor_noticias.ui.art_studio_v161 import install_art_studio_v161

install_art_studio_v161()

# V162: painéis redimensionáveis, modo foco e inspetor contextual.
from monitor_noticias.ui.art_studio_v162 import install_art_studio_v162

install_art_studio_v162()

# V163: biblioteca pesquisável de componentes gráficos vetoriais editáveis.
from monitor_noticias.ui.art_studio_v163 import install_art_studio_v163

install_art_studio_v163()

# V164: laboratório de imagem não destrutivo, com filtros, máscaras e bordas.
from monitor_noticias.ui.art_studio_v164 import install_art_studio_v164

install_art_studio_v164()

# V165: acabamento fotográfico avançado e enquadramento focal não destrutivo.
from monitor_noticias.ui.art_studio_v165 import install_art_studio_v165

install_art_studio_v165()

# V166: recorte não destrutivo de fundo por cor com tolerância e suavização.
from monitor_noticias.ui.art_studio_v166 import install_art_studio_v166

install_art_studio_v166()

# V167: estúdio profissional de tipografia para textos do canvas.
from monitor_noticias.ui.art_studio_v167 import install_art_studio_v167

install_art_studio_v167()

from monitor_noticias.app.application import main

if __name__ == "__main__":
    raise SystemExit(main())
