from typing import List
from .models import Candle, Lote, ReferenceChannel, PriceLimitSignal

def processar_limite_tipo1(candles: List[Candle], lotes: List[Lote]) -> List[PriceLimitSignal]:
    sinais = []
    
    for lote in lotes:
        estado = "AGUARDANDO_ROMPIMENTO"
        vela_rompimento = None
        vela_continuacao = None
        canal = None
        toques = 0
        
        for i in range(lote.end_idx + 1, len(candles)):
            candle = candles[i]
            
            # Regra Global: Lote perde a validade após 20 velas da sua criação
            if i - lote.start_idx > 20:
                estado = "FALHOU"
                break
            
            # Timeout de Rompimento: Se passar 5 velas e não romper, lote caduca
            if estado == "AGUARDANDO_ROMPIMENTO":
                if i - lote.end_idx > 5:
                    estado = "FALHOU"
                    break
                
                rompeu = False
                if lote.direction == "CALL" and candle.close > lote.top:
                    rompeu = True
                elif lote.direction == "PUT" and candle.close < lote.bottom:
                    rompeu = True
                    
                if rompeu:
                    vela_rompimento = candle
                    estado = "AGUARDANDO_CONTINUACAO"
                continue
                
            if estado == "AGUARDANDO_CONTINUACAO":
                mesma_direcao = (lote.direction == "CALL" and candle.is_bullish) or (lote.direction == "PUT" and candle.is_bearish)
                
                if mesma_direcao:
                    vela_continuacao = candle
                    # PDF: O canal de referência é a faixa entre o pavio da vela de rompimento e o pavio da vela de continuação.
                    if lote.direction == "CALL":
                        topo_canal = max(vela_rompimento.high, vela_continuacao.high)
                        fundo_canal = min(vela_rompimento.high, vela_continuacao.high)
                    else:
                        topo_canal = max(vela_rompimento.low, vela_continuacao.low)
                        fundo_canal = min(vela_rompimento.low, vela_continuacao.low)
                        
                    canal = ReferenceChannel(top=topo_canal, bottom=fundo_canal, start_idx=i)
                    estado = "AGUARDANDO_PRIMEIRA_LIQUIDEZ"
                else:
                    estado = "FALHOU"
                continue
                
            if estado in ["AGUARDANDO_PRIMEIRA_LIQUIDEZ", "LIMITE_ATIVO", "AGUARDANDO_REVERSAO"]:
                # Timeout de Pullback: 15 velas de vida para o canal
                if i - canal.start_idx > 15:
                    estado = "FALHOU"
                    break
                    
                # Invalidação Estrutural Global: Preço engoliu o lote de volta (fechou além do limite oposto)
                if lote.direction == "CALL" and candle.close < lote.bottom:
                    estado = "FALHOU"
                    break
                if lote.direction == "PUT" and candle.close > lote.top:
                    estado = "FALHOU"
                    break

                # Se estamos nas fases iniciais do Canal, processamos os toques.
                if estado in ["AGUARDANDO_PRIMEIRA_LIQUIDEZ", "LIMITE_ATIVO"]:
                    tocou_canal = False
                    furou_canal = False
                    
                    if lote.direction == "CALL":
                        if candle.low <= canal.top:
                            tocou_canal = True
                        if candle.low < canal.bottom:
                            furou_canal = True
                    else:
                        if candle.high >= canal.bottom:
                            tocou_canal = True
                        if candle.high > canal.top:
                            furou_canal = True
                            
                    if tocou_canal:
                        if furou_canal:
                            # PDF: Furou o canal = Invalida a Retração. Nasce a chance de Reversão!
                            estado = "AGUARDANDO_REVERSAO"
                        else:
                            toques += 1
                            estado = "LIMITE_ATIVO"
                            sinais.append(PriceLimitSignal(
                                channel=canal,
                                ativo_em=i,
                                tipo="retracao",
                                indice_vela=i,
                                direcao=lote.direction
                            ))
                            if toques >= 3:
                                estado = "FALHOU"
                
                # Se o status acabou de virar AGUARDANDO_REVERSAO ou já era, checamos o toque no corpo.
                # Nota: Não usamos elif aqui para que ele possa processar o toque no mesmo candle que furou o canal.
                if estado == "AGUARDANDO_REVERSAO":
                    if (lote.direction == "CALL" and candle.low <= lote.top) or (lote.direction == "PUT" and candle.high >= lote.bottom):
                        # Tocou no corpo do Lote original!
                        sinais.append(PriceLimitSignal(
                            channel=canal,
                            ativo_em=i,
                            tipo="reversao",
                            indice_vela=i,
                            direcao="PUT" if lote.direction == "CALL" else "CALL"
                        ))
                        # Reversão atira uma vez e finaliza o setup
                        estado = "FALHOU"
                        
            if estado == "FALHOU":
                break
                
    return sinais
