MONITOR DE NOTÍCIAS — WINDOWS PORTABLE

COMO EXECUTAR
1. Extraia completamente o ZIP para uma pasta gravável.
2. Execute MonitorDeNoticias.exe.
3. Não execute o programa diretamente de dentro do ZIP.

REQUISITOS
- Windows x64 compatível com a build registrada em BUILD-INFO.json.
- Não é necessário instalar Python, FFmpeg ou FFprobe separadamente.
- Algumas funções dependem de acesso à internet e da disponibilidade das fontes externas.

ESTRUTURA
- MonitorDeNoticias.exe: aplicativo principal.
- _internal/: runtime Python, PySide6/Qt, plugins e dependências congeladas.
- bin/: yt-dlp, yt-dlp stable, Deno, FFmpeg e FFprobe usados pelo aplicativo.
- resources/: recursos do Monitor e helper interno do Globoplay.
- data/: bancos e preferências graváveis criados/atualizados pelo aplicativo.
- logs/: logs de execução.
- temp/: temporários controlados pela aplicação.
- Videos/: downloads do Extrator.
- VideoEditorExports/: exportações do Editor de Vídeo.

DADOS
A pasta portable contém diretórios vazios de dados. Bancos e configurações são criados pelo próprio programa e permanecem ao lado do executável.

LOGS
Os logs ficam em logs/monitor-noticias.log.

ATUALIZAÇÃO
Preserve a pasta data/ quando substituir uma build por outra, salvo orientação específica de migração futura.

PROBLEMAS CONHECIDOS
- Mover a pasta depois de habilitar "Iniciar com Windows" pode deixar o Registro apontando para o caminho anterior; desative e ative novamente após mover.
- Serviços web externos podem mudar ou ficar indisponíveis independentemente do portable.

INTEGRIDADE
Confira o SHA-256 publicado ao lado do ZIP antes de distribuir ou arquivar a build.
