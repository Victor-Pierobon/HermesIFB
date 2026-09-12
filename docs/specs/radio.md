# Spec — `comunicacao/radio.py`

> Ver HERMES.md seção 3 ("regra de ouro": Comunicação expõe interface
> abstrata `enviar()`/`receber()`; Aplicação só conhece a interface, nunca
> a implementação concreta) e seção 8 (estrutura de pastas: `radio.py` é a
> interface, `radio_mock.py` e `radio_lora.py` são as implementações).

## Objetivo

Definir o contrato único que qualquer transporte (mock por socket, LoRa
real) precisa cumprir para que a camada de aplicação (FSM do totem,
integração) funcione sem saber qual dos dois está por trás.

Não há lógica aqui — é só o formato. Por isso é um `Protocol` (tipagem
estrutural do `typing`), não uma classe base com `ABC`/`abstractmethod`:
qualquer objeto com os métodos certos serve, sem precisar herdar de nada.
Menos código, mesma garantia de tipo.

## API pública

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Radio(Protocol):
    def enviar(self, pacote: Pacote) -> None: ...
    def receber(self, timeout: float | None = None) -> Pacote | None: ...
```

- `enviar(pacote)`: transmite um `Pacote` (já validado por
  `comunicacao/pacote.py`). Não retorna nada — é fogo-e-esquece, o
  handshake/retry é responsabilidade de quem chama (`aplicacao/estados.py`
  + integração), não do transporte.
- `receber(timeout=None)`: espera até `timeout` segundos por um pacote
  válido; retorna `None` se nada chegar a tempo (ou se o que chegou estava
  corrompido — CRC inválido é tratado como "nada chegou", não como erro).
  `timeout=None` bloqueia indefinidamente. Esse polling com timeout é o
  que permite ao relógio real (fora da FSM, HERMES.md seção 5) decidir
  quando chamar `totem.timeout()`.

## Casos de teste

| # | Given | When | Then |
|---|-------|------|------|
| 1 | Uma instância de `RadioMock` (ver `radio_mock.md`) | `isinstance(instancia, Radio)` | `True` — confirma que a implementação cumpre o Protocol sem herança explícita |

## Fora de escopo desta spec

- Qualquer implementação concreta (`radio_mock.py`, `radio_lora.py`).
- Filtragem por `linha_id` (o ônibus só processa `SOLIC` da própria linha,
  HERMES.md seção 4) — isso é decisão de aplicação, não do transporte:
  `receber()` entrega qualquer pacote válido que chegou, não filtra.
- Retry, contagem de tentativas, handshake — tudo isso já é coberto por
  `aplicacao/estados.py` (`docs/specs/estados.md`).
