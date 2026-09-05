"""Serialização do pacote LoRa (9 bytes). Ver docs/specs/pacote.md."""
from __future__ import annotations

import functools
import operator
import struct
from dataclasses import dataclass
from enum import IntEnum

_FORMATO_CORPO = ">HHHBB"  # parada_id, linha_id, req_id, qtd_pendentes, tipo_msg
TAMANHO_PACOTE = struct.calcsize(_FORMATO_CORPO) + 1  # + 1 byte de crc


class TipoMsg(IntEnum):
    SOLIC = 0x01
    ACK = 0x02
    HEARTBEAT = 0x03


class PacoteInvalidoError(ValueError):
    """Pacote com tamanho, CRC ou campo fora do intervalo válido."""


def _crc(corpo: bytes) -> int:
    return functools.reduce(operator.xor, corpo, 0)


@dataclass(frozen=True)
class Pacote:
    parada_id: int
    linha_id: int
    req_id: int
    qtd_pendentes: int
    tipo_msg: TipoMsg

    def empacotar(self) -> bytes:
        try:
            tipo_msg = TipoMsg(self.tipo_msg)
            corpo = struct.pack(
                _FORMATO_CORPO,
                self.parada_id,
                self.linha_id,
                self.req_id,
                self.qtd_pendentes,
                tipo_msg,
            )
        except (struct.error, ValueError) as erro:
            raise PacoteInvalidoError(str(erro)) from erro
        return corpo + bytes([_crc(corpo)])


def desempacotar(dados: bytes) -> Pacote:
    if len(dados) != TAMANHO_PACOTE:
        raise PacoteInvalidoError(
            f"tamanho esperado {TAMANHO_PACOTE}, recebido {len(dados)}"
        )
    corpo, crc_recebido = dados[:-1], dados[-1]
    if _crc(corpo) != crc_recebido:
        raise PacoteInvalidoError("CRC inválido")
    parada_id, linha_id, req_id, qtd_pendentes, tipo_msg = struct.unpack(
        _FORMATO_CORPO, corpo
    )
    try:
        tipo_msg = TipoMsg(tipo_msg)
    except ValueError as erro:
        raise PacoteInvalidoError(str(erro)) from erro
    return Pacote(parada_id, linha_id, req_id, qtd_pendentes, tipo_msg)
