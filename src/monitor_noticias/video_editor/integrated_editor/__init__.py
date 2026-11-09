from .advanced_editor_v300 import AdvancedVideoEditorWidget300
from monitor_noticias.ui.video_output_format_v128 import install_video_output_format_patch

# Instala o seletor antes de qualquer tela do Editor de Vídeo ser construída.
install_video_output_format_patch(AdvancedVideoEditorWidget300)

__all__ = ["AdvancedVideoEditorWidget300"]
