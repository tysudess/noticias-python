from __future__ import annotations

import base64
import json
import re
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from .http_client import HttpClient


UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125 Safari/537.36"
)

BATCH = (
    "https://news.google.com/_/DotsSplashUi/data/"
    "batchexecute?rpcids=Fbv4je"
)


def is_google_news(url: str) -> bool:
    try:
        host = (
            urlsplit(url).hostname
            or ""
        ).lower()
        return (
            host == "news.google.com"
            or host.endswith(
                ".news.google.com"
            )
        )
    except Exception:
        return (
            "news.google.com"
            in str(url or "").lower()
        )


class GoogleNewsUrlResolver:
    """Resolve links Google News para a URL real do veículo.

    V36:
    - NÃO guarda falhas no cache;
    - tenta formato legado;
    - tenta resolução assinada atual;
    - tenta RPC somente com o ID;
    - usa o HttpClient fornecido pelo Central, portanto respeita Proxy Geral.
    """

    def __init__(
        self,
        http: HttpClient | None = None,
    ) -> None:
        self.http = (
            http
            or HttpClient()
        )

        # Somente sucessos são mantidos.
        self.cache: dict[
            str,
            str,
        ] = {}

    def resolve(
        self,
        input_: str,
    ) -> str:
        input_ = str(
            input_ or ""
        ).strip()

        if not input_:
            return input_

        if not is_google_news(
            input_
        ):
            return input_

        cached = self.cache.get(
            input_
        )

        if cached:
            return cached

        decoded = self._resolve(
            input_
        )

        if (
            decoded
            and decoded.startswith(
                ("http://", "https://")
            )
            and not is_google_news(
                decoded
            )
        ):
            self.cache[input_] = (
                decoded
            )
            return decoded

        # IMPORTANTE:
        # não guardar input_ no cache quando a resolução falhar.
        # A próxima tentativa pode funcionar após mudança de proxy/rede.
        return input_

    def _resolve(
        self,
        input_: str,
    ) -> str | None:
        try:
            article_id = (
                urlsplit(input_)
                .path
                .rstrip("/")
                .split("/")[-1]
                .strip()
            )
        except Exception:
            return None

        if not article_id:
            return None

        return (
            self._legacy(
                article_id
            )
            or self._signed(
                article_id
            )
            or self._id_only(
                article_id
            )
        )

    def _legacy(
        self,
        article_id: str,
    ) -> str | None:
        try:
            padded = (
                article_id
                + "="
                * (
                    (
                        4
                        - len(article_id)
                        % 4
                    )
                    % 4
                )
            )

            text = (
                base64
                .urlsafe_b64decode(
                    padded
                )
                .decode(
                    "latin1"
                )
            )

            starts = [
                index
                for index
                in (
                    text.find(
                        "https://"
                    ),
                    text.find(
                        "http://"
                    ),
                )
                if index >= 0
            ]

            if not starts:
                return None

            start = min(
                starts
            )
            end = len(
                text
            )

            for index, char in enumerate(
                text[start:],
                start,
            ):
                if (
                    ord(char) < 32
                    or char == "\x00"
                ):
                    end = index
                    break

            candidate = (
                text[start:end]
                .strip()
            )

            if (
                urlsplit(
                    candidate
                ).hostname
                and not is_google_news(
                    candidate
                )
            ):
                return candidate

        except Exception:
            pass

        return None

    def _signed(
        self,
        article_id: str,
    ) -> str | None:
        urls = (
            (
                "https://news.google.com/"
                f"articles/{article_id}"
                "?hl=pt-BR&gl=BR&ceid=BR:pt-419"
            ),
            (
                "https://news.google.com/"
                f"rss/articles/{article_id}"
                "?hl=pt-BR&gl=BR&ceid=BR:pt-419"
            ),
        )

        for source_url in urls:
            try:
                text = (
                    self.http.get_text(
                        source_url,
                        headers={
                            "User-Agent":
                                UA,
                            "Accept-Language":
                                "pt-BR,pt;q=0.9,"
                                "en-US;q=0.8,en;q=0.7",
                        },
                        connect_timeout=10,
                        read_timeout=15,
                    )
                )

                soup = BeautifulSoup(
                    text,
                    "html.parser",
                )

                node = (
                    soup.select_one(
                        "c-wiz > "
                        "div[data-n-a-sg]"
                        "[data-n-a-ts]"
                    )
                    or soup.select_one(
                        "[data-n-a-id="
                        f"'{article_id}']"
                        "[data-n-a-sg]"
                        "[data-n-a-ts]"
                    )
                    or soup.select_one(
                        "[data-n-a-sg]"
                        "[data-n-a-ts]"
                    )
                )

                if node is None:
                    continue

                signature = str(
                    node.get(
                        "data-n-a-sg",
                        "",
                    )
                ).strip()

                timestamp = str(
                    node.get(
                        "data-n-a-ts",
                        "",
                    )
                ).strip()

                article = str(
                    node.get(
                        "data-n-a-id",
                        "",
                    )
                    or article_id
                ).strip()

                if (
                    not signature
                    or not timestamp
                ):
                    continue

                inner = json.dumps(
                    [
                        "garturlreq",
                        [
                            [
                                "pt-BR",
                                "BR",
                                [
                                    "FINANCE_TOP_INDICES",
                                    "WEB_TEST_1_0_0",
                                ],
                                None,
                                None,
                                1,
                                1,
                                "BR:pt-419",
                                None,
                                480,
                                None,
                                None,
                                None,
                                None,
                                None,
                                0,
                                5,
                            ],
                            "pt-BR",
                            "BR",
                            1,
                            [
                                2,
                                4,
                                8,
                            ],
                            1,
                            1,
                            None,
                            0,
                            0,
                            None,
                            0,
                        ],
                        article,
                        int(
                            timestamp
                        ),
                        signature,
                    ],
                    ensure_ascii=False,
                    separators=(
                        ",",
                        ":",
                    ),
                )

                resolved = (
                    self._batch(
                        inner
                    )
                )

                if resolved:
                    return resolved

            except Exception:
                continue

        return None

    def _id_only(
        self,
        article_id: str,
    ) -> str | None:
        try:
            inner = json.dumps(
                [
                    "garturlreq",
                    [
                        [
                            "en-US",
                            "US",
                            [
                                "FINANCE_TOP_INDICES",
                                "WEB_TEST_1_0_0",
                            ],
                            None,
                            None,
                            1,
                            1,
                            "US:en",
                            None,
                            180,
                            None,
                            None,
                            None,
                            None,
                            None,
                            0,
                            None,
                            None,
                            [
                                1608992183,
                                723341000,
                            ],
                        ],
                        "en-US",
                        "US",
                        1,
                        [
                            2,
                            3,
                            4,
                            8,
                        ],
                        1,
                        0,
                        "655000234",
                        0,
                        0,
                        None,
                        0,
                    ],
                    article_id,
                ],
                separators=(
                    ",",
                    ":",
                ),
            )

            return self._batch(
                inner
            )

        except Exception:
            return None

    def _batch(
        self,
        inner: str,
    ) -> str | None:
        try:
            payload = json.dumps(
                [
                    [
                        [
                            "Fbv4je",
                            inner,
                            None,
                            "generic",
                        ]
                    ]
                ],
                separators=(
                    ",",
                    ":",
                ),
            )

            body = (
                self.http
                .post_form_text(
                    BATCH,
                    {
                        "f.req":
                            payload,
                    },
                    headers={
                        "User-Agent":
                            UA,
                        "Content-Type":
                            "application/"
                            "x-www-form-urlencoded;"
                            "charset=UTF-8",
                        "Referer":
                            "https://news.google.com/",
                    },
                    connect_timeout=10,
                    read_timeout=15,
                )
            )

            return self._extract(
                body
            )

        except Exception:
            return None

    @staticmethod
    def _extract(
        body: str,
    ) -> str | None:
        body = str(
            body or ""
        )

        # Formato RPC estruturado.
        chunks = [
            chunk
            for chunk
            in body.split(
                "\n\n"
            )
            if chunk.strip()
        ]

        for chunk in chunks:
            clean = chunk.strip()

            if clean.startswith(
                ")]}'"
            ):
                clean = (
                    clean[4:]
                    .lstrip()
                )

            try:
                outer = json.loads(
                    clean
                )
            except Exception:
                continue

            stack = [
                outer
            ]

            while stack:
                value = stack.pop()

                if isinstance(
                    value,
                    list,
                ):
                    # Resposta comum:
                    # ["garturlres", "https://veiculo/..."]
                    if (
                        len(value) > 1
                        and value[0]
                        == "garturlres"
                        and isinstance(
                            value[1],
                            str,
                        )
                    ):
                        candidate = (
                            value[1]
                        )

                        if (
                            candidate.startswith(
                                (
                                    "http://",
                                    "https://",
                                )
                            )
                            and not is_google_news(
                                candidate
                            )
                        ):
                            return candidate

                    stack.extend(
                        value
                    )

                elif isinstance(
                    value,
                    dict,
                ):
                    stack.extend(
                        value.values()
                    )

                elif isinstance(
                    value,
                    str,
                ):
                    if value.startswith(
                        (
                            "[",
                            "{",
                        )
                    ):
                        try:
                            stack.append(
                                json.loads(
                                    value
                                )
                            )
                        except Exception:
                            pass

                    elif value.startswith(
                        (
                            "http://",
                            "https://",
                        )
                    ):
                        low = (
                            value.lower()
                        )

                        if (
                            not is_google_news(
                                value
                            )
                            and "googleusercontent.com"
                            not in low
                            and "gstatic.com"
                            not in low
                        ):
                            return value

        # Fallback textual para respostas escapadas.
        normalized = (
            body
            .replace(
                "\\/",
                "/",
            )
            .replace(
                "\\u003d",
                "=",
            )
            .replace(
                "\\u0026",
                "&",
            )
            .replace(
                "\\u0025",
                "%",
            )
        )

        for candidate in re.findall(
            r'https?://[^\\"\s]+',
            normalized,
        ):
            candidate = (
                candidate
                .rstrip(
                    ",]}\\"
                )
            )

            low = (
                candidate.lower()
            )

            if (
                not is_google_news(
                    candidate
                )
                and "googleusercontent.com"
                not in low
                and "gstatic.com"
                not in low
            ):
                return candidate

        return None
