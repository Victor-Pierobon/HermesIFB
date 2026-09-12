# Spec — `aplicacao/estados.py`

> FSM do totem. Ver HERMES.md seção 5. Camada de aplicação: não conhece rádio
> nem hardware, só estado e transições — 100% testável sem I/O.

## Objetivo

Modelar o ciclo de vida de uma solicitação de embarque no totem como uma
máquina de estados explícita, incluindo o retry com limite de tentativas e o
gancho que dispara a confirmação por voz.

## Estados

`OCIOSO`, `SELECAO_LINHA`, `ENVIANDO`, `AGUARDA_ACK`, `CONFIRMADO`, `FALHA`.

## Eventos

`toque()`, `confirma_linha()`, `pacote_enviado()`, `ack_recebido()`,
`timeout()`, `reset()`.

A FSM não tem timer próprio — quem chama `timeout()` é o código que gerencia
o relógio real (fora do escopo desta spec). Isso mantém a FSM pura.

## Tabela de transições

| Estado atual    | Evento          | Condição             | Estado seguinte | Efeito colateral                        |
|-----------------|-----------------|-----------------------|------------------|------------------------------------------|
| `OCIOSO`        | `toque()`       | —                     | `SELECAO_LINHA`  | —                                         |
| `SELECAO_LINHA` | `confirma_linha()` | —                  | `ENVIANDO`       | —                                         |
| `ENVIANDO`      | `pacote_enviado()` | —                  | `AGUARDA_ACK`    | `tentativas += 1`                         |
| `AGUARDA_ACK`   | `ack_recebido()` | —                    | `CONFIRMADO`     | chama `ao_confirmar()` (se houver)        |
| `AGUARDA_ACK`   | `timeout()`     | `tentativas < N`      | `ENVIANDO`       | — (caller reenvia e chama `pacote_enviado()` de novo) |
| `AGUARDA_ACK`   | `timeout()`     | `tentativas >= N`     | `FALHA`          | —                                         |
| `CONFIRMADO`    | `timeout()`     | —                     | `OCIOSO`         | `tentativas = 0`                          |
| **qualquer estado** | `reset()`   | —                     | `OCIOSO`         | `tentativas = 0`                          |

`N` (`max_tentativas`) é parâmetro do construtor, padrão **3** (HERMES.md
seção 4: "começar com 3").

**Qualquer combinação estado+evento fora desta tabela levanta
`TransicaoInvalidaError`** e não altera o estado (decisão confirmada:
falha explícita em vez de ignorar silenciosamente).

## Gancho de voz

Entrar em `CONFIRMADO` é o ponto que dispara "embarque solicitado" por voz
(HERMES.md seção 5). A FSM não fala nem sabe de TTS — recebe um callback
opcional `ao_confirmar: Callable[[], None]` no construtor e o invoca ao
entrar em `CONFIRMADO`. Quem toca o áudio de verdade é a camada de hardware.

## API pública

```python
class Estado(Enum):
    OCIOSO = auto()
    SELECAO_LINHA = auto()
    ENVIANDO = auto()
    AGUARDA_ACK = auto()
    CONFIRMADO = auto()
    FALHA = auto()

class TransicaoInvalidaError(Exception): ...

class Totem:
    def __init__(self, max_tentativas: int = 3,
                 ao_confirmar: Callable[[], None] | None = None): ...

    estado: Estado       # propriedade somente leitura
    tentativas: int      # propriedade somente leitura

    def toque(self) -> None: ...
    def confirma_linha(self) -> None: ...
    def pacote_enviado(self) -> None: ...
    def ack_recebido(self) -> None: ...
    def timeout(self) -> None: ...
    def reset(self) -> None: ...
```

## Casos de teste

| # | Given | When | Then |
|---|-------|------|------|
| 1 | `Totem()` recém-criado | — | `estado == OCIOSO`, `tentativas == 0` |
| 2 | `OCIOSO` | `toque()` | `SELECAO_LINHA` |
| 3 | `SELECAO_LINHA` | `confirma_linha()` | `ENVIANDO` |
| 4 | `ENVIANDO` | `pacote_enviado()` | `AGUARDA_ACK`, `tentativas == 1` |
| 5 | `AGUARDA_ACK` | `ack_recebido()` | `CONFIRMADO`; `ao_confirmar` foi chamado exatamente 1 vez |
| 6 | `AGUARDA_ACK`, `tentativas=1`, `N=3` | `timeout()` | volta a `ENVIANDO` (retry), `tentativas` inalterado |
| 7 | Ciclo enviando→aguarda_ack→timeout repetido até `tentativas == N` | mais um `timeout()` em `AGUARDA_ACK` | `FALHA` |
| 8 | `CONFIRMADO` | `timeout()` | `OCIOSO`, `tentativas == 0` |
| 9 | Cada estado (`SELECAO_LINHA`, `ENVIANDO`, `AGUARDA_ACK`, `CONFIRMADO`, `FALHA`) com `tentativas > 0` | `reset()` | `OCIOSO`, `tentativas == 0` |
| 10 | `OCIOSO` | `ack_recebido()` (evento fora de ordem) | levanta `TransicaoInvalidaError`; estado continua `OCIOSO` |
| 11 | `FALHA` | `reset()` | `OCIOSO` (caso específico pedido na seção 10 do HERMES.md, coberto pela regra geral do caso 9) |

## Fora de escopo desta spec

- Geração/validação de `req_id` (fica em `aplicacao/solicitacao.py`).
- O relógio real que decide quando chamar `timeout()` (fica na integração,
  fora da camada pura).
- Espera com jitter no retry — **pendência desta spec:** o HERMES.md e a
  spec de `pacote.py` já registram que o retry deve usar jitter
  (`3s + aleatório(0, 500ms)`) para evitar colisão entre totens. A FSM em si
  não decide o tempo de espera (isso é do relógio real, fora de escopo), mas
  quem chama `timeout()` deve aplicar esse jitter. Repassar essa pendência
  para a spec de `radio_mock.py` / integração, onde o timer de fato mora.
