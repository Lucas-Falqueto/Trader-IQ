import os
from dotenv import load_dotenv

load_dotenv()

# Credenciais IQ Option
IQ_EMAIL = os.getenv("IQ_EMAIL", "")
IQ_PASSWORD = os.getenv("IQ_PASSWORD", "")
ACCOUNT_TYPE = os.getenv("ACCOUNT_TYPE", "PRACTICE")

# Parâmetros de operação
ATIVO = os.getenv("ATIVO", "EURUSD")
VALOR_ENTRADA = float(os.getenv("VALOR_ENTRADA", "1.0"))  # em dólares
DURACAO_OPCAO = int(os.getenv("DURACAO_OPCAO", "1"))      # minutos
PAYOUT_MINIMO = float(os.getenv("PAYOUT_MINIMO", "0.70")) # 70%

# Martingale
USAR_GALE = os.getenv("USAR_GALE", "True").lower() in ("true", "1", "yes")
MAX_GALES = int(os.getenv("MAX_GALES", "2"))
FATOR_GALE = float(os.getenv("FATOR_GALE", "2.0"))

# Gestão de risco
MAX_PERDAS_SEGUIDAS = int(os.getenv("MAX_PERDAS_SEGUIDAS", "3"))
STOP_LOSS_DIARIO = float(os.getenv("STOP_LOSS_DIARIO", "10.0"))  # em dólares
META_DIARIA = float(os.getenv("META_DIARIA", "5.0"))             # em dólares

# Número de velas M15 usadas para marcar suporte/resistência
VELAS_SR = 3

# Expira o rompimento se o pullback não aparecer em N velas M1
TIMEOUT_VELAS_M1 = 15

# Histórico do backtest (paginado na API)
DIAS_BACKTEST = 30

# ── Parâmetros da Estratégia de Score ─────────────────────────────────────────
MINIMUM_WICK_RATIO = 0.25      # Pavio deve ter >= 25% da amplitude para ser considerado relevante
MINIMUM_BODY_RATIO = 0.50      # Vela forte deve ter >= 50% de corpo em relação à amplitude
BREAKOUT_THRESHOLD = 0.50      # Rompimento precisa cruzar > 50% da zona de S/R
PULLBACK_TOLERANCE = 0.001     # Preço pode estar dentro de 0.1% do nível para ser pullback
MINIMUM_SCORE = 6              # Nota mínima de confluência (0 a 8) para gerar sinal
