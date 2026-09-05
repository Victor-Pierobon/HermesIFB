# Projeto Hermes — Contexto para desenvolvimento

> Sistema acessível de solicitação de embarque assistido no transporte público.
> Este arquivo é o contexto-mestre do projeto. Leia-o inteiro antes de gerar ou alterar código.

---

## 1. O que é o Hermes

O Hermes inverte o fluxo convencional de embarque no ônibus. Hoje o passageiro
precisa **ver** o veículo, reconhecer a linha e sinalizar ao motorista — uma barreira
para pessoas cegas, com baixa visão ou mobilidade reduzida.

No Hermes, a solicitação de embarque é feita **de forma acessível na própria parada**
(botão tátil com retorno por voz, tela em alto contraste, ou aproximação de cartão RFID)
e transmitida **por rádio LoRa** ao ônibus da linha correspondente, que alerta o motorista
com antecedência.

**Dois nós físicos:**
1. **Totem** — instalado na parada. Onde o passageiro interage.
2. **Módulo embarcado** — instalado no ônibus. Recebe a solicitação e alerta o motorista.

Eles conversam por **LoRa ponto-a-ponto em 915 MHz** (NÃO é LoRaWAN — não há gateway
nem servidor de rede; é rádio direto entre os dois nós).

---

## 2. Princípios inegociáveis (regras de projeto)

Estes princípios moldam TODAS as decisões de código:

1. **Privacidade por design (LGPD).** A solicitação NUNCA carrega dado pessoal nem a
   condição do passageiro. Só trafegam identificadores neutros: `req_id`, `parada_id`,
   `linha_id`. Não existe campo "tem deficiência", "tipo de deficiência", nome, nada.
   A privacidade nasce da estrutura do pacote, não de um filtro posterior.

2. **Autonomia do motorista.** Ele recebe apenas informação operacional agregada
   (parada + quantidade de pessoas aguardando). Decide como sempre decidiu.

3. **Sem smartphone.** Nenhuma etapa pode exigir app, cadastro ou conexão de dados
   do usuário. A interface é pública e fica na parada.

4. **Arquitetura em 3 camadas.** A lógica de negócio NÃO pode depender de hardware
   específico. É isso que permite desenvolver com simulador agora e trocar só os drivers
   quando o hardware chegar. **Nunca misture leitura de pino / chamada de rádio dentro
   da camada de aplicação.**

---

## 3. Arquitetura em 3 camadas

```
┌─────────────────────────────────────────────┐
│  APLICAÇÃO  (regra de negócio)              │  ← independe de hardware; 100% testável
│  solicitação · linha/parada · rótulo neutro │
│  contagem de pendentes · máquina de estados │
├─────────────────────────────────────────────┤
│  COMUNICAÇÃO  (protocolo)                    │  ← formato do pacote + handshake
│  interface enviar()/receber()               │     por baixo: rádio real OU mock
├─────────────────────────────────────────────┤
│  HARDWARE / HAL  (drivers)                   │  ← única camada que muda entre
│  botão · RFID · voz · tela · rádio LoRa      │     RPi, ESP32 e simulador
└─────────────────────────────────────────────┘
```

**Regra de ouro:** a camada de Comunicação expõe uma interface abstrata
(`enviar(pacote)` / `receber()`). Existem duas implementações: `radio_lora` (hardware real)
e `radio_mock` (troca mensagens via socket/MQTT, para testar sem rádio). A camada de
Aplicação só conhece a interface, nunca a implementação concreta.

---

## 4. Protocolo LoRa (o contrato entre os nós)

### Formato do pacote — 9 bytes, big-endian

| Campo           | Tipo   | Bytes | Descrição                                   |
|-----------------|--------|-------|---------------------------------------------|
| `parada_id`     | uint16 | 2     | identifica o ponto de parada                |
| `linha_id`      | uint16 | 2     | linha solicitada                            |
| `req_id`        | uint16 | 2     | id neutro da solicitação (usado no ACK)     |
| `qtd_pendentes` | uint8  | 1     | pessoas aguardando embarque naquela parada  |
| `tipo_msg`      | uint8  | 1     | ver enum abaixo                             |
| `crc`           | uint8  | 1     | XOR dos 8 bytes anteriores (integridade)    |

