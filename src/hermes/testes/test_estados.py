"""Testes de aplicacao/estados.py — ver docs/specs/estados.md."""
import pytest

from hermes.aplicacao.estados import Estado, TransicaoInvalidaError, Totem


def test_caso1_estado_inicial():
    totem = Totem()
    assert totem.estado == Estado.OCIOSO
    assert totem.tentativas == 0


def test_caso2_toque_vai_para_selecao_linha():
    totem = Totem()
    totem.toque()
    assert totem.estado == Estado.SELECAO_LINHA


def test_caso3_confirma_linha_vai_para_enviando():
    totem = Totem()
    totem.toque()
    totem.confirma_linha()
    assert totem.estado == Estado.ENVIANDO


def test_caso4_pacote_enviado_vai_para_aguarda_ack_e_conta_tentativa():
    totem = Totem()
    totem.toque()
    totem.confirma_linha()
    totem.pacote_enviado()
    assert totem.estado == Estado.AGUARDA_ACK
    assert totem.tentativas == 1


def test_caso5_ack_recebido_confirma_e_chama_hook():
    chamadas = []
    totem = Totem(ao_confirmar=lambda: chamadas.append(1))
    totem.toque()
    totem.confirma_linha()
    totem.pacote_enviado()
    totem.ack_recebido()
    assert totem.estado == Estado.CONFIRMADO
    assert chamadas == [1]


def test_caso6_timeout_com_tentativas_abaixo_do_limite_faz_retry():
    totem = Totem(max_tentativas=3)
    totem.toque()
    totem.confirma_linha()
    totem.pacote_enviado()  # tentativas = 1
    totem.timeout()
    assert totem.estado == Estado.ENVIANDO
    assert totem.tentativas == 1


def test_caso7_esgotar_tentativas_vai_para_falha():
    totem = Totem(max_tentativas=3)
    totem.toque()
    totem.confirma_linha()
    for _ in range(3):
        totem.pacote_enviado()
        totem.timeout()
    assert totem.estado == Estado.FALHA


def test_caso8_confirmado_timeout_volta_a_ocioso():
    totem = Totem()
    totem.toque()
    totem.confirma_linha()
    totem.pacote_enviado()
    totem.ack_recebido()
    totem.timeout()
    assert totem.estado == Estado.OCIOSO
    assert totem.tentativas == 0


@pytest.mark.parametrize("chegar_em", [
    "SELECAO_LINHA", "ENVIANDO", "AGUARDA_ACK", "CONFIRMADO", "FALHA",
])
def test_caso9_reset_de_qualquer_estado_volta_a_ocioso(chegar_em):
    totem = Totem(max_tentativas=1)
    totem.toque()
    if chegar_em == "SELECAO_LINHA":
        pass
    else:
        totem.confirma_linha()
        if chegar_em == "ENVIANDO":
            pass
        else:
            totem.pacote_enviado()
            if chegar_em == "AGUARDA_ACK":
                pass
            elif chegar_em == "CONFIRMADO":
                totem.ack_recebido()
            elif chegar_em == "FALHA":
                totem.timeout()  # max_tentativas=1 -> direto FALHA

    totem.reset()
    assert totem.estado == Estado.OCIOSO
    assert totem.tentativas == 0


def test_caso10_evento_fora_de_ordem_levanta_erro_e_mantem_estado():
    totem = Totem()
    with pytest.raises(TransicaoInvalidaError):
        totem.ack_recebido()
    assert totem.estado == Estado.OCIOSO


def test_caso11_reset_a_partir_de_falha():
    totem = Totem(max_tentativas=1)
    totem.toque()
    totem.confirma_linha()
    totem.pacote_enviado()
    totem.timeout()
    assert totem.estado == Estado.FALHA
    totem.reset()
    assert totem.estado == Estado.OCIOSO
