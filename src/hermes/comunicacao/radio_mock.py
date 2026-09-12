"""Mock de rádio via socket UDP. Ver docs/specs/radio_mock.md."""
from __future__ import annotations

import socket

from hermes.comunicacao.pacote import Pacote, PacoteInvalidoError, desempacotar

_TAMANHO_BUFFER = 4096  # folga acima dos 9 bytes do pacote p/ não truncar lixo no teste de CRC


class RadioMock:
    def __init__(
        self,
        endereco_local: tuple[str, int],
        endereco_remoto: tuple[str, int],
    ) -> None:
        self._remoto = endereco_remoto
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.bind(endereco_local)

    def enviar(self, pacote: Pacote) -> None:
        self._socket.sendto(pacote.empacotar(), self._remoto)

    def receber(self, timeout: float | None = None) -> Pacote | None:
        self._socket.settimeout(timeout)
        try:
            dados, _ = self._socket.recvfrom(_TAMANHO_BUFFER)
        except socket.timeout:
            return None
        try:
            return desempacotar(dados)
        except PacoteInvalidoError:
            return None

    def fechar(self) -> None:
        self._socket.close()

    def __enter__(self) -> RadioMock:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.fechar()
