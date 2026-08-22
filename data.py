from iqoptionapi.stable_api import IQ_Option
import pandas as pd
import time
from config import ACCOUNT_TYPE


def conectar(email: str, senha: str) -> IQ_Option:
    """Conecta na IQ Option e retorna a instância autenticada."""
    api = IQ_Option(email, senha)
    check, reason = api.connect()
    if not check:
        raise ConnectionError(f"Falha ao conectar na IQ Option: {reason}")
    api.change_balance(ACCOUNT_TYPE)  # REAL ou PRACTICE
    return api


def _candles_para_df(candles) -> pd.DataFrame:
    df = pd.DataFrame(candles)
    df = df[["id", "from", "open", "close", "max", "min", "volume"]].rename(
        columns={"max": "high", "min": "low", "from": "ts"}
    )
    return df


def buscar_candles(api: IQ_Option, ativo: str, timeframe: int, count: int) -> pd.DataFrame:
    """
    Busca candles históricos.

    Args:
        timeframe: em segundos (900 = M15, 60 = M1)
        count: quantidade de candles

    Returns:
        DataFrame com colunas: open, close, high, low, volume, id (timestamp)
    """
    candles = api.get_candles(ativo, timeframe, count, time.time())
    df = _candles_para_df(candles)
    return df.sort_values("id").reset_index(drop=True)


def buscar_candles_historico(
    api: IQ_Option, ativo: str, timeframe: int, count: int, lote: int = 1000
) -> pd.DataFrame:
    """Busca `count` candles paginando para trás (a API limita o tamanho do lote)."""
    partes = []
    restante = count
    fim = time.time()
    while restante > 0:
        pedido = min(lote, restante)
        candles = api.get_candles(ativo, timeframe, pedido, fim)
        if not candles:
            break
        partes.append(_candles_para_df(candles))
        mais_antigo = min(c["from"] for c in candles)
        fim = mais_antigo - 1
        restante -= len(candles)
        if len(candles) < pedido:
            break
        time.sleep(0.2)
    if not partes:
        return pd.DataFrame(columns=["id", "ts", "open", "close", "high", "low", "volume"])
    df = pd.concat(partes, ignore_index=True)
    df = df.drop_duplicates(subset="id").sort_values("id").reset_index(drop=True)
    return df
