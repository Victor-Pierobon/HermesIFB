# Spec — `aplicacao/pendentes.py`

> Ver HERMES.md seção 6 (contagem de pendentes por parada/linha) e
> `docs/specs/telas.md` (onde a contagem aparece: campo `qtd_pendentes` do
> totem e a lista "Vila A: 2 / Centro: 1" do módulo embarcado).

## Objetivo

Contador puro de pessoas aguardando embarque, chaveado por
`(parada_id, linha_id)`. É o mesmo módulo usado nas duas pontas do
sistema, com chaves diferentes conforme quem chama:

- **No totem**: `parada_id` é fixo (o totem só existe em um lugar), e o
  contador varia por `linha_id` — uma parada pode atender várias linhas
  (`linhas_atendidas[]`, HERMES.md seção 6), cada uma com sua própria fila.
  O valor lido aqui é o que vai no campo `qtd_pendentes` do `Pacote` SOLIC
  (`comunicacao/pacote.py`) enviado para aquela linha.
- **No módulo embarcado**: `linha_id` é fixo (a própria linha do ônibus),
  e o contador varia por `parada_id` — monta a lista de paradas à frente
  com gente esperando (tela "Vila A: 2 / Centro: 1" de `telas.md`).

Por isso a chave é sempre o par `(parada_id, linha_id)`, mesmo que, em
cada ponta, uma das duas metades da chave seja constante na prática.

## API pública

```python
class ContadorPendentes:
    def __init__(self) -> None: ...

    def incrementar(self, parada_id: int, linha_id: int) -> int: ...
    def decrementar(self, parada_id: int, linha_id: int) -> int: ...
    def total(self, parada_id: int, linha_id: int) -> int: ...
```

- `incrementar`/`decrementar` retornam o novo total após a operação
  (evita uma segunda chamada a `total()` no caller mais comum).
- Par nunca visto antes: `total()` retorna `0`, sem levantar erro (é
  simplesmente "ninguém esperando ali ainda").
- `decrementar` nunca deixa o total negativo: em `0`, `decrementar` é
  no-op e retorna `0`. Contagem física não pode ser negativa; um
  decremento "sobrando" (ex.: dessincronia entre efetivamente embarcou e
  o que o totem contava) não deve virar exceção nem número inválido —
  só fica em zero.
  `# ponytail: clamp silencioso em 0, sem log de inconsistência —
  se isso mascarar bug de contagem na integração, trocar por um
  contador que também expõe "decrementos descartados" para diagnóstico.`

## Casos de teste

| # | Given | When | Then |
|---|-------|------|------|
| 1 | `ContadorPendentes()` novo | `total(1, 130)` | `0` |
| 2 | contador novo | `incrementar(1, 130)` | retorna `1`; `total(1, 130) == 1` |
| 3 | `total(1, 130) == 1` | `incrementar(1, 130)` duas vezes mais | `total(1, 130) == 3` |
| 4 | `total(1, 130) == 3` | `incrementar(1, 200)` (linha diferente, mesma parada) | `total(1, 130)` continua `3`; `total(1, 200) == 1` (pares independentes) |
| 5 | `total(1, 130) == 3` | `incrementar(2, 130)` (parada diferente, mesma linha) | `total(1, 130)` continua `3`; `total(2, 130) == 1` |
| 6 | `total(1, 130) == 3` | `decrementar(1, 130)` | retorna `2`; `total(1, 130) == 2` |
| 7 | `total(1, 130) == 0` | `decrementar(1, 130)` | retorna `0` (não vira negativo) |
| 8 | par nunca incrementado | `decrementar(9, 9)` | retorna `0`, sem erro |

## Fora de escopo desta spec

- **Quando** incrementar/decrementar (gatilhos: nova solicitação enviada,
  embarque fisicamente observado, expiração por timeout) — isso é
  orquestração da camada de integração, ligando eventos da FSM
  (`aplicacao/estados.py`) e de `aplicacao/solicitacao.py` a este contador.
- Persistência entre reinícios do processo (contador vive em memória).
- Ordenar a lista de paradas por distância/rota para a tela do embarcado
  (`telas.md` mostra a lista já ordenada — a ordenação usa dados de rota
  que não pertencem a este módulo).
- Cap em 255 para caber no campo `qtd_pendentes` (uint8) de
  `comunicacao/pacote.py`. Truncar/saturar nesse limite é responsabilidade
  de quem monta o `Pacote`, não deste contador (que deve refletir a
  contagem real, mesmo que > 255 no caso extremo).
