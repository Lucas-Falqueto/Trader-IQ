import logging
import time
from data import conectar
from executor import executar_ordem
from config import IQ_EMAIL, IQ_PASSWORD, ATIVO, VALOR_ENTRADA

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def testar_ordem():
    logger.info("Iniciando Teste de Ordem Live na IQ Option...")
    api = conectar(IQ_EMAIL, IQ_PASSWORD)
    
    # Checar saldo
    try:
        saldo_inicial = api.get_balance()
        logger.info(f"Banca atual: ${saldo_inicial:.2f}")
    except Exception as e:
        logger.error(f"Não foi possível ler o saldo: {e}")
        return

    logger.info(f"Forçando ordem de TESTE em {ATIVO} (Valor: ${VALOR_ENTRADA})...")
    
    # Executa um CALL (direção ALTA)
    resultado = executar_ordem(api, "ALTA", dry_run=False)
    
    logger.info(f"Retorno do Executor: {resultado}")
    
    # Checar saldo final
    try:
        saldo_final = api.get_balance()
        logger.info(f"Banca final: ${saldo_final:.2f} | Diferença: ${(saldo_final - saldo_inicial):.2f}")
    except Exception as e:
        logger.error(f"Não foi possível ler o saldo final: {e}")

if __name__ == "__main__":
    testar_ordem()
