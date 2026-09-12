"""Testes de aplicacao/pendentes.py — ver docs/specs/pendentes.md."""
from hermes.aplicacao.pendentes import ContadorPendentes


def test_caso1_par_nunca_visto_total_zero():
    contador = ContadorPendentes()
    assert contador.total(1, 130) == 0


def test_caso2_incrementar_retorna_e_persiste_total():
    contador = ContadorPendentes()
    assert contador.incrementar(1, 130) == 1
    assert contador.total(1, 130) == 1


def test_caso3_incrementar_acumula():
    contador = ContadorPendentes()
    contador.incrementar(1, 130)
    contador.incrementar(1, 130)
    assert contador.incrementar(1, 130) == 3


def test_caso4_linhas_diferentes_mesma_parada_sao_independentes():
    contador = ContadorPendentes()
    contador.incrementar(1, 130)
    contador.incrementar(1, 130)
    contador.incrementar(1, 130)
    contador.incrementar(1, 200)
    assert contador.total(1, 130) == 3
    assert contador.total(1, 200) == 1


def test_caso5_paradas_diferentes_mesma_linha_sao_independentes():
    contador = ContadorPendentes()
    for _ in range(3):
        contador.incrementar(1, 130)
    contador.incrementar(2, 130)
    assert contador.total(1, 130) == 3
    assert contador.total(2, 130) == 1


def test_caso6_decrementar_reduz_total():
    contador = ContadorPendentes()
    for _ in range(3):
        contador.incrementar(1, 130)
    assert contador.decrementar(1, 130) == 2
    assert contador.total(1, 130) == 2


def test_caso7_decrementar_em_zero_nao_fica_negativo():
    contador = ContadorPendentes()
    assert contador.decrementar(1, 130) == 0
    assert contador.total(1, 130) == 0


def test_caso8_decrementar_par_nunca_incrementado():
    contador = ContadorPendentes()
    assert contador.decrementar(9, 9) == 0
