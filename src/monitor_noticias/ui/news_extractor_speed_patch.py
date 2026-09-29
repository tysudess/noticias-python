from __future__ import annotations

import json
import os
from pathlib import Path
import time
import uuid

from PySide6.QtCore import (
    QProcess,
    QProcessEnvironment,
)
from PySide6.QtWidgets import QLabel

from monitor_noticias.ui.news_extractor_page import (
    NewsExtractorPage,
)
from monitor_noticias.ui.url_tools import (
    resolve_article_url,
)
from monitor_noticias.ui.news_extractor_proxy_patch import (
    _proxy_environment,
)


_PATCHED = False

# O motor Node possui um limite próprio menor. Este watchdog existe para
# proteger a UI caso o executável Electron deixe de responder por qualquer
# motivo (subprocesso, antivírus, rede, proxy ou encerramento incompleto).
DEFAULT_UI_TIMEOUT_MS = 50_000


def _process_running(
    process: QProcess | None,
) -> bool:
    return (
        process is not None
        and process.state()
        != QProcess.ProcessState.NotRunning
    )


def install_news_extractor_speed_patch() -> None:
    """V91: extração rápida sem worker Electron persistente.

    A V88 tentou manter um Electron aberto e enviar URLs por stdin. Em builds
    Portable reais esse canal pode permanecer aberto sem processar o comando,
    deixando a tela indefinidamente em "Extraindo...".

    A V91 volta ao modelo comprovado:
        1 clique -> 1 processo Electron headless -> 1 JSON -> encerra.

    Mantém:
    - Proxy Geral;
    - modo rápido;
    - resultado temporário JSON;
    - validação do motor atual;
    - timeout para que a interface nunca fique presa indefinidamente.
    """

    global _PATCHED

    if _PATCHED:
        return

    original_init = NewsExtractorPage.__init__
    original_consume = NewsExtractorPage._consume_result

    def patched_init(
        self: NewsExtractorPage,
        *args,
        **kwargs,
    ) -> None:
        original_init(
            self,
            *args,
            **kwargs,
        )

        self._v91_timeout_ms = (
            DEFAULT_UI_TIMEOUT_MS
        )

        # Corrige o texto da V88 para refletir o comportamento real.
        try:
            for label in self.findChildren(QLabel):
                text = label.text()

                if (
                    "O motor fica preparado após a primeira extração"
                    in text
                ):
                    label.setText(
                        "Cada matéria é extraída em um processo isolado. "
                        "Isso evita travamentos do motor entre uma URL e outra; "
                        "se um site não responder, a tentativa é encerrada "
                        "automaticamente."
                    )
                    label.setWordWrap(True)
        except Exception:
            pass

    def stop_one_shot(
        self: NewsExtractorPage,
    ) -> None:
        self._result_timer.stop()

        proc = self.process
        self.process = None
        self._worker_signature = None
        self._stdout_buffer = ""
        self._stderr_tail = ""

        if proc is None:
            return

        try:
            if _process_running(proc):
                proc.terminate()

                if not proc.waitForFinished(900):
                    proc.kill()
                    proc.waitForFinished(1200)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

        try:
            proc.deleteLater()
        except Exception:
            pass

    def drain_stdout(
        self: NewsExtractorPage,
    ) -> None:
        proc = self.process

        if proc is None:
            return

        try:
            data = bytes(
                proc.readAllStandardOutput()
            ).decode(
                "utf-8",
                "ignore",
            ).strip()

            if data:
                # Guardamos apenas a cauda para diagnóstico, sem permitir que
                # stdout encha o pipe do QProcess.
                self._stdout_buffer = (
                    self._stdout_buffer
                    + "\n"
                    + data
                )[-1600:]
        except Exception:
            pass

    def one_shot_extract(
        self: NewsExtractorPage,
    ) -> None:
        if self._request_active:
            return

        if _process_running(
            self.process
        ):
            return

        raw = self.url.text().strip()

        if not raw:
            self.status.setText(
                "Informe o link da matéria."
            )
            self.url.setFocus()
            return

        direct = str(
            resolve_article_url(raw)
            or raw
        ).strip()

        self.url.setText(direct)

        if not direct.lower().startswith(
            ("http://", "https://")
        ):
            self.status.setText(
                "O link precisa começar com http:// ou https://."
            )
            return

        if not self.exe.is_file():
            self.status.setText(
                "Motor do Extrator não encontrado no portable: "
                f"{self.exe}"
            )
            return

        try:
            proxy_env = _proxy_environment(
                Path(self.app_root)
            )
        except Exception as exc:
            self.status.setText(
                "Não foi possível ler o Proxy Geral do Central: "
                f"{exc}"
            )
            return

        if (
            proxy_env.get(
                "CENTRAL_PROXY_ENABLED"
            )
            == "1"
        ):
            required = (
                "CENTRAL_PROXY_HOST",
                "CENTRAL_PROXY_PORT",
                "CENTRAL_PROXY_USERNAME",
                "CENTRAL_PROXY_PASSWORD",
            )

            if not all(
                proxy_env.get(key)
                for key in required
            ):
                self.status.setText(
                    "O Proxy Geral está ativado, mas a configuração "
                    "está incompleta. Corrija em Configurações."
                )
                return

        temp_dir = (
            Path(self.app_root)
            / "temp"
        )
        temp_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        request_id = (
            uuid.uuid4().hex
        )

        result_file = (
            temp_dir
            / f"news-extractor-{request_id}.json"
        )

        try:
            result_file.unlink(
                missing_ok=True
            )
        except Exception:
            pass

        env = (
            QProcessEnvironment
            .systemEnvironment()
        )

        # Fluxo one-shot: NÃO usa MONITOR_PERSISTENT.
        try:
            env.remove(
                "MONITOR_PERSISTENT"
            )
        except Exception:
            pass

        env.insert(
            "MONITOR_HEADLESS",
            "1",
        )
        env.insert(
            "MONITOR_NEWS_URL",
            direct,
        )
        env.insert(
            "MONITOR_RESULT_FILE",
            str(result_file),
        )

        for key, value in (
            proxy_env.items()
        ):
            env.insert(
                str(key),
                str(value),
            )

        # Modo rápido conservador. O wrapper Node tem um hard timeout próprio.
        fast_env = {
            "CENTRAL_NEWS_FAST_MODE": "1",
            "CENTRAL_NEWS_BLOCK_IMAGES": "1",
            "CENTRAL_NEWS_BLOCK_MEDIA": "1",
            "CENTRAL_NEWS_NAV_TIMEOUT_MS": "18000",
            "CENTRAL_NEWS_IDLE_TIMEOUT_MS": "800",
            "CENTRAL_NEWS_HARD_TIMEOUT_MS": "38000",
        }

        for key, value in fast_env.items():
            env.insert(
                key,
                value,
            )

        proc = QProcess(self)
        proc.setProcessEnvironment(env)
        proc.setProgram(
            str(self.exe)
        )
        proc.setWorkingDirectory(
            str(self.exe.parent)
        )

        proc.readyReadStandardOutput.connect(
            lambda: drain_stdout(self)
        )
        proc.readyReadStandardError.connect(
            self._worker_stderr
        )
        proc.errorOccurred.connect(
            self._process_error
        )
        proc.finished.connect(
            self._worker_finished
        )

        self.process = proc
        self.result_file = result_file
        self._request_id = request_id
        self._request_active = True
        self._request_started_at = (
            time.monotonic()
        )
        self._stderr_tail = ""
        self._stdout_buffer = ""

        try:
            timeout_ms = int(
                os.environ.get(
                    "CENTRAL_NEWS_UI_TIMEOUT_MS",
                    DEFAULT_UI_TIMEOUT_MS,
                )
            )
        except Exception:
            timeout_ms = (
                DEFAULT_UI_TIMEOUT_MS
            )

        self._v91_timeout_ms = max(
            20_000,
            min(
                75_000,
                timeout_ms,
            ),
        )

        self.extract_button.setEnabled(
            False
        )
        self.extract_button.setText(
            "Extraindo…"
        )
        self.status.setText(
            "Extraindo matéria em processo isolado. Aguarde…"
        )

        proc.start()

        # Poll do arquivo continua útil porque o Electron grava o JSON antes
        # de terminar completamente.
        self._result_timer.start()

    def one_shot_poll(
        self: NewsExtractorPage,
    ) -> None:
        if not self._request_active:
            self._result_timer.stop()
            return

        result_file = self.result_file

        if (
            result_file is not None
            and result_file.is_file()
        ):
            self._consume_result()
            return

        elapsed_ms = int(
            (
                time.monotonic()
                - self._request_started_at
            )
            * 1000
        )

        if (
            elapsed_ms
            < self._v91_timeout_ms
        ):
            return

        proc = self.process

        self._request_failed(
            "Tempo limite da extração atingido. "
            "O site, a rede ou o proxy não respondeu dentro do limite. "
            "A tentativa foi encerrada para não deixar a Central travada."
        )

        if (
            proc is not None
            and _process_running(proc)
        ):
            try:
                proc.kill()
                proc.waitForFinished(
                    1200
                )
            except Exception:
                pass

        self.process = None

    def consume_one_shot(
        self: NewsExtractorPage,
    ) -> None:
        was_active = (
            self._request_active
        )

        original_consume(
            self
        )

        if (
            was_active
            and not self._request_active
            and self.text.toPlainText().strip()
        ):
            self.status.setText(
                "✓ Matéria extraída com sucesso. "
                "O conteúdo pode ser revisado e editado nesta tela."
            )

            proc = self.process

            # O JSON já foi gravado depois do histórico. Não precisamos manter
            # o Electron vivo após receber o resultado.
            if (
                proc is not None
                and _process_running(proc)
            ):
                try:
                    proc.terminate()
                except Exception:
                    pass

    NewsExtractorPage.__init__ = (
        patched_init
    )
    NewsExtractorPage.extract = (
        one_shot_extract
    )
    NewsExtractorPage._poll_result_file = (
        one_shot_poll
    )
    NewsExtractorPage._consume_result = (
        consume_one_shot
    )
    NewsExtractorPage._stop_worker = (
        stop_one_shot
    )
    NewsExtractorPage._drain_v91_stdout = (
        drain_stdout
    )

    _PATCHED = True
