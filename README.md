# Monitor de Notícias — migração Python

## Projeto

Fundação técnica da migração controlada do **Monitor de Notícias** para Python. A migração funcional ainda não foi concluída.

- **Fonte da verdade:** `tysudess/noticias-monitor`
- **Novo projeto:** `tysudess/MONITOR-DE-NOTICAS-PYTHON`
- **Baseline funcional aprovada:** Portable V8 / Build SHA `df1701ba5427a04954093e8ebed63f26abb2b2b7`

## Tecnologias-base

- Python **3.12.x**
- PySide6 **6.9.1**
- SQLite (será usado quando o módulo de banco for migrado; nenhum schema foi criado neste passo)
- FFmpeg/FFprobe (dependências futuras do Portable; apenas localização de caminhos foi preparada)

A escolha de Python 3.12 e PySide6 6.9.1 preserva as versões usadas pelo build V8 aprovado, evitando troca de motor ou versão sem evidência.

## Regra da migração

O repositório Kotlin permanece somente como referência. A implementação Python deve reproduzir os comportamentos documentados nos MIG-XXX sem inventar, modernizar, substituir motores ou preencher lacunas por suposição. Quando não houver evidência, registrar **NÃO DETERMINADO PELO CÓDIGO ANALISADO**.

## Preparar o ambiente

No Windows, com Python 3.12 instalado para desenvolvimento:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Executar

```powershell
python run.py
```

A execução atual abre somente uma janela mínima PySide6 para validar a fundação.

## Testes

```powershell
pytest
```

## Estrutura

- `src/monitor_noticias/app`: bootstrap da aplicação, caminhos e exceções globais.
- `src/monitor_noticias/ui`: UI mínima; telas reais ainda não migradas.
- `models`, `database`, `repositories`, `collectors`, `matching`, `automation`, `networking`, `windows`, `video`, `pdf`, `extraction`, `utils`: placeholders estruturais para os passos futuros.
- `bin`: reservado para binários portáteis aprovados; nada é baixado automaticamente.
- `resources`: recursos distribuíveis.
- `data`, `logs`, `temp`: diretórios runtime.
- `tests/equivalence`: futuros testes Kotlin × Python por MIG.
- `docs`: arquitetura, decisões e checklist MIG.

## Ainda não migrado

Coletores, matching completo, automações, notícias, vídeos, demandas, banco real, integração Windows completa, Editor de PDF, Editor de Vídeo, extrator/downloader e demais regras de negócio continuam pendentes.
