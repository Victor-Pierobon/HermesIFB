"""Testes de aplicacao/solicitacao.py — ver docs/specs/solicitacao.md."""
from datetime import datetime

import pytest

from hermes.aplicacao.solicitacao import (
    Solicitacao,
    SolicitacaoInvalidaError,
    StatusSolicitacao,
    confirmar,
    criar_solicitacao,
    expirar,
)


def test_caso1_criar_solicitacao_campos_basicos():
    sol = criar_solicitacao(1, 130)
    assert sol.parada_id == 1
    assert sol.linha_id == 130
    assert sol.status == StatusSolicitacao.ENVIADA
    assert 0 <= sol.req_id <= 65535


def test_caso2_gerador_req_id_injetavel():
    sol = criar_solicitacao(1, 130, gerador_req_id=lambda: 42)
    assert sol.req_id == 42


def test_caso3_agora_injetavel():
    quando = datetime(2026, 1, 1)
    sol = criar_solicitacao(1, 130, agora=lambda: quando)
    assert sol.criado_em == quando


def test_caso4_req_id_fora_do_intervalo_rejeitado():
    with pytest.raises(SolicitacaoInvalidaError):
        criar_solicitacao(1, 130, gerador_req_id=lambda: 70000)


def test_caso5_confirmar_muda_status_sem_alterar_original():
    sol = criar_solicitacao(1, 130, gerador_req_id=lambda: 1)
    confirmada = confirmar(sol)
    assert confirmada.status == StatusSolicitacao.CONFIRMADA
    assert confirmada.req_id == sol.req_id
    assert confirmada.parada_id == sol.parada_id
    assert confirmada.linha_id == sol.linha_id
    assert confirmada.criado_em == sol.criado_em
    assert sol.status == StatusSolicitacao.ENVIADA


def test_caso6_expirar_muda_status():
    sol = criar_solicitacao(1, 130, gerador_req_id=lambda: 1)
    expirada = expirar(sol)
    assert expirada.status == StatusSolicitacao.EXPIRADA


def test_caso7_confirmar_duas_vezes_rejeitado():
    sol = confirmar(criar_solicitacao(1, 130, gerador_req_id=lambda: 1))
    with pytest.raises(SolicitacaoInvalidaError):
        confirmar(sol)


@pytest.mark.parametrize("transicao", [confirmar, expirar])
def test_caso8_transicionar_a_partir_de_expirada_rejeitado(transicao):
    sol = expirar(criar_solicitacao(1, 130, gerador_req_id=lambda: 1))
    with pytest.raises(SolicitacaoInvalidaError):
        transicao(sol)


def test_caso9_req_id_cai_no_intervalo_valido_sem_gerador_fixo():
    sol1 = criar_solicitacao(1, 130)
    sol2 = criar_solicitacao(1, 130)
    assert 0 <= sol1.req_id <= 65535
    assert 0 <= sol2.req_id <= 65535
