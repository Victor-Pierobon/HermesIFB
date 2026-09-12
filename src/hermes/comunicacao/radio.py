"""Interface abstrata de transporte. Ver docs/specs/radio.md."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from hermes.comunicacao.pacote import Pacote


@runtime_checkable
class Radio(Protocol):
    def enviar(self, pacote: Pacote) -> None: ...
    def receber(self, timeout: float | None = None) -> Pacote | None: ...
