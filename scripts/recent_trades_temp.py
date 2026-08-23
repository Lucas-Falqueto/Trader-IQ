import os
import pandas as pd
from datetime import datetime, timezone, timedelta
import logging
from data import conectar, buscar_candles_historico
from engine import novo_estado, processar_vela
from config import IQ_EMAIL, IQ_PASSWORD, VELAS_SR
from run_all import ATIVOS_PARA_RODAR

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Buscar apenas o último 1 dia para ser rápido
CANDLES_M1 = 1 * 24 * 60
CANDLES_M15 = 1 * 24 * 4

def rodar_pesquisa_rapida():
    logger.info("Conectando para buscar dados recentes...")
    api = conectar(IQ_EMAIL, IQ_PASSWORD)

    # Horário alvo (hoje às 11:49)
    # tz = -3
    hoje_agora = datetime.now(tz=timezone(timedelta(hours=-3)))
    alvo_inicio = hoje_agora.replace(hour=11, minute=49, second=0, microsecond=0)
    ts_alvo_inicio = alvo_inicio.timestamp()

    for ativo in ATIVOS_PARA_RODAR:
        logger.info(f"\nVerificando {ativo}...")
        try:
            df_m15 = buscar_candles_historico(api, ativo, 900, CANDLES_M15)
            df_m1 = buscar_candles_historico(api, ativo, 60, CANDLES_M1)
        except Exception as e:
            logger.error(f"Erro ao baixar dados de {ativo}: {e}")
            continue

        estado = novo_estado()
        sinais_encontrados = []

        for i in range(VELAS_SR + 1, len(df_m1)):
            vela_m1 = df_m1.iloc[i]
            ts_m1 = vela_m1["ts"]

            m15_ate_agora = df_m15[df_m15["ts"] < ts_m1]
            if len(m15_ate_agora) < VELAS_SR + 1:
                continue

            resultado_sinal = processar_vela(estado, vela_m1, m15_ate_agora)
            
            if resultado_sinal is not None and resultado_sinal["signal"] != "NO_TRADE":
                if ts_m1 >= ts_alvo_inicio:
                    hora_sinal = datetime.fromtimestamp(ts_m1, tz=timezone(timedelta(hours=-3))).strftime("%H:%M:%S")
                    sinais_encontrados.append(f"{hora_sinal} - {resultado_sinal['signal']}")

        if sinais_encontrados:
            logger.info(f"💰 SINAIS ENCONTRADOS em {ativo} desde as 11:49:")
            for s in sinais_encontrados:
                logger.info(f"   -> {s}")
        else:
            logger.info(f"Nenhum sinal desde as 11:49 para {ativo}.")

if __name__ == "__main__":
    rodar_pesquisa_rapida()
