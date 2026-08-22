# Trader-IQ (Pullback Bot M1/M15) 🚀

Este é um sistema autônomo de trading em alta performance desenhado para operar Opções Binárias na IQ Option com foco na estratégia de **Pullback** combinando a estrutura macro de 15 Minutos (M15) com a precisão cirúrgica de 1 Minuto (M1).

## 🧠 Arquitetura Avançada
O bot foi programado com ferramentas matemáticas e lógicas de defesa pesadas:
* **Filtro de Payout:** Cancela instantaneamente a ordem se a corretora dropar o payout abaixo do limite aceitável no momento da compra (Ex: 70%).
* **Warmup Engine (Prevenção de Cold Start):** Ao ser ligado, o robô consome as últimas 90 velas de 1 minuto em um milissegundo para reconstruir todo o histórico e garantir que não perderá um toque numa resistência que foi rompida há horas atrás.
* **WebSocket de Alta Frequência:** Usa conexão contínua direta via WebSocket para escutar o momento *exato* de Win/Loss sem congelar o bot, anulando qualquer delay no disparo de Gales.
* **Gale Dinâmico (Martingale):** Gerencia nativamente até `N` níveis de Gale com fator configurável, efetuando o disparo cravado no segundo `00` sem atrasos corretivos.

## ⚠️ A Biblioteca `iqoptionapi` Modificada (Importante!)
Para que todo o mecanismo acima fosse possível (principalmente a escuta de ordens pelo WebSocket sem os tradicionais delays e travamentos), **a biblioteca oficial `iqoptionapi` foi desconstruída, editada e trazida de forma local para a raiz deste projeto.**

Você **não** deve instalar a `iqoptionapi` usando `pip install`. O código já lerá a biblioteca da pasta nativa `/iqoptionapi/` no repositório. Arquivos principais alterados:
* `iqoptionapi/stable_api.py` -> A função `check_win_v3` foi reconstruída para rastrear a leitura assíncrona do dicionário `order_async`.
* `iqoptionapi/constants.py` -> O dicionário `ACTIVES` foi expandido para suportar todos os pares exóticos `-OTC` (como SP35-OTC, US100-OTC, JP225-OTC, etc).

## 🛠 Instalação
1. Clone este repositório.
2. Crie e ative um ambiente virtual (`python -m venv .venv`).
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Copie o arquivo `.env.example` para `.env` e preencha suas configurações:
   ```env
   IQ_EMAIL=seu_email@email.com
   IQ_PASSWORD=sua_senha
   MODE=PRACTICE
   ATIVO=EURUSD-OTC
   MAX_PERDAS_SEGUIDAS=3
   STOP_LOSS_DIARIO=100.0
   META_DIARIA=50.0
   VALOR_ENTRADA=1.0
   PAYOUT_MINIMO=0.70
   USAR_GALE=True
   MAX_GALES=2
   FATOR_GALE=2.0
   VELAS_SR=3
   ```

## 🚀 Como Executar

### Backtest Isolado
Para rodar simulações estatísticas no passado para qualquer par (busca os últimos 30 dias):
```bash
python backtest.py
```
*(Os resultados serão salvos em `/resultados/backtests/`)*

### Robô Ao Vivo (Bot Individual)
Para rodar o bot no mercado em tempo real lendo as variáveis do `.env`:
```bash
python main.py
```

### Portfólio Simultâneo (Multi-Moedas)
Para rodar dezenas de robôs simultâneos operando todas as moedas da lista `ATIVOS_PARA_RODAR`:
1. Edite os pares desejados dentro do arquivo `run_all.py` (Linha 7).
2. Dê dois cliques em `iniciar_robos.bat` ou execute:
```bash
python run_all.py
```
*(Os logs individuais ficarão registrados no console e os trades finais aparecerão na pasta `/resultados/live/`)*
