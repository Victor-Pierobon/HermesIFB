"""Contador de pendentes por (parada_id, linha_id). Ver docs/specs/pendentes.md."""
from __future__ import annotations

from collections import defaultdict


class ContadorPendentes:
    def __init__(self) -> None:
        self._contagem: dict[tuple[int, int], int] = defaultdict(int)

    def incrementar(self, parada_id: int, linha_id: int) -> int:
        chave = (parada_id, linha_id)
        self._contagem[chave] += 1
        return self._contagem[chave]

    def decrementar(self, parada_id: int, linha_id: int) -> int:
        chave = (parada_id, linha_id)
        # ponytail: clamp silencioso em 0, sem log de inconsistência —
        # se isso mascarar bug de contagem na integração, trocar por um
        # contador que também expõe "decrementos descartados" para diagnóstico.
        self._contagem[chave] = max(0, self._contagem[chave] - 1)
        return self._contagem[chave]

    def total(self, parada_id: int, linha_id: int) -> int:
        return self._contagem[(parada_id, linha_id)]
