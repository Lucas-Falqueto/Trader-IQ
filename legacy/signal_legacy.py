import pandas as pd
from core.config import MINIMUM_WICK_RATIO

def analisar_candle(vela: pd.Series) -> dict:
    """
    Extrai proporções matemáticas da vela (ratios) para uso no Score System.
    Retorna um dicionário com os dados brutos e os booleanos derivados.
    """
    open_p = vela["open"]
    close_p = vela["close"]
    high_p = vela["high"]
    low_p = vela["low"]
    
    range_p = high_p - low_p
    body = abs(close_p - open_p)
    upper_wick = high_p - max(open_p, close_p)
    lower_wick = min(open_p, close_p) - low_p
    
    body_ratio = body / range_p if range_p > 0 else 0
    upper_wick_ratio = upper_wick / range_p if range_p > 0 else 0
    lower_wick_ratio = lower_wick / range_p if range_p > 0 else 0
    
    has_upper_wick = upper_wick_ratio >= MINIMUM_WICK_RATIO
    has_lower_wick = lower_wick_ratio >= MINIMUM_WICK_RATIO
    
    favored_wick = "NONE"
    if has_upper_wick and has_lower_wick:
        favored_wick = "BOTH"
    elif has_upper_wick:
        favored_wick = "UPPER"
    elif has_lower_wick:
        favored_wick = "LOWER"
        
    return {
        "range": range_p,
        "body": body,
        "upperWick": upper_wick,
        "lowerWick": lower_wick,
        "bodyRatio": body_ratio,
        "upperWickRatio": upper_wick_ratio,
        "lowerWickRatio": lower_wick_ratio,
        "hasUpperWick": has_upper_wick,
        "hasLowerWick": has_lower_wick,
        "favoredWick": favored_wick,
        "isBullish": close_p > open_p,
        "isBearish": close_p < open_p,
        "high": high_p,
        "low": low_p,
        "close": close_p
    }

def detectar_engolfo(vela_atual: pd.Series, vela_anterior: pd.Series) -> str:
    """
    Detecta engolfo clássico (corpo cobre corpo).
    Retorna: "BULLISH_ENGULFING", "BEARISH_ENGULFING" ou "NONE".
    """
    if vela_atual is None or vela_anterior is None:
        return "NONE"

    ant_max = max(vela_anterior["open"], vela_anterior["close"])
    ant_min = min(vela_anterior["open"], vela_anterior["close"])
    atu_max = max(vela_atual["open"], vela_atual["close"])
    atu_min = min(vela_atual["open"], vela_atual["close"])
    
    cobre_corpo = atu_min <= ant_min and atu_max >= ant_max
    
    atu_bullish = vela_atual["close"] > vela_atual["open"]
    ant_bearish = vela_anterior["close"] < vela_anterior["open"]
    
    if atu_bullish and ant_bearish and cobre_corpo:
        return "BULLISH_ENGULFING"
        
    if (not atu_bullish) and (not ant_bearish) and cobre_corpo:
        # atu_bearish e ant_bullish
        return "BEARISH_ENGULFING"
        
    return "NONE"
