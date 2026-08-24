from typing import List
from .models import Candle

def calcular_tamanho_medio(candles: List[Candle], lookback: int = 10) -> float:
    """Calcula o tamanho médio total (high - low) das últimas 'lookback' velas."""
    if not candles:
        return 0.0
    
    tamanho_lista = min(len(candles), lookback)
    recents = candles[-tamanho_lista:]
    
    total = sum(c.total_size for c in recents)
    return total / tamanho_lista if tamanho_lista > 0 else 0.0

def eh_vela_relevante(candle: Candle, atr: float, proporcao_minima: float = 0.5) -> bool:
    """Verifica se o corpo da vela representa um movimento de impulsão relevante."""
    corpo = candle.body_top - candle.body_bottom
    return corpo >= (atr * proporcao_minima)

def tem_overlap_corpo(c1: Candle, c2: Candle) -> bool:
    """Verifica se há intersecção (overlap) entre os corpos de duas velas."""
    return not (c1.body_top < c2.body_bottom or c1.body_bottom > c2.body_top)

def calcular_overlap_corpo(c1: Candle, c2: Candle) -> tuple[float, float]:
    """Retorna a faixa (topo, fundo) onde os corpos se sobrepõem."""
    topo = min(c1.body_top, c2.body_top)
    fundo = max(c1.body_bottom, c2.body_bottom)
    return topo, fundo

def tem_pavio_rejeicao_abertura(candle: Candle) -> bool:
    """Verifica se a vela deixou pavio contra o próprio movimento logo na abertura."""
    if candle.is_bullish:
        # Vela de alta tem pavio de rejeição na abertura se o fundo for menor que a abertura
        return candle.lower_wick > 0
    else:
        # Vela de baixa tem pavio de rejeição na abertura se o topo for maior que a abertura
        return candle.upper_wick > 0
