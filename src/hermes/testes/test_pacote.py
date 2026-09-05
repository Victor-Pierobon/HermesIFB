"""Testes de comunicacao/pacote.py — ver docs/specs/pacote.md."""
import pytest

from hermes.comunicacao.pacote import (
    TAMANHO_PACOTE,
    Pacote,
    PacoteInvalidoError,
    TipoMsg,
    desempacotar,
)


def test_caso1_ida_e_volta_preserva_campos():
    original = Pacote(parada_id=10, linha_id=130, req_id=42,
                       qtd_pendentes=3, tipo_msg=TipoMsg.SOLIC)
    dados = original.empacotar()
    assert len(dados) == TAMANHO_PACOTE
    assert desempacotar(dados) == original


def test_caso2_crc_corrompido_rejeitado():
    dados = bytearray(Pacote(1, 1, 1, 1, TipoMsg.ACK).empacotar())
    dados[-1] ^= 0xFF
    with pytest.raises(PacoteInvalidoError):
        desempacotar(bytes(dados))


def test_caso3_tamanho_errado_rejeitado():
    with pytest.raises(PacoteInvalidoError):
        desempacotar(b"\x00" * 5)


@pytest.mark.parametrize("campo", ["parada_id", "linha_id", "req_id"])
def test_caso4_campo_uint16_fora_do_intervalo_rejeitado(campo):
    valores = dict(parada_id=1, linha_id=1, req_id=1,
                   qtd_pendentes=1, tipo_msg=TipoMsg.SOLIC)
    valores[campo] = 65536
    with pytest.raises(PacoteInvalidoError):
        Pacote(**valores).empacotar()


def test_caso5_qtd_pendentes_fora_do_intervalo_rejeitado():
    pacote = Pacote(parada_id=1, linha_id=1, req_id=1,
                     qtd_pendentes=256, tipo_msg=TipoMsg.SOLIC)
    with pytest.raises(PacoteInvalidoError):
        pacote.empacotar()


def test_caso6_tipo_msg_fora_do_enum_rejeitado_ao_empacotar():
    pacote = Pacote(parada_id=1, linha_id=1, req_id=1,
                     qtd_pendentes=1, tipo_msg=0x99)
    with pytest.raises(PacoteInvalidoError):
        pacote.empacotar()


def test_caso7_tipo_msg_fora_do_enum_rejeitado_ao_desempacotar():
    import struct
    corpo = struct.pack(">HHHBB", 1, 1, 1, 1, 0x99)
    crc = 0
    for byte in corpo:
        crc ^= byte
    dados = corpo + bytes([crc])
    with pytest.raises(PacoteInvalidoError):
        desempacotar(dados)


@pytest.mark.parametrize("tipo", [TipoMsg.SOLIC, TipoMsg.ACK, TipoMsg.HEARTBEAT])
def test_caso8_cada_tipo_msg_preservado_no_round_trip(tipo):
    original = Pacote(1, 1, 1, 1, tipo)
    assert desempacotar(original.empacotar()).tipo_msg == tipo