Formato `struct`: `>HHHBBB`. **Nenhum campo revela pessoa ou condição.**

### Enum tipo_msg

| Valor | Nome        | Direção         | Significado                                        |
|-------|-------------|-----------------|----------------------------------------------------|
| 0x01  | `SOLIC`     | totem → ônibus  | nova solicitação de embarque                       |
| 0x02  | `ACK`       | ônibus → totem  | confirmação, com o MESMO `req_id` (dispara a voz)  |
| 0x03  | `HEARTBEAT` | ônibus → totem  | presença/proximidade da linha na área da parada    |

### Handshake

```
TOTEM                             ÔNIBUS
  │   SOLIC (req_id=N)              │
  ├────────────────────────────────►│  filtra: é minha linha?
  │                                  │  incrementa pendentes
  │   ACK (req_id=N)                 │
  │◄────────────────────────────────┤
  │  confirma ao usuário por voz     │
```

- Sem ACK em **X segundos** (parametrizável, começar com 3s): o totem **reenvia**.
- Máximo de **N tentativas** (começar com 3). Esgotado → estado FALHA, avisa o usuário.
- O ônibus só considera pacotes `SOLIC` da **sua própria linha**; descarta os demais.

---

## 5. Máquina de estados do totem

```
        toque/cartão        confirma linha        pacote enviado
OCIOSO ──────────────► SELECAO_LINHA ──────────► ENVIANDO ──────────► AGUARDA_ACK
  ▲                                                  ▲                    │  │
  │ reset                                            │ retry (< N)        │  │ ACK
  │                                                  └────────────────────┘  ▼
  │                                                                      CONFIRMADO
  │◄─────────── volta ao início (timeout) ──────────────────────────────────┘
  │
  └──────────────── FALHA (N tentativas sem ACK) ──────────────────────────┘
```

Estados: `OCIOSO`, `SELECAO_LINHA`, `ENVIANDO`, `AGUARDA_ACK`, `CONFIRMADO`, `FALHA`.
Eventos: `toque()`, `confirma_linha()`, `pacote_enviado()`, `ack_recebido()`, `timeout()`, `reset()`.

Implementar como FSM explícita (enum + transições), NÃO como condicionais espalhados.
A entrada em `CONFIRMADO` é o gancho que dispara o retorno por voz "embarque solicitado".

---

## 6. Modelo de dados

Entidades lógicas (enxutas de propósito):

- **PARADA**: `parada_id` (PK), nome, latitude, longitude, `linhas_atendidas[]`
- **LINHA**: `linha_id` (PK), código (ex.: "0.130"), nome/destino, acessível (bool)
- **SOLICITACAO**: `req_id` (PK), `parada_id` (FK), `linha_id` (FK), timestamp,
  status (`enviada` | `confirmada` | `expirada`)

Para o protótipo, dados de parada/linha podem viver em um arquivo local (JSON/dict).
Não há banco de dados pesado nesta fase.

---

## 7. Stack e bibliotecas

### Totem Versão A — Raspberry Pi 3 (Python)
- **TTS (voz):** `pyttsx3` (offline) ou `espeak-ng` — roda igual no notebook para teste
- **RFID:** `mfrc522` + `spidev` (leitor RC522)
- **GPIO/botão:** `gpiozero`
- **Rádio LoRa:** `adafruit-circuitpython-rfm9x` (SX127x via SPI)
- **Tela alto contraste:** `pygame` ou `tkinter`
- **Testes:** `pytest`

### Totem Versão B + Módulo Embarcado — ESP32 (C++/Arduino)
- **Rádio LoRa:** `sandeepmistry/arduino-LoRa`
- **RFID:** `MFRC522` (miguelbalboa)
- **Display:** `Adafruit_SSD1306` + `Adafruit_GFX` (OLED)
- **Voz econômica:** `DFRobotDFPlayerMini` (áudios MP3 pré-gravados)
- **Ambiente:** PlatformIO (VS Code)

### Desenvolvimento sem hardware (fase atual)
- **Wokwi** — simula ESP32 + botão + OLED + RFID. **NÃO simula rádio LoRa.**
- **Mock LoRa próprio** — dois processos trocando pacotes via socket/MQTT.
  Valida protocolo, handshake e retry SEM rádio físico.
- **Notebook Linux** — roda toda a camada de aplicação e o TTS.

