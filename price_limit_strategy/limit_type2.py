from typing import List
from .models import Candle, ReferenceChannel, PriceLimitSignal
from .candle_utils import tem_overlap_corpo, calcular_overlap_corpo

def processar_limite_tipo2(candles: List[Candle]) -> List[PriceLimitSignal]:
    sinais = []
    
    for i in range(3, len(candles) - 1):
        c1 = candles[i-1]
        c2 = candles[i]
        
        # 1. Cores opostas
        if (c1.is_bullish and c2.is_bearish) or (c1.is_bearish and c2.is_bullish):
            
            c1_body_size = c1.body_top - c1.body_bottom
            c2_body_size = c2.body_top - c2.body_bottom
            overlap_top = min(c1.body_top, c2.body_top)
            overlap_bottom = max(c1.body_bottom, c2.body_bottom)
            
            overlap_size = max(0, overlap_top - overlap_bottom)
            gap_abertura = abs(c2.open - c1.close)
            
            # Classificação
            if overlap_size == 0 and gap_abertura < 0.0001:
                variacao = "V2" # Taxa Dividida
            elif overlap_size > 0:
                pct_overlap = overlap_size / max(c1_body_size, c2_body_size, 0.0001)
                if pct_overlap < 0.20:
                    variacao = "V1" # Gap Mínimo / Fino
                else:
                    variacao = "V3" # Profundo
            else:
                continue
                
            if c1.is_bullish and c2.is_bearish: # PUT (Resistência)
                if not (candles[i-2].is_bearish and candles[i-3].is_bearish):
                    continue
                direcao = "PUT"
                limite_linha = overlap_top if variacao == "V1" else c2.high
                linha_azul = overlap_top
                
            else: # CALL (Suporte)
                if not (candles[i-2].is_bullish and candles[i-3].is_bullish):
                    continue
                direcao = "CALL"
                limite_linha = overlap_bottom if variacao == "V1" else c2.low
                linha_azul = overlap_bottom
                
            canal = ReferenceChannel(top=limite_linha, bottom=limite_linha, start_idx=i)
            toques = 0
            travado_na_azul = (variacao != "V2") # V1 e V3 já nascem travados
            
            for j in range(i + 1, len(candles)):
                vela = candles[j]
                
                if j - i > 15:
                    break
                    
                if not travado_na_azul:
                    if direcao == "PUT" and vela.high >= linha_azul:
                        travado_na_azul = True
                    elif direcao == "CALL" and vela.low <= linha_azul:
                        travado_na_azul = True
                        
                tocou = (vela.high >= limite_linha) if direcao == "PUT" else (vela.low <= limite_linha)
                furou = (vela.close > limite_linha) if direcao == "PUT" else (vela.close < limite_linha)
                        
                if tocou:
                    if furou:
                        break # Rompeu corpo, morre
                    else:
                        if travado_na_azul:
                            toques += 1
                            sinais.append(PriceLimitSignal(channel=canal, ativo_em=j, tipo="tipo2", indice_vela=j, direcao=direcao))
                        if toques >= 2:
                            break
                                
    return sinais
