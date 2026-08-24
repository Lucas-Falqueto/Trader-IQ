# Plano de Implementação — Estratégia "Limitação de Preço e Primeiro Registro"

> Baseado no PDF `704065513-9-Limitacao-do-preco-e-primeiro-registro.pdf`.
> Regras seguidas (CLAUDE.md): mudanças cirúrgicas (módulo novo, zero alteração no bot atual), simplicidade primeiro, suposições explícitas, critérios de sucesso verificáveis.

---

## 0. Escopo e restrições de arquitetura

- **Nenhum arquivo existente do bot é tocado.** Tudo entra em um pacote novo, isolado.
- O módulo é **puro**: recebe uma lista de candles → devolve sinais/estruturas de dados. Não conhece corretora, WebSocket, ordens, nem estado do bot.
- Quem conecta isso à fonte de dados real e à execução é o outro agente — este plano entrega a lógica e a interface, não a integração.
- Estrutura sugerida (nova pasta, não conflita com nada):

```
price_limit_strategy/
├── __init__.py
├── models.py          # Candle, Lote, Channel, Signal (dataclasses)
├── candle_utils.py     # funções puras sobre candles (corpo, pavio, cor, overlap)
├── lote_detection.py   # detecção de "lote" e vela de comando
├── limit_type1.py       # canal de referência tipo 1 (rompimento)
├── limit_type2.py       # canal de referência tipo 2 (segunda vela / DDT)
├── first_register.py    # primeiros registros (3 subtipos)
├── signal_engine.py     # combina tudo -> sinal final de alta confiança
└── tests/
    └── test_fixtures.py  # candles extraídos manualmente dos prints do PDF
```

---

## 1. Modelo de dados (`models.py`)

```python
@dataclass
class Candle:
    open: float
    high: float
    low: float
    close: float
    timestamp: int  # ou datetime

    @property
    def is_bullish(self) -> bool: return self.close >= self.open

    @property
    def body_top(self) -> float: return max(self.open, self.close)

    @property
    def body_bottom(self) -> float: return min(self.open, self.close)

    @property
    def upper_wick(self) -> float: return self.high - self.body_top

    @property
    def lower_wick(self) -> float: return self.body_bottom - self.low
```

`Lote`, `ReferenceChannel`, `PriceLimit` e `Signal` como dataclasses simples (definidos na seção 3–6, criados só quando a lógica estiver fechada — não especular campo que não vai ser usado, conforme regra de simplicidade).

---

## 2. Glossário — tradução dos termos do PDF para regras técnicas

O documento usa jargão informal/visual. Abaixo, minha interpretação de cada termo com o nível de confiança. **Itens marcados `[CONFIRMAR]` são suposições que o outro agente deveria validar com quem escreveu o material antes de codar a versão final** — não travam o plano, mas travam a precisão da implementação.

