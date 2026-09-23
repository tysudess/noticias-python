CENTRAL INTELIGENTE DE MÍDIA — UBUNTU PORTABLE
================================================

Este pacote NÃO é AppImage.

Ele é uma pasta portátil com:
- Python/PySide6 empacotado pelo PyInstaller;
- Qt/QtWebEngine;
- FFmpeg e FFprobe;
- yt-dlp;
- Deno;
- helper Globoplay;
- runtime Linux do Extrator de Matérias;
- todas as abas atuais da Central.

COMO USAR
---------

1. Extraia o arquivo .tar.gz inteiro.

2. Abra a pasta:
   Central-Inteligente-de-Midia-Ubuntu-Portable-x86_64

3. Execute:
   ./INICIAR-CENTRAL.sh

Também é possível executar diretamente:
   ./CentralInteligenteDeMidia

NÃO mova somente o executável principal para fora da pasta.
Os diretórios _internal, bin, resources e tools fazem parte do portable.

DADOS DO PROGRAMA
-----------------

Como esta versão é realmente portátil, os dados ficam na própria pasta:

- data/
- logs/
- temp/
- Videos/
- VideoEditorExports/

Assim a pasta inteira pode ser movida para outro computador.

SE NÃO ABRIR
------------

Execute:

   ./TESTAR-PORTABLE.sh

O diagnóstico será salvo em:

   logs/diagnostico-portable.txt

O log de inicialização fica em:

   logs/inicializacao.log

COMPATIBILIDADE
---------------

Alvo:
- Ubuntu Desktop 22.04 x86_64
- Ubuntu Desktop 24.04 x86_64

Gravador:
- X11: captura de tela habilitada.
- Wayland: a Central abre normalmente; a captura de tela aguarda o backend
  via portal ScreenCast/PipeWire.

WhatsApp e Planilhas permanecem fora da Central, conforme removidos do
projeto anteriormente.
