"""
main.py — Loop principal do bot de pullback.

Modos:
  python main.py           → modo live (PRACTICE), executa ordens na conta demo
  python main.py --dry-run → modo simulação, não envia nenhuma ordem
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import time
import logging
import argparse
import csv
import os
from datetime import datetime
from core.data import conectar, buscar_candles
from core.levels import marcar_niveis
from core.engine import novo_estado, processar_vela
from core.executor import executar_ordem
from core.config import (
    IQ_EMAIL, IQ_PASSWORD, ATIVO,
    MAX_PERDAS_SEGUIDAS, STOP_LOSS_DIARIO, META_DIARIA, VALOR_ENTRADA, PAYOUT_MINIMO,
    USAR_GALE, MAX_GALES, FATOR_GALE, VELAS_SR
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

def aguardar_proximo_minuto():
    """Calcula os segundos exatos até a virada do minuto e dorme até lá (+1s de margem)."""
    agora = time.time()
    segundos = 60 - (agora % 60)
    time.sleep(segundos + 1)

def registrar_trade_csv(ativo, direcao, gale_nivel, valor_investido, lucro_final, status):
    os.makedirs(os.path.join("resultados", "live"), exist_ok=True)
    filename = os.path.join("resultados", "live", f"trades_live_{ativo}.csv")
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


def main(dry_run: bool):
    logger.info(f"Iniciando bot | ativo={ATIVO} | dry_run={dry_run}")
    api = conectar(IQ_EMAIL, IQ_PASSWORD)

    perdas_seguidas = 0
    resultado_dia = 0.0
    estado = novo_estado()
    ultimo_ts = None
    warmup_feito = False

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
            df_m15 = buscar_candles(api, ATIVO, 900, 10)
            df_m1 = buscar_candles(api, ATIVO, 60, 120)
        except Exception as e:
            logger.error(f"Erro ao buscar candles: {e}")
            aguardar_proximo_minuto()
            continue

        if not warmup_feito:
            logger.info("Aquecendo a memória do robô com o histórico recente (Warmup)...")
            # Pega as últimas 90 velas e passa na engine para reconstruir o estado
            for i in range(max(VELAS_SR + 1, len(df_m1) - 90), len(df_m1) - 1):
                vela_hist = df_m1.iloc[i]
                ts_hist = vela_hist["ts"]
                m15_hist = df_m15[df_m15["ts"] < ts_hist]
                if len(m15_hist) >= VELAS_SR + 1: # Garante contexto M15 suficiente
                    processar_vela(estado, vela_hist, m15_hist)
            
            warmup_feito = True
            logger.info(f"Warmup concluído! Status atual da engine: {estado['status']}")

        df_m15_ate_agora = df_m15.iloc[:-1]
        vela_atual = df_m1.iloc[-2]

        if ultimo_ts == vela_atual["ts"]:
            aguardar_proximo_minuto()
            continue
        ultimo_ts = vela_atual["ts"]

        logger.info(f"Monitorando... | Status: {estado['status']} | Ativo: {ATIVO}")

        resultado_sinal = processar_vela(estado, vela_atual, df_m15_ate_agora)
        if resultado_sinal is None or resultado_sinal["signal"] == "NO_TRADE":
            aguardar_proximo_minuto()
            continue

        direcao = resultado_sinal["signal"]
        score = resultado_sinal["score"]
        reasons = ", ".join(resultado_sinal["reasons"])
        
        logger.info(f"SINAL GERADO: {direcao} | Score: {score}/8 | Motivos: {reasons}")
        
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
                    resultado_dia += lucro_trade_acumulado # Será negativo
                    perdas_seguidas += 1
                    logger.info(f"FIM DOS GALES | Prejuízo Total: ${lucro_trade_acumulado:.2f} | Dia: ${resultado_dia:.2f} | Seguidas: {perdas_seguidas}")
                    break
                    
            elif status_final == "timeout":
                lucro_trade_acumulado -= valor_atual
                valor_investido_acumulado += valor_atual
                resultado_dia += lucro_trade_acumulado
                logger.warning("TIMEOUT: Não foi possível validar o Win a tempo. Ciclo de Gale abortado para não pegar a vela errada atrasado!")
                break
                    
            elif status_final == "tie":
                logger.info("Empate (TIE). Dinheiro devolvido. Encerrando ciclo de entrada.")
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

        # Ao final de um trade, resetamos a memória da engine para evitar usar níveis fantasmas
        estado = novo_estado()
        ultimo_ts = None
        warmup_feito = False
        logger.info("Memória da engine resetada. Refazendo Warmup na próxima vela...")
        aguardar_proximo_minuto()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bot IQ Option — Estratégia Pullback")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula ordens sem enviar para a API (recomendado para testes iniciais)",
    )
    args = parser.parse_args()
    main(dry_run=args.dry_run)
