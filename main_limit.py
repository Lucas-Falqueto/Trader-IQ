import time
import logging
import argparse
import csv
import os
import pandas as pd
from datetime import datetime
from data import conectar, buscar_candles
from executor import executar_ordem
from config import (
    IQ_EMAIL, IQ_PASSWORD, ATIVO,
    MAX_PERDAS_SEGUIDAS, STOP_LOSS_DIARIO, META_DIARIA, VALOR_ENTRADA, PAYOUT_MINIMO,
    USAR_GALE, MAX_GALES, FATOR_GALE
)

from price_limit_strategy.models import Candle
from price_limit_strategy.signal_engine import run as run_signal_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

def aguardar_proximo_minuto():
    agora = time.time()
    segundos = 60 - (agora % 60)
    time.sleep(segundos + 1)

def registrar_trade_csv(ativo, direcao, gale_nivel, valor_investido, lucro_final, status):
    os.makedirs(os.path.join("resultados", "live_limit"), exist_ok=True)
    filename = os.path.join("resultados", "live_limit", f"trades_live_{ativo}.csv")
    file_exists = os.path.isfile(filename)
    with open(filename, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Data", "Ativo", "Direcao", "Gale", "Valor", "Lucro", "Status"])
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ativo,
            direcao,
            gale_nivel,
            round(valor_investido, 2),
            round(lucro_final, 2),
            status
        ])

def calcular_indicadores(df: pd.DataFrame) -> pd.DataFrame:
    df["sma"] = df["close"].rolling(window=100).mean().fillna(0)
    df["sma20"] = df["close"].rolling(window=20).mean().fillna(0)
    
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    df["rsi"] = (100 - (100 / (1 + rs))).fillna(50)
    return df

def df_para_candles(df: pd.DataFrame) -> list[Candle]:
    candles_puros = []
    for idx, row in df.iterrows():
        candles_puros.append(Candle(
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            timestamp=int(row["ts"]) if "ts" in row else idx,
            rsi=float(row["rsi"]),
            sma=float(row["sma"]),
            sma20=float(row["sma20"])
        ))
    return candles_puros

