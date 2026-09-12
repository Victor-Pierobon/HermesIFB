"""Testes de comunicacao/radio_mock.py — ver docs/specs/radio_mock.md."""
import socket

from hermes.comunicacao.pacote import Pacote, TipoMsg
from hermes.comunicacao.radio_mock import RadioMock

_A = ("127.0.0.1", 52301)
_B = ("127.0.0.1", 52302)


def test_caso1_ida_e_volta_entre_dois_radiomock():
    with RadioMock(_A, _B) as a, RadioMock(_B, _A) as b:
        pacote = Pacote(1, 130, 42, 3, TipoMsg.SOLIC)
        a.enviar(pacote)
        assert b.receber(timeout=1) == pacote


def test_caso2_receber_sem_nada_enviado_retorna_none_apos_timeout():
    with RadioMock(_A, _B) as a:
        assert a.receber(timeout=0.1) is None


def test_caso3_bytes_corrompidos_retornam_none():
    with RadioMock(_A, _B) as b:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as bruto:
            bruto.sendto(b"lixo corrompido", _A)
        assert b.receber(timeout=1) is None


def test_caso4_mensagens_chegam_em_ordem():
    with RadioMock(_A, _B) as a, RadioMock(_B, _A) as b:
        pacotes = [Pacote(1, 130, i, 0, TipoMsg.SOLIC) for i in range(3)]
        for pacote in pacotes:
            a.enviar(pacote)
        recebidos = [b.receber(timeout=1) for _ in pacotes]
        assert recebidos == pacotes


def test_caso5_fechar_libera_a_porta():
    radio = RadioMock(_A, _B)
    radio.fechar()
    with RadioMock(_A, _B) as novo:
        assert novo is not None
