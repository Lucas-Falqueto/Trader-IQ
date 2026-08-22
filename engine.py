from signal import analisar_candle, detectar_engolfo
from config import BREAKOUT_THRESHOLD, PULLBACK_TOLERANCE, MINIMUM_SCORE, TIMEOUT_VELAS_M1, VELAS_SR
from levels import marcar_niveis

# Estados
WAITING = "WAITING"
WAITING_PULLBACK = "WAITING_PULLBACK"

def novo_estado() -> dict:
    return {
        "status": WAITING,
        "breakoutLevel": None,
        "breakoutDirection": None,
        "breakoutRatio": None,
        "isStrongBreakout": False,
        "isStrongCandle": False,
        "hasOpposingWick": True,
        "m15Engulfing": False,
        "regionRespected": False,
        "velas_espera": 0,
        "ultimo_sr_rompido": None
    }

def avaliar_sinal(estado: dict) -> dict:
    """Calcula o score final (0 a 8) focado na qualidade do M15."""
    score = 0
    reasons = []

    # 1. Rompimento válido (ocorreu e está registrado)
    if estado["breakoutDirection"]:
        score += 1
        reasons.append("valid_breakout")

    # 2. Rompimento > 50% da zona
    if estado["isStrongBreakout"]:
        score += 1
        reasons.append("strong_breakout_ratio")

    # 3. Vela de força no rompimento (corpo > 50% do range)
    if estado["isStrongCandle"]:
        score += 1
        reasons.append("strong_breakout_candle")

    # 4. Sem pavio contrário (só pavio a favor)
    if not estado["hasOpposingWick"]:
        score += 1
        reasons.append("no_opposing_wick")

    # 5. Região respeitada (velas anteriores deixaram pavio na zona)
    if estado["regionRespected"]:
        score += 1
        reasons.append("region_respected")

    # 6. Engolfo M15 na vela de rompimento
    if estado["m15Engulfing"]:
        score += 1
        reasons.append("m15_engulfing")

    # 7. Pullback válido (toque exato na tolerância) - obrigatório pelo state machine
    score += 1
    reasons.append("exact_touch_pullback")

    # 8. Bônus por score estar alto (para manter a nota 8 possível)
    # Podemos considerar a força direcional geral
    if estado["isStrongBreakout"] and estado["m15Engulfing"]:
         score += 1
         reasons.append("perfect_structure")

    direcao = estado["breakoutDirection"]
    signal = "CALL" if direcao == "ALTA" else "PUT"
    if score < MINIMUM_SCORE:
        signal = "NO_TRADE"

    return {
        "signal": signal,
        "direction": direcao,
        "score": score,
        "breakoutLevel": estado["breakoutLevel"],
        "breakoutDirection": direcao,
        "reasons": reasons
    }

def _reset(estado: dict):
    estado["status"] = WAITING
    estado["breakoutLevel"] = None
    estado["breakoutDirection"] = None
    estado["breakoutRatio"] = None
    estado["isStrongBreakout"] = False
    estado["isStrongCandle"] = False
    estado["hasOpposingWick"] = True
    estado["m15Engulfing"] = False
    estado["regionRespected"] = False
    estado["velas_espera"] = 0

