"""Ciclo de vida de uma solicitação de embarque. Ver docs/specs/solicitacao.md."""
from __future__ import annotations

import random
from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum, auto
from typing import Callable

_REQ_ID_MIN, _REQ_ID_MAX = 0, 65535


class StatusSolicitacao(Enum):
    ENVIADA = auto()
    CONFIRMADA = auto()
    EXPIRADA = auto()


class SolicitacaoInvalidaError(Exception):
    """req_id fora do intervalo válido ou transição de status não permitida."""


@dataclass(frozen=True)
class Solicitacao:
    req_id: int
    parada_id: int
    linha_id: int
    criado_em: datetime
    status: StatusSolicitacao = StatusSolicitacao.ENVIADA


def criar_solicitacao(
    parada_id: int,
    linha_id: int,
    *,
    gerador_req_id: Callable[[], int] | None = None,
    agora: Callable[[], datetime] | None = None,
) -> Solicitacao:
    gerar = gerador_req_id or (lambda: random.randint(_REQ_ID_MIN, _REQ_ID_MAX))
    req_id = gerar()
    if not (_REQ_ID_MIN <= req_id <= _REQ_ID_MAX):
        raise SolicitacaoInvalidaError(
            f"req_id {req_id} fora do intervalo {_REQ_ID_MIN}-{_REQ_ID_MAX}"
        )
    criado_em = (agora or datetime.now)()
    return Solicitacao(req_id, parada_id, linha_id, criado_em)


def _transicionar(solicitacao: Solicitacao, novo_status: StatusSolicitacao) -> Solicitacao:
    if solicitacao.status is not StatusSolicitacao.ENVIADA:
        raise SolicitacaoInvalidaError(
            f"não é possível ir para {novo_status} a partir de {solicitacao.status}"
        )
    return replace(solicitacao, status=novo_status)


def confirmar(solicitacao: Solicitacao) -> Solicitacao:
    return _transicionar(solicitacao, StatusSolicitacao.CONFIRMADA)


def expirar(solicitacao: Solicitacao) -> Solicitacao:
    return _transicionar(solicitacao, StatusSolicitacao.EXPIRADA)