def main(dry_run: bool):
    logger.info(f"Iniciando bot Limit Strategy | ativo={ATIVO} | dry_run={dry_run}")
    api = conectar(IQ_EMAIL, IQ_PASSWORD)

    perdas_seguidas = 0
    resultado_dia = 0.0
    ultimo_ts = None

    while True:
        if perdas_seguidas >= MAX_PERDAS_SEGUIDAS:
            logger.warning(f"Stop por {MAX_PERDAS_SEGUIDAS} perdas seguidas. Encerrando.")
            break

        if resultado_dia <= -STOP_LOSS_DIARIO:
            logger.warning(f"Stop loss diário de ${STOP_LOSS_DIARIO} atingido. Encerrando.")
            break

        if resultado_dia >= META_DIARIA:
            logger.info(f"Meta diária de ${META_DIARIA} atingida. Encerrando.")
            break

        try:
            # Busca 150 velas para garantir histórico suficiente para SMA 100 e Lotes
            df_m1 = buscar_candles(api, ATIVO, 60, 150) 
        except Exception as e:
            logger.error(f"Erro ao buscar candles: {e}")
            aguardar_proximo_minuto()
            continue

        vela_atual = df_m1.iloc[-2] # A penúltima vela é a que acabou de fechar

        if ultimo_ts == vela_atual["ts"]:
            aguardar_proximo_minuto()
            continue
            
        ultimo_ts = vela_atual["ts"]
        logger.info(f"Analisando fechamento... | Ativo: {ATIVO}")

        df_m1 = calcular_indicadores(df_m1)
        
        # Consideramos apenas até a penúltima vela (vela_atual) para gerar o sinal
        df_historico = df_m1.iloc[:-1].copy()
        
        candles = df_para_candles(df_historico)
        sinais = run_signal_engine(candles)
        
        ultimo_idx = len(candles) - 1
        sinal_valido = None
        
        for s in sinais:
            if s.candle_idx == ultimo_idx and s.alta_confianca and s.tipo != "tipo2":
                sinal_valido = s
                break
                
        if not sinal_valido:
            aguardar_proximo_minuto()
            continue

        # Filtros de horário e indicadores
        vela_gatilho = candles[ultimo_idx]
        hora = datetime.fromtimestamp(vela_gatilho.timestamp).hour

        passou_indicador = False
        is_supernova = False

        if sinal_valido.direcao == "CALL":
            if vela_gatilho.close > vela_gatilho.sma and vela_gatilho.rsi < 80:
                passou_indicador = True
                # Filtro de Aceleração: 2 velas fortes contrárias = sem espaço para a operação
                if ultimo_idx >= 2:
                    c1 = candles[ultimo_idx - 1]
                    c2 = candles[ultimo_idx - 2]
                    if c1.is_bearish and c2.is_bearish:
                        passou_indicador = False
                if passou_indicador and vela_gatilho.rsi >= 65:
                    is_supernova = True
        else:
            if vela_gatilho.close < vela_gatilho.sma and vela_gatilho.rsi > 20:
                passou_indicador = True
                # Filtro de Aceleração: 2 velas fortes contrárias = sem espaço para a operação
                if ultimo_idx >= 2:
                    c1 = candles[ultimo_idx - 1]
                    c2 = candles[ultimo_idx - 2]
                    if c1.is_bullish and c2.is_bullish:
                        passou_indicador = False
                if passou_indicador and vela_gatilho.rsi <= 35:
                    is_supernova = True

        if not passou_indicador:
            logger.info(f"SINAL BLOQUEADO (SMA/RSI) -> {sinal_valido.direcao} | RSI: {vela_gatilho.rsi:.1f}")
            aguardar_proximo_minuto()
            continue

        if hora in [0, 10, 15, 13, 23, 4, 20]:
            if is_supernova:
                logger.info(f"FURA-BLOQUEIO ATIVADO! Sinal SUPERNOVA detectado às {hora}h | Direção: {sinal_valido.direcao} | RSI: {vela_gatilho.rsi:.1f}")
            else:
                logger.info(f"SINAL BLOQUEADO (Horário da Morte): {hora}h | Possível Sinal: {sinal_valido.direcao} ({sinal_valido.tipo})")
                registrar_trade_csv(ATIVO, sinal_valido.direcao, 0, 0.0, 0.0, "BLOQUEADO_HORA")
                aguardar_proximo_minuto()
                continue

        direcao = sinal_valido.direcao
        descricao = sinal_valido.descricao
        
        logger.info(f"SINAL SNIPER APROVADO: {direcao} | Tipo: {sinal_valido.tipo} | {descricao}")
        
        gale_atual = 0
        valor_atual = VALOR_ENTRADA
        lucro_trade_acumulado = 0.0
        valor_investido_acumulado = 0.0
        status_final = ""
        limite_gales = MAX_GALES if USAR_GALE else 0

        while gale_atual <= limite_gales:
            if gale_atual > 0:
                logger.info(f"Entrando com GALE {gale_atual} | Direção: {direcao} | Valor: ${valor_atual:.2f}")
            
            resultado = executar_ordem(api, direcao, valor_atual, dry_run=dry_run)
            status_final = resultado["resultado"]
            
            if status_final == "win":
                lucro = resultado.get("lucro") or (valor_atual * PAYOUT_MINIMO)
                lucro_trade_acumulado += lucro
                valor_investido_acumulado += valor_atual
                
                resultado_dia += lucro_trade_acumulado
                perdas_seguidas = 0
                logger.info(f"WIN +${lucro_trade_acumulado:.2f} | Dia: ${resultado_dia:.2f}")
                break
                
            elif status_final == "lose":
                lucro_trade_acumulado -= valor_atual
                valor_investido_acumulado += valor_atual
                logger.info(f"LOSS -${valor_atual:.2f}")
                
                gale_atual += 1
                if gale_atual <= limite_gales:
                    valor_atual = valor_atual * FATOR_GALE
                else:
                    resultado_dia += lucro_trade_acumulado
                    perdas_seguidas += 1
                    logger.info(f"FIM DOS GALES | Prejuízo: ${lucro_trade_acumulado:.2f} | Dia: ${resultado_dia:.2f}")
                    break
                    
            elif status_final == "timeout":
                lucro_trade_acumulado -= valor_atual
                valor_investido_acumulado += valor_atual
                resultado_dia += lucro_trade_acumulado
                logger.warning("TIMEOUT. Ciclo abortado.")
                break
                    
            elif status_final == "tie":
                logger.info("Empate (TIE). Dinheiro devolvido.")
                valor_investido_acumulado += valor_atual
                resultado_dia += lucro_trade_acumulado
                break
            
            elif status_final == "simulado":
                logger.info("Ordem simulada registrada (dry-run).")
                break
                
            else:
                logger.warning(f"Ordem falhou com status: {status_final}")
                resultado_dia += lucro_trade_acumulado
                break

        registrar_trade_csv(ATIVO, direcao, min(gale_atual, limite_gales), valor_investido_acumulado, lucro_trade_acumulado, status_final)
        logger.info("Voltando a monitorar...")
        aguardar_proximo_minuto()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bot IQ Option — Price Limit Strategy")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula ordens sem enviar API",
    )
    args = parser.parse_args()
    main(dry_run=args.dry_run)