def processar_vela(estado: dict, vela_m1, df_m15_ate_agora) -> dict | None:
    """
    Máquina de estados iterando sobre cada vela M1 fechada.
    Avalia a estrutura M15 para rompimento, e entra IMEDIATAMENTE no toque do pullback.
    """
    if len(df_m15_ate_agora) < VELAS_SR + 2:
        return None
        
    status = estado["status"]

    if status == WAITING:
        # A última vela fechada M15 é a candidata a rompimento
        vela_rompimento = df_m15_ate_agora.iloc[-1]
        vela_anterior_romp = df_m15_ate_agora.iloc[-2]
        
        # As velas base para o S/R são as 3 anteriores à vela de rompimento
        base_m15 = df_m15_ate_agora.iloc[-(VELAS_SR+1):-1]
        niveis = marcar_niveis(base_m15)
        
        analise_m15 = analisar_candle(vela_rompimento)
        zona = niveis["resistencia"] - niveis["suporte"]
        if zona <= 0:
            return None

        direcao_rompimento = None
        nivel_rompido = None
        ratio = 0.0
        opposing_wick = True

        if analise_m15["isBullish"] and analise_m15["close"] > niveis["resistencia"]:
            direcao_rompimento = "ALTA"
            nivel_rompido = niveis["resistencia"]
            ratio = (analise_m15["close"] - niveis["resistencia"]) / zona
            opposing_wick = analise_m15["hasLowerWick"]
        elif analise_m15["isBearish"] and analise_m15["close"] < niveis["suporte"]:
            direcao_rompimento = "BAIXA"
            nivel_rompido = niveis["suporte"]
            ratio = (niveis["suporte"] - analise_m15["close"]) / zona
            opposing_wick = analise_m15["hasUpperWick"]

        if direcao_rompimento:
            chave_sr = (niveis["suporte"], niveis["resistencia"], direcao_rompimento)
            if estado["ultimo_sr_rompido"] != chave_sr:
                estado["status"] = WAITING_PULLBACK
                estado["breakoutDirection"] = direcao_rompimento
                estado["breakoutLevel"] = nivel_rompido
                estado["breakoutRatio"] = ratio
                estado["isStrongBreakout"] = ratio >= BREAKOUT_THRESHOLD
                estado["isStrongCandle"] = analise_m15["bodyRatio"] >= 0.50
                estado["hasOpposingWick"] = opposing_wick
                
                # Engolfo M15
                engolfo = detectar_engolfo(vela_rompimento, vela_anterior_romp)
                estado["m15Engulfing"] = False
                if direcao_rompimento == "ALTA" and engolfo == "BULLISH_ENGULFING":
                    estado["m15Engulfing"] = True
                elif direcao_rompimento == "BAIXA" and engolfo == "BEARISH_ENGULFING":
                    estado["m15Engulfing"] = True
                    
                # Região respeitada: alguma das 3 velas base deixou pavio tocando/ultrapassando a zona?
                respeitou = False
                for i in range(len(base_m15)):
                    v = base_m15.iloc[i]
                    if direcao_rompimento == "ALTA" and v["high"] >= niveis["resistencia"]:
                        respeitou = True
                    if direcao_rompimento == "BAIXA" and v["low"] <= niveis["suporte"]:
                        respeitou = True
                estado["regionRespected"] = respeitou
                
                estado["velas_espera"] = 0
                estado["ultimo_sr_rompido"] = chave_sr
        return None

    if status == WAITING_PULLBACK:
        estado["velas_espera"] += 1
        
        direcao = estado["breakoutDirection"]
        nivel = estado["breakoutLevel"]
        
        # Invalidação se o M1 fechar rompendo a zona pro lado errado
        if direcao == "ALTA" and vela_m1["close"] < nivel:
            _reset(estado)
            return None
        if direcao == "BAIXA" and vela_m1["close"] > nivel:
            _reset(estado)
            return None
            
        if estado["velas_espera"] > TIMEOUT_VELAS_M1:
            _reset(estado)
            return None

        # Toque exato (Pullback): M1 cruza ou toca a linha
        tolerancia = nivel * PULLBACK_TOLERANCE
        tocou = False
        if direcao == "ALTA":
            tocou = vela_m1["low"] <= nivel + tolerancia
        elif direcao == "BAIXA":
            tocou = vela_m1["high"] >= nivel - tolerancia

        if tocou:
            # Não espera fechar M1, já avalia o sinal IMEDIATAMENTE no toque
            resultado = avaliar_sinal(estado)
            _reset(estado)
            if resultado["signal"] != "NO_TRADE":
                return resultado

    return None
