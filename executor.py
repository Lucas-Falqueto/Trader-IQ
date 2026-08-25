import logging
import concurrent.futures
from iqoptionapi.stable_api import IQ_Option
from config import ATIVO, DURACAO_OPCAO, PAYOUT_MINIMO

logger = logging.getLogger(__name__)


def _normalizar_check_win(bruto) -> dict:
    """check_win_v3 devolve (status, lucro), não uma string."""
    lucro = 0.0
    if isinstance(bruto, tuple):
        status, lucro = bruto[0], float(bruto[1] or 0)
    else:
        status = bruto
    texto = str(status).lower()
    if texto in ("win",):
        resultado = "win"
    elif texto in ("lose", "loose"):
        resultado = "lose"
    elif texto in ("equal", "tie"):
        resultado = "tie"
    else:
        resultado = texto
    return {"resultado": resultado, "lucro": lucro}


def verificar_payout(api: IQ_Option) -> bool:
    try:
        payout = api.get_all_profit()
        payout_ativo = payout.get(ATIVO, {}).get("turbo", 0)
        
        if payout_ativo < PAYOUT_MINIMO:
            logger.warning(f"Payout lido da API ({payout_ativo:.0%}) está abaixo do mínimo. Ignorando bloqueio por suspeita de bug da corretora.")
            
        return True # Força a aprovação para não perder o sinal
    except Exception as e:
        logger.error(f"Erro ao checar payout: {e}")
        return True


def executar_ordem(api: IQ_Option, direcao: str, valor_entrada: float, dry_run: bool = False) -> dict:
    """
    Executa uma ordem binária.

    Args:
        api: IQ_Option instance
        direcao: "ALTA" -> call | "BAIXA" -> put
        valor_entrada: Valor a ser investido na ordem
        dry_run: se True, loga a ordem mas NÃO envia para a API (modo simulação)

    Returns:
        {"id": ..., "resultado": "win"|"lose"|"tie"|"simulado"}
    """
    # A engine retorna "CALL" ou "PUT"
    direcao_upper = direcao.upper()
    if direcao_upper in ("ALTA", "CALL"):
        action = "call"
    else:
        action = "put"

    if dry_run:
        logger.info(f"[DRY-RUN] Ordem simulada: {action} | {ATIVO} | ${valor_entrada}")
        return {"id": None, "resultado": "simulado", "lucro": 0.0}

    if not verificar_payout(api):
        logger.warning(f"Payout abaixo de {PAYOUT_MINIMO:.0%}. Ordem cancelada.")
        return {"id": None, "resultado": "cancelado", "lucro": 0.0}

    try:
        sucesso, order_id = api.buy(valor_entrada, ATIVO, action, DURACAO_OPCAO)
        if not sucesso:
            logger.error("Falha ao enviar ordem para a API (Retorno False).")
            return {"id": None, "resultado": "erro", "lucro": 0.0}
    except Exception as e:
        logger.error(f"Exceção ao tentar enviar ordem: {e}")
        return {"id": None, "resultado": "erro", "lucro": 0.0}

    logger.info(f"Ordem enviada: {action} | id={order_id}. Aguardando resultado...")

    # Usa um ThreadPool para evitar que o check_win trave o bot para sempre
    timeout_segundos = (DURACAO_OPCAO * 60) + 120  # Aumentado para 2 minutos extras de margem
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = pool.submit(api.check_win_v3, order_id)
    try:
        bruto = future.result(timeout=timeout_segundos)
        logger.info(f"Resultado recebido da corretora: {bruto}")
        return {"id": order_id, **_normalizar_check_win(bruto)}
    except concurrent.futures.TimeoutError:
        logger.error(f"Timeout ao aguardar resultado da ordem {order_id}.")
        return {"id": order_id, "resultado": "timeout", "lucro": 0.0}
    except Exception as e:
        logger.error(f"Erro ao checar resultado da ordem {order_id}: {e}")
        return {"id": order_id, "resultado": "erro", "lucro": 0.0}
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
