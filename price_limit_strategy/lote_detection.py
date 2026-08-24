from typing import List, Optional
from .models import Candle, Lote
from .candle_utils import calcular_tamanho_medio, eh_vela_relevante, tem_pavio_rejeicao_abertura

def detectar_lotes(candles: List[Candle]) -> List[Lote]:
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
            # É a origem de um movimento.
            # Regra do PDF: "a primeira vela dessa base deixa um pavio logo na sua abertura"
            if tem_pavio_rejeicao_abertura(candle):
                direcao = "CALL" if candle.is_bullish else "PUT"
                pavio_abertura = candle.low if candle.is_bullish else candle.high
                
                # O Lote é travado IMEDIATAMENTE como essa vela base de origem.
                # Seus limites são os limites do corpo (topo e fundo do corpo).
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
