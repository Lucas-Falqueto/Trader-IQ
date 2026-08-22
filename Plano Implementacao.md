# Plano de Implementação — Bot IQ Option (Estratégia Pullback)

## Diretrizes obrigatórias (Karpathy Guidelines)

Antes de codar qualquer parte deste plano, siga estas 4 regras em toda a sessão:

### 1. Pense antes de codar
- Não assuma nada em silêncio. Se houver ambiguidade, apresente as interpretações possíveis ou pergunte — não escolha sozinho.
- Se existir uma abordagem mais simples, diga isso. Questione quando fizer sentido.
- Se algo estiver confuso, pare. Nomeie o que está confuso. Pergunte.

### 2. Simplicidade primeiro
- Código mínimo que resolve o problema. Nada especulativo.
- Sem features além do que foi pedido.
- Sem abstrações para código de uso único.
- Sem "flexibilidade" ou "configurabilidade" que não foi pedida.
- Sem tratamento de erro para cenários impossíveis.
- Se escreveu 200 linhas e podia ser 50, reescreva.

### 3. Mudanças cirúrgicas
- Mexa só no que precisa. Não "melhore" código adjacente, comentários ou formatação.
- Não refatore o que não está quebrado.
- Siga o estilo já existente no arquivo, mesmo que faria diferente.
- Se notar código morto não relacionado, mencione — não apague.
- Remova apenas imports/variáveis/funções que a SUA mudança tornou órfãos.

### 4. Execução orientada a metas
- Toda tarefa deve virar um critério verificável antes de começar a codar.
- Para tarefas com múltiplas etapas, apresente um plano curto:
  ```
  1. [Passo] → verificar: [checagem]
  2. [Passo] → verificar: [checagem]
  ```
- Loop até a verificação passar. Não pare em "deve estar funcionando".

---

## Premissas assumidas (validar antes de prosseguir)

- Todo desenvolvimento e teste ocorre em **conta demo**. Execução em conta real só depois do backtest (passo 5) mostrar consistência.
- IQ Option não tem API oficial pública. Será usada uma biblioteca não-oficial da comunidade (ex.: `iqoptionapi`), que pode quebrar quando a corretora mudar o backend. Isso é uma limitação estrutural do projeto.
- A estratégia "pullback" descrita é análise técnica discricionária, sem validação estatística prévia. O backtest (passo 5) existe justamente para checar se há edge real antes de ligar execução automática.
- Opções binárias são instrumento de alto risco, com estrutura de soma desfavorável ao operador contra a casa.

---

## Meta verificável

Bot em Python que:
1. Monitora candles M15 para marcar suporte/resistência (topo/fundo do pavio das 3 penúltimas velas).
2. Monitora M1 para detectar rompimento (>50% da marcação, sem pavio contrário) + pullback (retorno ao nível rompido) + confirmação (vela de força ou engolfo).
3. Tem modo backtest/simulação, obrigatório rodar **antes** de qualquer execução real.
4. Opcionalmente executa ordem via API não-oficial, só depois do backtest validado.

## Stack

- Python 3.10+
- `iqoptionapi` (biblioteca comunitária) — candles e execução
- `pandas` — manipulação de candles
- Sem framework multi-corretora, sem banco de dados, sem abstrações não pedidas.

## Arquitetura

```
main.py           # loop principal
data.py           # busca candles M15/M1 via API
levels.py         # marca suporte/resistência (3 penúltimas velas, topo/fundo do pavio)
signal.py         # detecta rompimento >50%, vela de força, engolfo, pullback
executor.py       # decide compra/venda e (opcional) envia ordem
backtest.py       # roda a lógica sobre dados históricos, sem executar ordem real
config.py         # ativo, timeframe, % payout mínimo, etc — só o que for usado
```

## Passos com verificação

1. **Conexão e coleta de dados**
   → verificar: script conecta na conta demo e imprime candles M15 e M1 de um ativo real.

2. **Marcação de suporte/resistência (M15)**
   → verificar: rodando sobre um gráfico histórico conhecido, a marcação bate com marcação manual esperada.

3. **Detecção de rompimento (M1)**
   → verificar: função sinaliza rompimento só quando a vela ultrapassa >50% da marcação, sem pavio contrário.

4. **Detecção de pullback + confirmação (vela de força / engolfo)**
   → verificar: em dataset histórico com pullbacks conhecidos, a função marca entrada exatamente nos pontos esperados.

5. **Backtest**
   → verificar: rodar a estratégia completa sobre N meses de histórico e reportar taxa de acerto, sem ajustar parâmetros olhando o mesmo período testado (evitar overfitting).

6. **Execução (opcional, só após passo 5 mostrar consistência)**
   → verificar: bot abre ordem em conta demo com valor configurado e loga o resultado.

7. **Gestão de risco simples**
   → verificar: bot para automaticamente após N perdas seguidas ou ao atingir meta/stop diário configurado.

## Fora de escopo (não implementar por padrão)

- Suporte a múltiplos ativos/corretoras simultâneos
- Dashboard/interface gráfica
- "Modo configurável" para trocar de estratégia
- Machine learning em cima da estratégia