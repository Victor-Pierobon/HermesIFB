"""FSM do totem. Ver docs/specs/estados.md."""
from __future__ import annotations

from enum import Enum, auto
from typing import Callable


class Estado(Enum):
    OCIOSO = auto()
    SELECAO_LINHA = auto()
    ENVIANDO = auto()
    AGUARDA_ACK = auto()
    CONFIRMADO = auto()
    FALHA = auto()


class TransicaoInvalidaError(Exception):
    """Evento não permitido para o estado atual da FSM."""


class Totem:
    def __init__(self, max_tentativas: int = 3,
                 ao_confirmar: Callable[[], None] | None = None) -> None:
        self._max_tentativas = max_tentativas
        self._ao_confirmar = ao_confirmar
        self.estado = Estado.OCIOSO
        self.tentativas = 0

    def toque(self) -> None:
        self._transicionar(Estado.OCIOSO, Estado.SELECAO_LINHA)

    def confirma_linha(self) -> None:
        self._transicionar(Estado.SELECAO_LINHA, Estado.ENVIANDO)

    def pacote_enviado(self) -> None:
        self._transicionar(Estado.ENVIANDO, Estado.AGUARDA_ACK)
        self.tentativas += 1

    def ack_recebido(self) -> None:
        self._transicionar(Estado.AGUARDA_ACK, Estado.CONFIRMADO)
        if self._ao_confirmar is not None:
            self._ao_confirmar()

    def timeout(self) -> None:
        if self.estado is Estado.AGUARDA_ACK:
            if self.tentativas < self._max_tentativas:
                self.estado = Estado.ENVIANDO
            else:
                self.estado = Estado.FALHA
        elif self.estado is Estado.CONFIRMADO:
            self._ir_para_ocioso()
        else:
            raise TransicaoInvalidaError(
                f"timeout() inválido em {self.estado}"
            )

    def reset(self) -> None:
        self._ir_para_ocioso()

    def _ir_para_ocioso(self) -> None:
        self.estado = Estado.OCIOSO
        self.tentativas = 0

    def _transicionar(self, de: Estado, para: Estado) -> None:
        if self.estado is not de:
            raise TransicaoInvalidaError(
                f"evento inválido em {self.estado}, esperava {de}"
            )
        self.estado = para
