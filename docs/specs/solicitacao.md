# Spec — `aplicacao/solicitacao.py`

> Ver HERMES.md seção 6 (modelo `SOLICITACAO`) e seção 1 (privacidade por
> design). Camada de aplicação: gera e transiciona o objeto que representa
> um pedido de embarque — não conhece rádio, pacote binário nem hardware.

## Objetivo

Modelar `SOLICITACAO` (HERMES.md seção 6) como um valor imutável com um
`req_id` neutro e um ciclo de vida de status (`enviada` → `confirmada` ou
`expirada`). É a estrutura que, por construção, garante o princípio 1
("a privacidade nasce da estrutura do pacote, não de um filtro posterior"):
não existe campo aqui para nome, condição ou qualquer dado do passageiro —
só `req_id`, `parada_id`, `linha_id`, `criado_em`, `status`.

## Relação com outros módulos

- `req_id` gerado aqui é o mesmo campo `req_id` de `comunicacao/pacote.py`
  (uint16, 0–65535) — este módulo não serializa nada, só garante que o
  valor gerado é válido para caber lá.
- Este módulo **não decide** quando a FSM do totem (`aplicacao/estados.py`)
  avança. Quem orquestra (`toque()` → `criar_solicitacao()` →
  `confirma_linha()` → ... → `ack_recebido()` → `confirmar()`) é a camada
  de integração, fora de escopo aqui.
- Não conta pendentes (isso é `aplicacao/pendentes.py`).

## API pública

```python
class StatusSolicitacao(Enum):
    ENVIADA = auto()
    CONFIRMADA = auto()
    EXPIRADA = auto()

class SolicitacaoInvalidaError(Exception): ...

@dataclass(frozen=True)
class Solicitacao:
    req_id: int
    parada_id: int
    linha_id: int
    criado_em: datetime
    status: StatusSolicitacao = StatusSolicitacao.ENVIADA

def criar_solicitacao(
    parada_id: int,
    linha_id: int,
    *,
    gerador_req_id: Callable[[], int] | None = None,
    agora: Callable[[], datetime] | None = None,
) -> Solicitacao: ...

def confirmar(solicitacao: Solicitacao) -> Solicitacao: ...
def expirar(solicitacao: Solicitacao) -> Solicitacao: ...
```

Notas de design:

- `Solicitacao` é **imutável** (`frozen=True`, mesmo padrão de `Pacote` em
  `comunicacao/pacote.py`). `confirmar()`/`expirar()` retornam uma **nova**
  instância com `status` atualizado — nunca mutam a original. Mantém a
  camada de aplicação livre de efeitos colaterais escondidos.
- `gerador_req_id` e `agora` são injetáveis (padrão igual ao "a FSM não
  tem timer próprio" de `estados.md`) só para permitir teste determinístico.
  Em produção, os padrões são `random.randint(0, 65535)` e
  `datetime.now()`.
- `req_id` fora do intervalo 0–65535 retornado por um `gerador_req_id`
  customizado deve levantar `SolicitacaoInvalidaError` — este módulo não
  deixa passar um `req_id` que `pacote.py` rejeitaria depois.
- `confirmar()`/`expirar()` só são válidos a partir de `ENVIADA`. Chamar
  em uma `Solicitacao` já `CONFIRMADA` ou `EXPIRADA` levanta
  `SolicitacaoInvalidaError` (mesma filosofia de falha explícita da FSM:
  "decisão confirmada: falha explícita em vez de ignorar silenciosamente").

## Casos de teste

| # | Given | When | Then |
|---|-------|------|------|
| 1 | `parada_id=1, linha_id=130` | `criar_solicitacao(1, 130)` | `Solicitacao` com `parada_id==1`, `linha_id==130`, `status==ENVIADA`, `0 <= req_id <= 65535` |
| 2 | `gerador_req_id=lambda: 42` | `criar_solicitacao(1, 130, gerador_req_id=...)` | `req_id == 42` (permite teste determinístico) |
| 3 | `agora=lambda: datetime(2026, 1, 1)` | `criar_solicitacao(1, 130, agora=...)` | `criado_em == datetime(2026, 1, 1)` |
| 4 | `gerador_req_id=lambda: 70000` (fora do intervalo) | `criar_solicitacao(...)` | Levanta `SolicitacaoInvalidaError` |
| 5 | `Solicitacao` com `status=ENVIADA` | `confirmar(sol)` | Nova `Solicitacao` com `status==CONFIRMADA`; demais campos iguais aos originais; objeto `sol` original inalterado |
| 6 | `Solicitacao` com `status=ENVIADA` | `expirar(sol)` | Nova `Solicitacao` com `status==EXPIRADA`; demais campos iguais |
| 7 | `Solicitacao` com `status=CONFIRMADA` | `confirmar(sol)` novamente | Levanta `SolicitacaoInvalidaError` |
| 8 | `Solicitacao` com `status=EXPIRADA` | `confirmar(sol)` ou `expirar(sol)` | Levanta `SolicitacaoInvalidaError` |
| 9 | Duas chamadas a `criar_solicitacao` sem `gerador_req_id` fixo | comparar os dois `req_id` | Nenhuma garantia de unicidade global é feita por este módulo (ver "Fora de escopo") — só se testa que ambos caem no intervalo válido |

## Fora de escopo desta spec

- **Unicidade de `req_id` entre totens concorrentes.** Um totem físico só
  tem uma solicitação em voo por vez (a FSM é single-flight), então
  colisão só importaria entre *totens diferentes* transmitindo ao mesmo
  tempo dentro do alcance do mesmo ônibus. Prototipagem (TRL 2→4, HERMES.md
  seção 11) aceita a chance de colisão de 1/65536 por ora; se isso doer na
  integração, a correlação de ACK deve usar `(parada_id, req_id)` juntos
  (responsabilidade de `comunicacao/radio.py`, não deste módulo).
- Orquestração com a FSM do totem (`aplicacao/estados.py`) — fica na
  camada de integração/script principal.
- Conversão para `Pacote` (empacotamento) — fica em `comunicacao/pacote.py`,
  chamado pela integração.
- Persistência (a `Solicitacao` vive em memória durante o ciclo de vida do
  pedido; não há banco nesta fase, HERMES.md seção 6).
