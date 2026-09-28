# V82 — Corrigir EXE PyInstaller e preservar ícone

## Base
Patch preparado sobre a `main` confirmada antes da correção:

`a9938845ba051ee168cc4e4384b8bd9173a14d70`

Essa base já contém a V81.

## Erro corrigido
O portable da V81 podia gerar um `MonitorDeNoticias.exe` com aproximadamente
547 KB e, ao executar, mostrar:

`Could not load PyInstaller's embedded PKG archive from the executable`

## Causa
A V81 reabria o EXE **depois do COLLECT** usando as APIs Windows
`BeginUpdateResourceW` / `UpdateResourceW` para forçar o ícone.

O executável PyInstaller possui um overlay no fim do arquivo contendo o
CArchive/PKG. Regravar os recursos PE depois da montagem final pode eliminar ou
truncar esse overlay. Isso produz exatamente o erro observado.

## Correção
- removida toda alteração de `RT_ICON`/`RT_GROUP_ICON` posterior ao build;
- mantido o ícone pelo mecanismo nativo e suportado do PyInstaller:
  `icon=str(APP_ASSETS / "app_icon.ico")`;
- adicionada validação pós-COLLECT **somente de leitura**;
- o build falha se o EXE tiver menos de 2 MB;
- o build falha se `CArchiveReader` não conseguir abrir o PKG embutido;
- nenhum arquivo de Jornais Digitais, login, proxy, Home, PDF ou Android foi
  alterado nesta versão.

## Ícone no Windows Explorer
O `.ico` multi-resolução continua sendo usado pelo PyInstaller. O Windows pode
manter o ícone antigo em cache quando o executável é extraído repetidamente para
o mesmo caminho/nome. Para validar a nova compilação, extraia o portable em uma
pasta nova, por exemplo:

`Central-V82-Teste\MonitorDeNoticias.exe`

## Arquivos
### Substituir
- `MonitorDeNoticias.spec`

### Adicionar
- `tests/unit/test_windows_exe_v82.py`
- `README_V82_EXE_PYINSTALLER.md`

## WORKFLOW
**NÃO PRECISA ALTERAR.**

O workflow existente já executa `python -m PyInstaller --noconfirm --clean
MonitorDeNoticias.spec`; portanto a validação V82 roda dentro do próprio build.
