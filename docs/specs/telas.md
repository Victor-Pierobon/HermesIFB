# Spec — Telas (Totem e Módulo Embarcado)

> Base visual/textual de cada tela, amarrada aos eventos e estados já
> definidos em `docs/specs/estados.md` (FSM do totem) e à seção 2 do
> HERMES.md (autonomia do motorista, privacidade). Não há código de tela
> ainda — esta spec é o contrato para quando a camada HARDWARE for escrita
> (`hardware/totem_rpi`, `hardware/totem_esp32`, `hardware/embarcado`).

## Decisão de interação (pré-requisito desta spec)

Seleção de linha usa **RFID com fallback por botão**:

- Cartão RFID é vinculado a **uma linha fixa** do passageiro. Aproximar o
  cartão dispara `toque()` seguido imediatamente de `confirma_linha()` — a
  tela `SELECAO_LINHA` aparece só como confirmação rápida, não como menu.
- Sem cartão, o botão tátil **cicla** entre as linhas atendidas na parada
  (`linhas_atendidas` de `PARADA`, seção 6 do HERMES.md), com locução a
  cada toque. Um toque longo (ou segundo botão dedicado) confirma a linha
  anunciada por último.

## Regras gerais de acessibilidade (herdadas do HERMES.md)

- **Alto contraste sempre**: fundo preto, texto branco ou amarelo, fonte
  grande. Nunca depender só de cor para transmitir estado (usar também
  ícone/forma).
- **Redundância modal**: toda mudança de tela relevante para o usuário é
  acompanhada de fala equivalente. A tela nunca é a única fonte de
  informação — quem não enxerga precisa entender o fluxo só pelo áudio.
- **Zero dado pessoal na tela**: só aparecem `linha_id`/código da linha,
  nome da parada, contagem de pendentes e status da solicitação. Nunca
  nome, condição ou identificador do passageiro (princípio 1 do HERMES.md).
- **Duas variantes de hardware, mesmo conteúdo:**
  - **RPi (Versão A)** — tela cheia (pygame/tkinter), texto completo em
    frases.
  - **ESP32 (Versão B)** — OLED SSD1306 128×64, ~4 linhas de texto curto;
    o grosso da informação vai por áudio pré-gravado (DFPlayerMini), a tela
    só reforça o essencial.

---

## Totem — tela e voz por estado da FSM

| Estado | Tela RPi (texto completo) | Tela OLED (curto, 128×64) | Voz | Interação esperada |
|---|---|---|---|---|
| `OCIOSO` | "APROXIME O CARTÃO\nOU TOQUE NO BOTÃO" | `APROXIME O\nCARTAO OU\nTOQUE` | silêncio (espera) | aproximar RFID ou tocar botão |
| `SELECAO_LINHA` (via botão, ciclando) | "LINHA 0.130\nTaguatinga Centro\n(toque = próxima / segure = confirmar)" | `L.0.130\nTAGUATINGA\nCTR` | "Linha 0 ponto 130, Taguatinga Centro. Toque para próxima linha, segure para confirmar." a cada ciclo | tocar (próxima) ou segurar (confirma) |
| `SELECAO_LINHA` (via RFID, transição rápida) | "LINHA 0.130 confirmada" (pisca ~1s) | `L.0.130\nOK` | "Linha 0 ponto 130 confirmada." | nenhuma (auto-avança para `ENVIANDO`) |
| `ENVIANDO` | "ENVIANDO SOLICITAÇÃO..." + spinner | `ENVIANDO...` | "Solicitando embarque." | aguardar |
| `AGUARDA_ACK` | "AGUARDANDO CONFIRMAÇÃO\nTentativa {tentativas} de {N}" | `AGUARDANDO\n{tentativas}/{N}` | silêncio na 1ª tentativa; "Ainda tentando..." a partir da 2ª | aguardar |
| `CONFIRMADO` | "✓ EMBARQUE SOLICITADO\nLinha 0.130" | `OK!\nEMBARQUE\nSOLICITADO` | **"Embarque solicitado. Aguarde o ônibus da linha 0.130."** (gancho `ao_confirmar`, HERMES.md seção 5) | aguardar o ônibus |
| `FALHA` | "✗ NÃO FOI POSSÍVEL CONFIRMAR\nTente novamente" | `FALHOU.\nTENTE\nDE NOVO` | "Não foi possível confirmar. Tente novamente." | nenhuma — integração chama `reset()` automaticamente após alguns segundos (volta a `OCIOSO`, conforme diagrama da seção 5 do HERMES.md) |

Notas:
- `{tentativas}` e `{N}` vêm de `Totem.tentativas` / `max_tentativas`
  (`aplicacao/estados.py`) — a tela só lê essas propriedades, nunca decide
  retry.
- O áudio da versão ESP32 é pré-gravado (arquivos `.mp3` no
  `DFPlayerMini`); a tela OLED é só reforço visual do mesmo estado, não
  precisa repetir a frase inteira.

---

## Módulo embarcado (ônibus) — telas por evento

O módulo embarcado não roda a FSM do totem — ele reage a pacotes recebidos
e mantém uma contagem de pendentes por parada, para a **sua própria
linha** (HERMES.md seção 4: "o ônibus só considera pacotes `SOLIC` da sua
própria linha"). Modelo de tela:

| Situação | Tela (OLED, todas as versões usam a mesma) | Voz/alerta sonoro | Efeito colateral |
|---|---|---|---|
| Repouso — nenhuma parada com pendentes | `LINHA 0.130\nnenhum pedido` | silêncio | — |
| `SOLIC` recebido da própria linha | `PARADA Vila A\n+1 (total: {n})` pisca 2s, depois entra na lista | beep curto (buzzer) — sem voz, o motorista só precisa notar, não ouvir frase longa (princípio 2: autonomia do motorista) | envia `ACK` com o mesmo `req_id`; incrementa pendentes da parada |
| Lista de paradas com pendentes > 0 à frente | `Vila A: 2\nCentro: 1` (uma linha por parada, ordenado pela rota) | — | — |
| `SOLIC` de outra linha (descartado) | sem mudança de tela | sem alerta | pacote ignorado (regra da seção 4) |
| `HEARTBEAT` enviado | sem mudança visível (é saída, não entrada) | — | — |

Notas:
- Nenhuma tela do embarcado mostra `req_id` ou qualquer coisa que
  identifique uma solicitação individual — só nome da parada e contagem
  agregada, reforçando o princípio 1 (privacidade) e 2 (autonomia:
  motorista decide, não é instruído a agir).
- Quando o ônibus passa pela parada e os pendentes daquela parada devem
  zerar, o gatilho (embarque físico observado pelo motorista, ou um botão
  "limpar parada") fica **fora de escopo desta spec** — pertence à spec de
  `aplicacao/pendentes.py`, ainda não escrita.

---

## Fora de escopo desta spec

- Implementação em pygame/tkinter (RPi) ou biblioteca OLED/DFPlayerMini
  (ESP32) — isso é código de `hardware/`, vem depois.
- Lógica de quando zerar pendentes de uma parada no embarcado (fica em
  `aplicacao/pendentes.py`).
- Menu de configuração/pareamento de linha do totem (qual linha cada
  totem físico atende) — assume-se que isso é configuração estática por
  totem, não uma tela do fluxo do passageiro.
- Multilíngue — todas as telas/vozes desta fase são em português (convenção
  do projeto, HERMES.md seção 9).
