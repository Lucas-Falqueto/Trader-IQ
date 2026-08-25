"""
backtest.py — Roda a estratégia pullback sobre dados históricos sem enviar ordens.

Uso:
    python backtest.py

Saída:
    Relatório no terminal com total de sinais, taxa de acerto vs break-even
    de payout, e resumo financeiro usando VALOR_ENTRADA e PAYOUT_MINIMO.
"""

import pandas as pd
import os
from datetime import datetime, timezone, timedelta
import logging
from core.data import conectar, buscar_candles_historico
from core.engine import novo_estado, processar_vela
from core.config import (
    IQ_EMAIL, IQ_PASSWORD, ATIVO, VALOR_ENTRADA, PAYOUT_MINIMO,
    DIAS_BACKTEST, VELAS_SR, USAR_GALE, MAX_GALES, FATOR_GALE
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

CANDLES_M1 = DIAS_BACKTEST * 24 * 60
CANDLES_M15 = DIAS_BACKTEST * 24 * 4


def rodar_backtest():
    logger.info("Conectando para buscar dados históricos...")
    api = conectar(IQ_EMAIL, IQ_PASSWORD)

    logger.info(f"Baixando ~{DIAS_BACKTEST} dias (M1={CANDLES_M1}, M15={CANDLES_M15})...")
    df_m15 = buscar_candles_historico(api, ATIVO, 900, CANDLES_M15)
    df_m1 = buscar_candles_historico(api, ATIVO, 60, CANDLES_M1)

    logger.info(f"M15: {len(df_m15)} velas | M1: {len(df_m1)} velas")

    entradas = []
    estado = novo_estado()
    skip_until = 0

    for i in range(VELAS_SR + 1, len(df_m1)):
        if i < skip_until:
            continue

        vela_m1 = df_m1.iloc[i]
        ts_m1 = vela_m1["ts"]

        m15_ate_agora = df_m15[df_m15["ts"] < ts_m1]
        if len(m15_ate_agora) < VELAS_SR + 1:
            continue

        resultado_sinal = processar_vela(estado, vela_m1, m15_ate_agora)
        if resultado_sinal is None or resultado_sinal["signal"] == "NO_TRADE":
            continue
            
        if i + 1 >= len(df_m1):
            break

        gale_atual = 0
        valor_atual = VALOR_ENTRADA
        lucro_trade_acumulado = 0.0
        valor_investido_acumulado = 0.0
        resultado_final = "lose"
        
        limite_gales = MAX_GALES if USAR_GALE else 0
        idx_operacao = i + 1

        while gale_atual <= limite_gales and idx_operacao < len(df_m1):
            vela_resultado = df_m1.iloc[idx_operacao]
            win = False
            tie = False
            
            if resultado_sinal["signal"] == "CALL":
                if vela_resultado["close"] > vela_resultado["open"]:
                    win = True
                elif vela_resultado["close"] == vela_resultado["open"]:
                    tie = True
            elif resultado_sinal["signal"] == "PUT":
                if vela_resultado["close"] < vela_resultado["open"]:
                    win = True
                elif vela_resultado["close"] == vela_resultado["open"]:
                    tie = True

            if win:
                lucro = valor_atual * PAYOUT_MINIMO
                lucro_trade_acumulado += lucro
                valor_investido_acumulado += valor_atual
                resultado_final = "win"
                break
            elif tie:
                valor_investido_acumulado += valor_atual
                resultado_final = "tie"
                break
            else:
                lucro_trade_acumulado -= valor_atual
                valor_investido_acumulado += valor_atual
                
                gale_atual += 1
                if gale_atual <= limite_gales:
                    valor_atual = valor_atual * FATOR_GALE
                    idx_operacao += 1
                else:
                    resultado_final = "lose"
                    break
        
        skip_until = idx_operacao

        entradas.append({
            "horario": datetime.fromtimestamp(ts_m1, tz=timezone(timedelta(hours=-3))).strftime("%Y-%m-%d %H:%M"),
            "direcao": resultado_sinal["signal"],
            "score": resultado_sinal["score"],
            "reasons": "|".join(resultado_sinal["reasons"]),
            "gales_usados": min(gale_atual, limite_gales),
            "valor_investido": round(valor_investido_acumulado, 2),
            "lucro_liquido": round(lucro_trade_acumulado, 2),
            "resultado": resultado_final,
        })

    if not entradas:
        logger.info("Nenhum sinal gerado no período analisado.")
        return

    df_result = pd.DataFrame(entradas)
    total = len(df_result)
    wins = int((df_result["resultado"] == "win").sum())
    loses = int((df_result["resultado"] == "lose").sum())
    ties = int((df_result["resultado"] == "tie").sum())
    
    lucro_liquido = df_result["lucro_liquido"].sum()
    taxa = wins / (wins + loses) if (wins + loses) > 0 else 0

    logger.info("\n" + "=" * 50)
    logger.info(f"Ativo analisado : {ATIVO}")
    logger.info(f"Dias pedidos    : {DIAS_BACKTEST}")
    logger.info(f"Velas M1 usadas : {len(df_m1)}")
    logger.info(f"Total de sinais : {total}")
    logger.info(f"Gale Máx Permit : {MAX_GALES if USAR_GALE else 0}")
    logger.info(f"Wins            : {wins}  ({taxa:.1%})")
    logger.info(f"Loses           : {loses}")
    logger.info(f"Empates (Ties)  : {ties}")
    logger.info(f"Lucro líquido   : ${lucro_liquido:.2f}")
    logger.info("=" * 50)

    os.makedirs(os.path.join("resultados", "backtests"), exist_ok=True)
    nome_csv = os.path.join("resultados", "backtests", f"backtest_{ATIVO}_{datetime.now(tz=timezone(timedelta(hours=-3))).strftime('%Y%m%d_%H%M')}.csv")
    df_result.to_csv(nome_csv, index=False)
    logger.info(f"Entradas exportadas: {nome_csv}")

    print("\nTodas as entradas:")
    print(df_result.to_string(index=False))


if __name__ == "__main__":
    rodar_backtest()