| Termo do PDF | Interpretação técnica |
|---|---|
| **Lote** | Um par de candles (ou pequena sequência) que forma um bloco de preço com pavio de rejeição na "abertura" do movimento — equivalente a um *order block* simples. |
| **Pavio na abertura** | A primeira vela do lote deixa um pavio (rejeição) no início do movimento, antes do corpo continuar na direção. |
| **Rompimento + continuação** | Preço rompe (fecha além de) o topo/fundo do lote, e a vela seguinte fecha na mesma direção (confirmação, evita rompimento falso). |
| **Canal de referência** | Faixa de preço = [pavio da vela de rompimento, pavio da vela de continuação] (linha superior e inferior). É a "zona" onde o preço deve tocar depois. |
| **Primeira liquidez** | Primeiro toque do preço, em retração, dentro do canal de referência após o rompimento. |
| **Limite de preço ativado** | Depois da 1ª liquidez tocar o canal, a próxima vela tende a não ultrapassar o pavio da liquidez com o **corpo** (só pavio pode ultrapassar, corpo não). |
| **Invalidação do limite** | Se a vela que "deixa liquidez" ultrapassar o canal de referência com o **pavio**, o limite é invalidado (mercado já reconquistou interesse ali). |
| **Renovação de limite** | Depois do 1º limite validado, se uma 2ª vela também deixar liquidez sem furar o canal, o limite "renova" e vale de novo na vela seguinte. Só invalida quando o canal for furado. |
| **Vela final de taxa dentro do canal** | Quando a vela **não** deixa liquidez dentro do canal (ou seja, não toca/retrai) — sinal de possível reversão. Confirmar entrando só quando o preço tocar o **corpo** do lote rompido (maior segurança). |
| **Segunda vela de lote** (limite tipo 2) | Padrão de 2 candles (verde+vermelho ou vermelho+verde) onde o canal de referência já nasce pronto (overlap dos corpos), sem precisar de rompimento prévio. 6 variações de desenho, conforme onde o overlap acontece. |
| **DDT / Domínio de transferência** | `[CONFIRMAR]` — interpreto como uma "nova posição pós-rompimento", i.e., um novo lote formado logo após o preço romper um lote anterior e mudar de perna, tratado com a mesma lógica do tipo 2. |
| **Ponto de entrada do limite (linha rosa)** | No tipo 2, o ponto de entrada não é o canal inteiro — é uma linha única, deslocada para o lado onde o overlap "sobrou" (ver 6 exemplos do PDF). Precisa do "travamento" na linha azul (canal) pra então ativar a entrada na linha rosa. |
| **D.C / D.V** | `[CONFIRMAR]` — provavelmente "Domínio de Compra" / "Domínio de Venda", indicando a direção dominante do movimento até aquele canal. Usado só como anotação visual nos prints, não parece alterar a regra de entrada. |
| **Transferência** | `[CONFIRMAR]` — aparenta ser o momento em que o preço "transfere" de um lote/canal antigo pra um novo, reaproveitando a mesma lógica de limite tipo 1/2. |
| **Limite tipo 2 — validade** | Só vale até o mercado romper o canal **2 vezes**; depois disso, descartar. |
| **Primeiro registro** | O primeiro pavio contra a direção do movimento em uma vela — pode ser: (a) toda vela de reversão com pavio, (b) o primeiro pavio contrário dentro de um lote que ainda não tinha registro daquele lado, (c) o primeiro pavio na vela de comando e na 1ª vela após o final de uma taxa/consolidação. |
| **Função do primeiro registro** | Tenta "segurar" o preço antes de romper e depois de romper. Toque + retração nele → leitura de retração na vela seguinte. Se romper, esperar vela de confirmação antes de entrar a favor (evita falso rompimento). |
| **Sinal de alta assertividade** | Regra central do documento: primeiro registro **isolado** tem baixa assertividade (às vezes segura, às vezes rompe tudo). Só fica confiável quando o candle que toca o **canal de referência** (tipo 1 ou 2) **é**, ao mesmo tempo, um primeiro registro. Essa combinação é o gatilho de entrada final. |
| **Vela de comando** | A vela de impulso que inicia o movimento/lote — sempre cria um primeiro registro de pavio. |
| **Final de taxa** | `[CONFIRMAR]` — interpreto como o fim de uma fase de lateralização/consolidação (taxa = período sem tendência clara); a vela seguinte a esse período também gera primeiro registro. |

---

## 3. Detecção de Lote e Vela de Comando (`lote_detection.py`)

**Objetivo:** identificar, dado um histórico de candles, os "lotes" candidatos.

Passos:
1. Percorrer candles em sequência; identificar uma vela de comando: candle com corpo relevante (filtro de tamanho mínimo configurável) que inicia um movimento direcional.
2. Verificar se a vela seguinte (ou a própria) deixa pavio na direção contrária logo na abertura → marca o "lote" (guardar índice de início/fim, topo e fundo do corpo, e o pavio de abertura).
3. Guardar isso como objeto `Lote(start_idx, end_idx, top, bottom, direction)`.

**Critério de sucesso:** rodar contra os fixtures extraídos manualmente dos prints do PDF (seção 8) e confirmar que os lotes marcados nas imagens são detectados nos mesmos índices.

---

## 4. Limite Tipo 1 (`limit_type1.py`)

Sequência de estados (máquina de estados simples, sem histórico externo):

1. `AGUARDANDO_ROMPIMENTO`: dado um `Lote`, monitorar candles seguintes até o preço fechar além do topo/fundo do lote.
2. `AGUARDANDO_CONTINUACAO`: a vela seguinte ao rompimento precisa fechar na mesma direção. Se não fechar → descarta o setup.
3. Definir `ReferenceChannel = (pavio_da_vela_rompimento, pavio_da_vela_continuacao)`.
4. `AGUARDANDO_PRIMEIRA_LIQUIDEZ`: monitorar candles futuros até o preço (pavio) tocar dentro do canal pela primeira vez.
5. Ao tocar: verificar a regra de invalidação — **se o pavio da vela que tocou ultrapassar o canal inteiro, invalidar**. Caso contrário, `LIMITE_ATIVO = True`.
6. Enquanto ativo: cada vela seguinte que também tocar o canal sem furar → **renovação** (mantém `LIMITE_ATIVO`). Assim que o canal for furado pelo pavio, `LIMITE_ATIVO = False` (fim do ciclo).
7. Caso a vela **não** toque/deixe liquidez dentro do canal (fecha sem tocar) → gerar sinal alternativo de **reversão** (vela final de taxa): aguardar toque no corpo do lote rompido para confirmar entrada.

