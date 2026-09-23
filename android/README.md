# Central Inteligente de Mídia — Android

Esta pasta contém a nova versão Android da Central Inteligente de Mídia.

## Objetivo da fase 1

- manter a versão Windows intacta;
- criar uma interface mobile nativa em Qt Quick/QML;
- gerar um APK arm64 instalável;
- preparar a navegação para receber os módulos existentes gradualmente.

## Estrutura

- `main.py`: entrada da aplicação Android;
- `qml/Main.qml`: dashboard e navegação mobile;
- `pyproject.toml`: manifesto do projeto Qt for Python;
- `requirements.txt`: dependências do host de desenvolvimento.

## Arquitetura

A versão Android não executa os binários .exe usados pelo portable Windows.
As regras de negócio que forem multiplataforma serão reaproveitadas. Integrações
específicas de Windows serão substituídas por implementações Android.

## Primeiros módulos previstos

1. Notícias
2. Demandas
3. Fontes
4. Histórico
5. Capas
6. Extrator
7. PDF
8. Configurações
