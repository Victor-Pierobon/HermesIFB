# Spec — `comunicacao/radio_mock.py`

> Ver HERMES.md seção 7 ("Mock LoRa próprio — dois processos trocando
> pacotes via socket/MQTT. Valida protocolo, handshake e retry SEM rádio
> físico") e `docs/specs/radio.md` (contrato `Radio` que esta classe
> implementa).

## Objetivo

Implementação de `Radio` que liga totem e ônibus por **socket UDP em
loopback/rede local**, para testar todo o protocolo (pacote, handshake,
retry) sem hardware de rádio. UDP porque LoRa também é sem conexão e sem
garantia de entrega — usar TCP esconderia justamente os casos que o
protocolo precisa tratar (pacote perdido = sem ACK = retry).

Cada nó (totem ou ônibus) roda um `RadioMock` apontando para o endereço do
outro. Para o protótipo (um totem + um ônibus, TRL 2→4), unicast
ponto-a-ponto é suficiente — ver "Fora de escopo" para o caminho de
múltiplos totens.

## API pública

```python
class RadioMock:
    def __init__(
        self,
        endereco_local: tuple[str, int],
        endereco_remoto: tuple[str, int],
    ) -> None: ...

    def enviar(self, pacote: Pacote) -> None: ...
    def receber(self, timeout: float | None = None) -> Pacote | None: ...
    def fechar(self) -> None: ...

    def __enter__(self) -> "RadioMock": ...
    def __exit__(self, *exc_info: object) -> None: ...
```

Comportamento:

- `__init__` cria um socket UDP (`socket.SOCK_DGRAM`) e faz `bind` em
  `endereco_local`. `endereco_remoto` é para onde `enviar()` manda.
- `enviar(pacote)`: `pacote.empacotar()` (de `comunicacao/pacote.py`) e
  `sendto` para `endereco_remoto`. Deixa `PacoteInvalidoError` de
  `empacotar()` propagar — mandar um pacote inválido é bug de quem chama,
  não algo para o transporte engolir.
- `receber(timeout=None)`: `settimeout(timeout)` no socket, `recvfrom`,
  tenta `desempacotar()`. Dois casos viram `None` (indistinguíveis de
  propósito, como no rádio real): nada chegou a tempo (`socket.timeout`)
  ou chegou lixo/CRC inválido (`PacoteInvalidoError`).
- `fechar()`/context manager: fecha o socket. Usar como
  `with RadioMock(...) as radio:` para garantir liberação da porta.

## Casos de teste

| # | Given | When | Then |
|---|-------|------|------|
| 1 | Dois `RadioMock` em loopback, `A` local=porta X remoto=porta Y, `B` local=porta Y remoto=porta X | `A.enviar(pacote)` | `B.receber(timeout=1)` retorna um `Pacote` igual ao enviado |
| 2 | Um `RadioMock` sozinho, nada enviado para ele | `receber(timeout=0.1)` | Retorna `None` dentro do timeout (não bloqueia indefinidamente) |
| 3 | Bytes corrompidos enviados direto no socket UDP (bypassando `enviar()`) | `receber(timeout=1)` no lado receptor | Retorna `None` (CRC inválido tratado como "nada chegou", não levanta `PacoteInvalidoError`) |
| 4 | `A` chama `enviar()` três vezes seguidas com pacotes diferentes | `B` chama `receber()` três vezes | Recebe os três pacotes, na ordem de envio |
| 5 | `with RadioMock(...) as radio: ...` | bloco termina | Socket fechado — abrir um novo `RadioMock` no mesmo `endereco_local` não levanta "address already in use" |

## Fora de escopo desta spec

- **Múltiplos totens para um ônibus.** O protótipo é ponto-a-ponto
  (unicast). Simular N totens exigiria trocar o socket UDP unicast por
  broadcast/multicast — troca isolada dentro de `RadioMock`, a interface
  `Radio` (`enviar`/`receber`) não muda. Adiado até haver necessidade real
  de testar mais de um totem simultâneo.
- **MQTT.** HERMES.md cita como alternativa, mas socket UDP já cobre o
  objetivo (testar sem rádio físico) com zero dependência nova — ladder de
  simplicidade: stdlib resolve, não precisa de broker.
- Filtragem por `linha_id`, retry, contagem de tentativas — tudo isso é
  `aplicacao/estados.py` + integração, não deste transporte.
- `radio_lora.py` (implementação real com SX127x) — fase de hardware,
  spec própria quando chegar a hora (HERMES.md seção 10).