Saída: lista de `PriceLimitSignal(channel, ativo_em, tipo="retracao"|"reversao", indice_vela)`.

---

## 5. Limite Tipo 2 (`limit_type2.py`)

1. Detectar o padrão de 2 candles (segunda vela de lote / DDT): overlap de corpos entre vela N e N+1, cor oposta ou mesma cor conforme os 6 casos do PDF.
2. Canal de referência = faixa do overlap de corpos (sem precisar de rompimento prévio — já nasce pronto).
3. Ponto de entrada (linha rosa) = deslocado para o lado onde sobrou o overlap (regra específica de cada um dos 6 padrões — implementar como tabela de casos, não como heurística genérica, pra evitar overfit).
4. Validade: contar quantas vezes o canal foi rompido; **descartar após a 2ª ruptura**.

Saída: mesma estrutura `PriceLimitSignal`, com `tipo="tipo2"`.

---

## 6. Primeiro Registro (`first_register.py`)

Três funções puras, independentes:

- `primeiro_registro_reversao(candles) -> list[int]`: índices de velas de reversão com pavio.
- `primeiro_registro_dentro_do_lote(lote) -> int | None`: primeiro pavio contrário dentro de um lote que ainda não tinha marcado esse lado.
- `primeiro_registro_novo_preco(candles) -> list[int]`: pavios na vela de comando e na 1ª vela após final de taxa/consolidação.

Regra adicional: se o preço rompe um primeiro registro, só considerar entrada a favor do rompimento **após vela de confirmação** (evitar falso rompimento).

---

## 7. Motor de Sinal Combinado (`signal_engine.py`)

Esta é a regra central do documento — junta tudo:

```
Para cada PriceLimitSignal (tipo 1 ou tipo 2):
    se a vela que tocou o canal de referência TAMBÉM é um primeiro registro
        (de qualquer um dos 3 subtipos):
        -> emitir Signal(alta_confianca=True, direcao=..., candle_idx=...)
    senão:
        -> emitir Signal(alta_confianca=False, ...) ou descartar,
           conforme configuração (flag no engine, não hardcoded)
```

Essa é a "mágica" citada no PDF: primeiro registro isolado tem assertividade baixa e inconsistente; combinado ao canal de referência dos limites tipo 1/2, fica assertivo.

---

## 8. Fixtures de teste (critério de verificação — goal-driven)

Extrair manualmente, candle a candle (O/H/L/C aproximados), pelo menos 5 dos prints do PDF que já vêm anotados (ex.: "tipo 1 + 1º registro", "1º registro de reversão", "LIMITE TIPO 1" com "1ºR"). Cada fixture vira um teste:

```python
def test_tipo1_mais_primeiro_registro_caso_A():
    candles = FIXTURE_CASO_A
    signals = signal_engine.run(candles)
    assert signals[-1].alta_confianca is True
    assert signals[-1].candle_idx == INDICE_ESPERADO
```

**Definição de "pronto":** todos os fixtures batendo com o que está anotado manualmente nas imagens do PDF (rompimento, canal, ponto de ativação, e o sinal final).

---

## 9. Interface pública (o que o outro agente vai consumir)

```python
from price_limit_strategy import signal_engine

signals = signal_engine.run(candles: list[Candle]) -> list[Signal]
```

Um único ponto de entrada. O outro agente decide o que fazer com `Signal` (logar, alertar, ou converter em ordem) — isso fica fora deste módulo, como combinado.

---

## 10. Itens em aberto para confirmar antes da versão final

1. `[CONFIRMAR]` significado exato de **D.C**, **D.V**, **Transferência** e **final de taxa** — não impedem o esqueleto do módulo, mas afetam a precisão de `lote_detection.py` e `first_register.py`.
2. `[CONFIRMAR]` os 6 padrões do limite tipo 2 — vou implementar como tabela de casos fixos a partir das imagens; se houver mais variações no material completo do curso, a tabela precisa ser estendida.
3. Tamanho mínimo de corpo/pavio para considerar "relevante" (o PDF não define numericamente) — proponho parametrizar como `%` do ATR (average true range) do ativo, ajustável, em vez de valor fixo.