"""Simulação ponta-a-ponta: totem + ônibus via RadioMock.

HERMES.md seção 10, item 5: instancia totem e ônibus ligados pelo mock,
dispara uma solicitação e valida o ciclo completo SOLIC -> ACK -> CONFIRMADO.
É também o "relógio real" que as specs de estados.py/pacote.py deixam fora
de escopo (quem decide quando chamar timeout() e monta o Pacote de fato).

Rodar como script: python -m hermes.simulacao_e2e
"""
from __future__ import annotations

import threading
from typing import Callable

from hermes.aplicacao.estados import Estado, Totem
from hermes.aplicacao.pendentes import ContadorPendentes
from hermes.aplicacao.solicitacao import (
    Solicitacao,
    StatusSolicitacao,
    confirmar,
    criar_solicitacao,
    expirar,
)
from hermes.comunicacao.pacote import Pacote, TipoMsg
from hermes.comunicacao.radio import Radio
from hermes.comunicacao.radio_mock import RadioMock

_ENDERECO_TOTEM = ("127.0.0.1", 47001)
_ENDERECO_ONIBUS = ("127.0.0.1", 47002)

PARADA_ID = 10
LINHA_ID = 130


class NoOnibus:
    """Lado ônibus: escuta a própria linha, conta pendentes e confirma."""

    def __init__(self, radio: Radio, linha_id: int) -> None:
        self._radio = radio
        self._linha_id = linha_id
        self._parar = threading.Event()
        # ponytail: set nunca é limpo — cresce sem limite numa execução
        # longa de verdade. Numa simulação curta não importa; em produção
        # precisaria de expiração (ex.: TTL por req_id) na integração real.
        self._vistos: set[int] = set()
        self.pendentes = ContadorPendentes()

    def rodar(self) -> None:
        while not self._parar.is_set():
            pacote = self._radio.receber(timeout=0.2)
            if pacote is None or pacote.tipo_msg != TipoMsg.SOLIC:
                continue
            if pacote.linha_id != self._linha_id:
                continue  # HERMES.md seção 4: só processa SOLIC da própria linha
            if pacote.req_id not in self._vistos:
                self._vistos.add(pacote.req_id)
                self.pendentes.incrementar(pacote.parada_id, pacote.linha_id)
            total = self.pendentes.total(pacote.parada_id, pacote.linha_id)
            self._radio.enviar(Pacote(
                pacote.parada_id, pacote.linha_id, pacote.req_id,
                min(total, 255), TipoMsg.ACK,
            ))

    def parar(self) -> None:
        self._parar.set()


def solicitar_embarque(
    radio: Radio,
    parada_id: int,
    linha_id: int,
    *,
    timeout_ack: float = 1.0,
    max_tentativas: int = 3,
    ao_confirmar: Callable[[], None] | None = None,
) -> tuple[Totem, Solicitacao]:
    """Lado totem: FSM + retry, seguindo docs/specs/estados.md."""
    totem = Totem(max_tentativas=max_tentativas, ao_confirmar=ao_confirmar)
    solicitacao = criar_solicitacao(parada_id, linha_id)

    totem.toque()
    totem.confirma_linha()

    while totem.estado not in (Estado.CONFIRMADO, Estado.FALHA):
        radio.enviar(Pacote(parada_id, linha_id, solicitacao.req_id, 0, TipoMsg.SOLIC))
        totem.pacote_enviado()

        resposta = radio.receber(timeout=timeout_ack)
        recebeu_ack = (
            resposta is not None
            and resposta.tipo_msg == TipoMsg.ACK
            and resposta.req_id == solicitacao.req_id
        )
        if recebeu_ack:
            totem.ack_recebido()
        else:
            totem.timeout()

    if totem.estado is Estado.CONFIRMADO:
        solicitacao = confirmar(solicitacao)
    else:
        solicitacao = expirar(solicitacao)
    return totem, solicitacao


def executar_simulacao() -> None:
    with RadioMock(_ENDERECO_TOTEM, _ENDERECO_ONIBUS) as radio_totem, \
         RadioMock(_ENDERECO_ONIBUS, _ENDERECO_TOTEM) as radio_onibus:

        onibus = NoOnibus(radio_onibus, LINHA_ID)
        thread_onibus = threading.Thread(target=onibus.rodar, daemon=True)
        thread_onibus.start()

        print(f"[totem] solicitando embarque — parada {PARADA_ID}, linha {LINHA_ID}")
        totem, solicitacao = solicitar_embarque(
            radio_totem, PARADA_ID, LINHA_ID,
            ao_confirmar=lambda: print("[totem] embarque solicitado (gancho de voz)"),
        )

        onibus.parar()
        thread_onibus.join(timeout=1)

    assert totem.estado is Estado.CONFIRMADO, f"esperado CONFIRMADO, obtido {totem.estado}"
    assert solicitacao.status is StatusSolicitacao.CONFIRMADA
    assert onibus.pendentes.total(PARADA_ID, LINHA_ID) == 1

    print(f"[onibus] pendentes na parada {PARADA_ID}: "
          f"{onibus.pendentes.total(PARADA_ID, LINHA_ID)}")
    print("[e2e] ciclo SOLIC -> ACK -> CONFIRMADO completo")


if __name__ == "__main__":
    executar_simulacao()
