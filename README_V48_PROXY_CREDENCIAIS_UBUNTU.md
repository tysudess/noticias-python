# V48 — Proxy Geral e credenciais seguras no Ubuntu

Esta versão é CUMULATIVA: já inclui a fundação V47.

Windows continua usando DPAPI CurrentUser.

Ubuntu/Linux usa Secret Service / keyring da sessão do usuário, sem fallback
para senha em plaintext.

Dependências Linux:
- keyring>=25,<26
- SecretStorage>=3.3,<4

PyAudioWPatch passa a ser dependência somente Windows no pyproject.toml.

Arquivos novos V48:
- src/monitor_noticias/platform/credentials.py
- src/monitor_noticias/ui/settings_credentials_patch.py
- tests/unit/test_platform_credentials.py
- tests/unit/test_proxy_secure_storage.py

Arquivos substituídos V48:
- src/monitor_noticias/platform/__init__.py
- src/monitor_noticias/networking/proxy.py
- src/monitor_noticias/app/application.py
- requirements.txt
- pyproject.toml

O pacote também carrega os arquivos V47 necessários para permitir aplicação
direta da V48 mesmo que a V47 ainda não tenha sido enviada ao GitHub.

WORKFLOW: NÃO PRECISA ALTERAR.

Próxima fase: V49, abertura de arquivos/pastas e binários externos Linux.
