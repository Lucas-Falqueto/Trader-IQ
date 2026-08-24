from typing import List, Optional
from .models import Candle, Lote

def primeiro_registro_reversao(candles: List[Candle]) -> List[int]:
    """
    Identifica os índices das velas de reversão (mudança de cor) 
    que deixaram um pavio (registro) contra a nova tendência.
    """
    indices = []
    if len(candles) < 2:
        return indices
        
    for i in range(1, len(candles)):
        candle = candles[i]
        candle_ant = candles[i-1]
        
        mudou_cor = (candle.is_bullish != candle_ant.is_bullish)
        if mudou_cor:
            if candle.is_bullish and candle.lower_wick > 0:
                indices.append(i)
            elif candle.is_bearish and candle.upper_wick > 0:
                indices.append(i)
                
    return indices

def primeiro_registro_dentro_do_lote(lote: Lote, candles: List[Candle]) -> Optional[int]:
    """
    Retorna o índice da primeira vela dentro de um lote (após a vela de comando)
    que deixou um pavio contrário (registro).
    """
    # Se o lote tem apenas 1 vela, não há "próximas velas no lote"
    if lote.end_idx <= lote.start_idx:
        return None
        
    for i in range(lote.start_idx + 1, lote.end_idx + 1):
        candle = candles[i]
        if lote.direction == "CALL" and candle.lower_wick > 0:
            return i
        elif lote.direction == "PUT" and candle.upper_wick > 0:
            return i
            
    return None

def primeiro_registro_novo_preco(candles: List[Candle]) -> List[int]:
    """
    Mock para identificar pavios em vela de comando pós-consolidação (Final de taxa).
    (Como não temos a definição exata de D.C/D.V, usamos mudança de volatilidade).
    """
    # Simplificação temporária: retorna mesmos indíces da reversão
    return primeiro_registro_reversao(candles)
