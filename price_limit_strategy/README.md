# Estratégia Price Limit & Primeiro Registro (Nova Arquitetura)

## 1. Visão Geral
A estratégia *Price Limit* (Sniper) atua rastreando agrupamentos direcionais (Lotes) para construir canais de referência baseados na liquidez presa. A principal característica desta arquitetura é o **altíssimo volume de oportunidades** mantendo uma assertividade cirúrgica (entre 87% e 92%) em testes de estresse de 30 dias contínuos.

## 2. Setups Operacionais
A estratégia foi dividida em três lógicas principais, sendo apenas duas ativas para conta real:

- **Retração (Canal T1) - Ativo:** Ocorre quando o preço recua e toca a borda do canal formado entre o pavio de rompimento e continuação do Lote. É o setup de maior assertividade (~90%).
- **Reversão (Furo do T1 + Corpo do Lote) - Ativo:** Se a Retração falhar e o preço romper o Canal, surge a Reversão. Ela acontece quando o preço finalmente atinge o corpo sólido do Lote original, repelindo o mercado fortemente de volta.
- **Limite Tipo 2 - Desativado:** Setup baseado em overlap (encavalamento) de preço sem rompimento absoluto. Desligado cirurgicamente após backtest em massa provar que gera ruído e puxa o Win Rate global para baixo.

## 3. O "Filtro Sniper" (Confluência Matemática)
O robô só abre a ordem se todos os satélites de dados entrarem em alinhamento no momento do gatilho:
1. **O Primeiro Registro:** O toque no limite de preço só é válido se a vela em questão formar um padrão de "Primeiro Registro", garantindo que a região ainda está virgem de liquidez.
2. **SMA 100:** O preço deve estar a favor da Macrotendência (Call acima, Put abaixo da média).
3. **RSI (14 - Wilder's EWM):** Rastreador de exaustão em tempo real, travando sinais que caem em picos absolutos (Call apenas se RSI < 80, Put apenas se RSI > 20).

## 4. Escudo Defensivo: Horários da Morte e "Supernova"
Durante a execução de 24 horas, há janelas de alta probabilidade estatística de sequências de ruído que quebram o Gale (0h, 4h, 10h, 13h, 15h, 20h e 23h).

- **O Bloqueio:** O robô detecta e aborta os trades nessas horas. Para fins de estudo, salva no CSV uma marcação `BLOQUEADO_HORA` sem afetar sua banca.
- **O Fura-Bloqueio (Sinal Supernova):** O robô pode ignorar a regra acima se, e somente se, o sinal for um ponto de pressão brutal, cumprindo rigorosamente:
  - RSI indicando fluxo fortíssimo a favor (>= 65 para Alta, <= 35 para Baixa).
  - Nenhuma aceleração contrária ameaçadora nas últimas 2 velas (`t-1` e `t-2` não podem vir da mesma cor fechando contra você).

## 5. Como Executar e Monitorar
1. **Para Ligar:** Execute o script `iniciar_limit.bat` (Janela de cor azul-clara).
2. **Diretório de Resultados:** Todos os dados, lucros, perdas e sinais bloqueados cairão isoladamente em `resultados/live_limit/trades_live_{Ativo}.csv`.
3. **Meta:** Funciona melhor sob o conceito *Hit and Run* (Bater e Correr): aproveitando o volume de ~50 trades/dia por ativo, o robô baterá a `META_DIARIA` em questão de poucas horas e deve se desligar em segurança.