> A linguagem-base para começar é **Python** (camada de aplicação + comunicação +
> mock), porque é onde dá para avançar mais rápido sem hardware. O código ESP32 (C++)
> entra depois, na fase de integração.

---

## 8. Estrutura de pastas alvo

```
hermes/
├── aplicacao/          # camada de negócio (independe de hardware)
│   ├── __init__.py
│   ├── solicitacao.py  # geração de req_id, rótulo neutro
│   ├── pendentes.py    # contagem por parada/linha
│   └── estados.py      # máquina de estados do totem (FSM)
├── comunicacao/        # protocolo LoRa (real + mock)
│   ├── __init__.py
│   ├── pacote.py       # (des)serialização dos 9 bytes + CRC
│   ├── radio.py        # interface abstrata enviar()/receber()
│   ├── radio_mock.py   # implementação via socket/MQTT
│   └── radio_lora.py   # implementação real (SX127x) — fase de hardware
├── hardware/           # HAL — a única camada que muda
│   ├── totem_rpi/      # versão A (Raspberry Pi)
│   ├── totem_esp32/    # versão B (econômica, C++/PlatformIO)
│   └── embarcado/      # módulo do ônibus (C++/PlatformIO)
├── dados/
│   ├── paradas.json
│   └── linhas.json
├── testes/             # pytest
│   ├── test_pacote.py
│   └── test_estados.py
└── docs/               # arquitetura, medições, relatório
```

---

## 9. Convenções

- **Idioma:** código, nomes de variáveis e comentários em **português** (o domínio é
  em português; mantém coerência com o edital e a documentação).
- **Estilo Python:** PEP 8, type hints sempre que possível, funções pequenas e testáveis.
- **Testes primeiro nas camadas puras:** todo módulo de `aplicacao/` e `comunicacao/`
  nasce com teste em `testes/`. Meta: rodar `pytest` verde a cada commit.
- **Sem dependência de hardware nas camadas puras:** se um import de `aplicacao/` ou
  `comunicacao/pacote.py` puxar `RPi.GPIO`, `spidev` ou similar, está errado.
- **Commits pequenos e descritivos**, em português.

---

## 10. Onde começar (ordem de implementação)

Fase atual: **software puro, sem hardware.** Seguir esta ordem:

1. **`comunicacao/pacote.py`** — serialização/desserialização dos 9 bytes + CRC.
   Começar por aqui: é o contrato de que tudo depende. Escrever `testes/test_pacote.py`
   junto (ida-e-volta, CRC inválido, tamanho errado).

2. **`aplicacao/estados.py`** — a FSM do totem (seção 5). Testar cada transição em
   `testes/test_estados.py` (toque→seleção, timeout com retry, N tentativas→FALHA).

3. **`aplicacao/solicitacao.py` e `pendentes.py`** — geração de `req_id` neutro e
   contagem de pendentes por parada/linha.

4. **`comunicacao/radio.py` + `radio_mock.py`** — interface abstrata e o mock que
   liga totem e ônibus por socket local.

5. **Simulação ponta-a-ponta** — um script que instancia totem + ônibus usando o mock,
   dispara uma solicitação e valida o ciclo completo SOLIC → ACK → confirmação.

6. **(Paralelo) Wokwi** — projeto "olá mundo" ESP32 + botão + OLED, para ganhar
   familiaridade antes do hardware chegar.

Só depois, quando o hardware chegar: implementar `radio_lora.py` e os projetos
PlatformIO em `hardware/`, trocando APENAS a camada de HAL.

---

## 11. Contexto do desenvolvedor

- Projeto de bolsa (Edital 18/2026 — PRPI/IFB, Campus Taguatinga), prazo de **4 meses**.
- Meta de maturidade: sair de **TRL 2** e chegar a **TRL 4** (protótipo integrado,
  validado em ambiente controlado). NÃO se pretende operação em serviço regular.
- Desenvolvedor com **pouca experiência em ESP32 e LoRa** — prefira soluções simples,
  bibliotecas maduras e explicações quando introduzir um conceito novo de hardware/rádio.
- O maior risco técnico do projeto é o **LoRa** (só se revela no hardware). Por isso a
  estratégia é validar TODA a lógica de comunicação por mock antes do rádio físico.
