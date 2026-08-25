from typing import List, Optional
from .models import Candle, Lote
from .candle_utils import calcular_tamanho_medio, eh_vela_relevante, tem_pavio_rejeicao_abertura

def detectar_lotes(candles: List[Candle], atr_lookback: int = 10, proporcao_minima: float = 0.5) -> List[Lote]:
    """
    Varre a lista de candles e retorna todos os Lotes encontrados.
    Um lote inicia com uma vela de comando (movimento direcional) e termina quando a cor muda.
    """
    lotes = []
    
    for i in range(1, len(candles)):
        candle = candles[i]
        candle_ant = candles[i-1]
        
        mudou_cor = (candle.is_bullish != candle_ant.is_bullish)
        
        if mudou_cor:
            atr = calcular_tamanho_medio(candles[:i], lookback=atr_lookback)
            # Sem histórico suficiente ainda: não filtra, evita descartar primeiros candles do dataset.
            if atr > 0 and not eh_vela_relevante(candle, atr, proporcao_minima):
                continue

            if tem_pavio_rejeicao_abertura(candle):
                direcao = "CALL" if candle.is_bullish else "PUT"
                pavio_abertura = candle.low if candle.is_bullish else candle.high
                
                lote = Lote(
                    start_idx=i, 
                    end_idx=i, 
                    top=candle.body_top, 
                    bottom=candle.body_bottom,
                    direction=direcao, 
                    opening_wick=pavio_abertura
                )
                lotes.append(lote)
                
    return lotes
