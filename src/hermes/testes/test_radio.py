"""Testes de comunicacao/radio.py — ver docs/specs/radio.md."""
from hermes.comunicacao.radio import Radio
from hermes.comunicacao.radio_mock import RadioMock


def test_caso1_radio_mock_satisfaz_protocolo_radio():
    with RadioMock(("127.0.0.1", 52101), ("127.0.0.1", 52102)) as radio:
        assert isinstance(radio, Radio)
