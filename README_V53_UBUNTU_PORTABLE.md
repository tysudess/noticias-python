# V53 — Ubuntu Portable em pasta

## Mudança principal

AppImage foi abandonado.

Agora o GitHub gera:

`Central-Inteligente-de-Midia-Ubuntu-Portable-x86_64.tar.gz`

O arquivo contém uma pasta completa e portátil.

Não usa FUSE.
Não usa AppRun.
Não depende de montar AppImage.

## Como o usuário inicia

Depois de extrair:

`./INICIAR-CENTRAL.sh`

ou diretamente:

`./CentralInteligenteDeMidia`

## Estrutura final

Central-Inteligente-de-Midia-Ubuntu-Portable-x86_64/
- CentralInteligenteDeMidia
- INICIAR-CENTRAL.sh
- TESTAR-PORTABLE.sh
- README-UBUNTU-PORTABLE.txt
- _internal/
- bin/
- resources/
- tools/
- data/
- logs/
- temp/
- Videos/
- VideoEditorExports/

## Abas

O portable continua sendo construído a partir do repositório inteiro.

Portanto mantém as abas atuais:
- Início
- Notícias
- Vídeos
- Demandas
- Fontes
- Histórico
- Termos
- Parar buscas
- Extrator de Notícias
- Capas
- Editor PDF
- Extrator de Vídeos
- Editor de Vídeo
- Gravador de Tela
- Configurações

WhatsApp e Planilhas continuam removidos.

## Validação mais forte

O workflow não valida apenas a compilação.

Ele:
1. valida os binários;
2. executa o smoke test do PyInstaller;
3. inicia a interface real em X11 virtual com Xvfb;
4. exige que o programa permaneça aberto por 18 segundos;
5. cria o tar.gz;
6. extrai o tar.gz novamente;
7. valida permissões;
8. executa TESTAR-PORTABLE.sh;
9. executa novo smoke test a partir do arquivo extraído;
10. só então publica a Release.

## Logs

Se o portable não abrir no computador final:

`./TESTAR-PORTABLE.sh`

gera:

`logs/diagnostico-portable.txt`

O launcher registra inicialização em:

`logs/inicializacao.log`

## Arquivos novos

- portable/linux/INICIAR-CENTRAL.sh
- portable/linux/TESTAR-PORTABLE.sh
- portable/linux/README-UBUNTU-PORTABLE.txt

## Substituir

- .github/workflows/build-ubuntu.yml

## Mantidos

- MonitorDeNoticias-Linux.spec
- runtime Linux do Extrator de Matérias
- helper Globoplay Linux
- FFmpeg/FFprobe Linux
- yt-dlp Linux
- Deno Linux
- toda a camada multiplataforma V47–V52

## Workflow

SIM — SUBSTITUIR o workflow Ubuntu atual.

O workflow Windows `build-portable.yml` não deve ser alterado.
