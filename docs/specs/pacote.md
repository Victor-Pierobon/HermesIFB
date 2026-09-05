# Spec — `comunicacao/pacote.py`

> Contrato de serialização do pacote LoRa. Ver HERMES.md seção 4 para o
> protocolo completo. Esta spec detalha o suficiente para escrever os testes
> antes da implementação.

## Objetivo

Converter entre uma estrutura de dados em memória (`Pacote`) e os 9 bytes
big-endian trocados entre totem e ônibus, com detecção de corrupção (CRC) e
de valores fora do intervalo permitido pelo formato.

## Formato binário

`>HHHBBB` (9 bytes, big-endian):

| Campo           | Tipo   | Intervalo válido | Bytes |
|-----------------|--------|-------------------|-------|
| `parada_id`     | uint16 | 0–65535           | 2     |
| `linha_id`      | uint16 | 0–65535           | 2     |
| `req_id`        | uint16 | 0–65535           | 2     |
| `qtd_pendentes` | uint8  | 0–255             | 1     |
| `tipo_msg`      | uint8  | um dos valores do enum `TipoMsg` | 1 |
| `crc`           | uint8  | XOR dos 8 bytes anteriores | 1 |

## Enum `TipoMsg`

`SOLIC = 0x01`, `ACK = 0x02`, `HEARTBEAT = 0x03`. Qualquer outro valor de
`tipo_msg` é inválido.

## API pública

```python
class TipoMsg(IntEnum): ...

class PacoteInvalidoError(ValueError): ...

@dataclass(frozen=True)
class Pacote:
    parada_id: int
    linha_id: int
    req_id: int
    qtd_pendentes: int
    tipo_msg: TipoMsg

    def empacotar(self) -> bytes: ...

def desempacotar(dados: bytes) -> Pacote: ...
```

`PacoteInvalidoError` é a **única** exceção que este módulo levanta — todo
erro de validação (tamanho, CRC, campo fora do intervalo, `tipo_msg`
desconhecido) é normalizado para ela. Quem chama este módulo nunca precisa
capturar `struct.error` ou `ValueError` de outro lugar.

## Casos de teste

| # | Given | When | Then |
|---|-------|------|------|
| 1 | Um `Pacote` válido qualquer | `empacotar()` seguido de `desempacotar()` | Retorna um `Pacote` igual ao original (round-trip) |
| 2 | Um `Pacote` válido empacotado | 1 byte do CRC é alterado | `desempacotar()` levanta `PacoteInvalidoError` |
| 3 | Bytes de tamanho ≠ 9 | `desempacotar(dados)` | Levanta `PacoteInvalidoError` |
| 4 | `parada_id=65536` (ou qualquer campo uint16 > 65535, ou negativo) | `Pacote(...).empacotar()` | Levanta `PacoteInvalidoError` |
| 5 | `qtd_pendentes=256` (ou qualquer campo uint8 > 255, ou negativo) | `Pacote(...).empacotar()` | Levanta `PacoteInvalidoError` |
| 6 | `tipo_msg=0x99` (fora do enum) | `Pacote(...).empacotar()` | Levanta `PacoteInvalidoError` |
| 7 | 9 bytes com `tipo_msg` fora do enum, mas CRC correto para esses bytes | `desempacotar(dados)` | Levanta `PacoteInvalidoError` (CRC bater não valida o conteúdo semântico) |
| 8 | Cada valor de `TipoMsg` (`SOLIC`, `ACK`, `HEARTBEAT`) | round-trip | Preserva o valor corretamente |

## Fora de escopo desta spec

- Envio/recebimento por rádio ou mock (fica em `radio.py` / `radio_mock.py`).
- Geração de `req_id` (fica em `aplicacao/solicitacao.py`).
- Retry/timeout do handshake (fica em `aplicacao/estados.py`). **Pendência
  registrada para a spec de `estados.py`:** o retry deve usar espera com
  jitter (ex.: `3s + aleatório(0, 500ms)`) em vez de intervalo fixo, para
  reduzir colisão quando múltiplos totens reenviam ao mesmo tempo (LoRa
  ponto-a-ponto não tem coordenação central — ver HERMES.md seção 11).
