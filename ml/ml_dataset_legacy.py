import os
import sys
import pandas as pd
from datetime import datetime

from iqoptionapi.stable_api import IQ_Option
from core.config import IQ_EMAIL, IQ_PASSWORD, ACCOUNT_TYPE, VELAS_SR
from core.data import buscar_candles_historico
from core.engine import novo_estado, processar_vela
from core.levels import marcar_niveis

class SuppressOutput:
    def __enter__(self):
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr

def rodar_extracao_legacy():
    ativos = ["GER30-OTC", "AUS200-OTC"]
    dias = 20
    count_velas = dias * 24 * 60

    print("Conectando à IQ Option...")
    with SuppressOutput():
        api = IQ_Option(IQ_EMAIL, IQ_PASSWORD)
        api.connect()
        api.change_balance(ACCOUNT_TYPE)

    dataset = []

    for ativo in ativos:
        print(f"\nBaixando {count_velas} velas de {ativo}...")
        df_m1 = buscar_candles_historico(api, ativo, 60, count_velas, lote=1000)
        df_m15 = buscar_candles_historico(api, ativo, 900, int(count_velas / 15), lote=1000)
        
        if df_m1.empty or df_m15.empty:
            continue
            
        print(f"[{ativo}] Processando motor legado de S/R...")
        
        estado = novo_estado()
        
        for i in range(len(df_m1)):
            vela_m1 = df_m1.iloc[i]
            ts_m1 = vela_m1["ts"]

            m15_ate_agora = df_m15[df_m15["ts"] < ts_m1]
            if len(m15_ate_agora) < VELAS_SR + 1:
                continue

            resultado_sinal = processar_vela(estado, vela_m1, m15_ate_agora)
            if resultado_sinal is None or resultado_sinal["signal"] == "NO_TRADE":
                continue
                
            # SINAL GERADO
            direcao = resultado_sinal["signal"]
            
            # Verificar Win/Loss G0/G1/G2
            win_found = False
            idx_alvo = i + 1
            
            # G0
            if idx_alvo < len(df_m1):
                vela_res = df_m1.iloc[idx_alvo]
                if (direcao == "CALL" and vela_res["close"] > vela_res["open"]) or (direcao == "PUT" and vela_res["close"] < vela_res["open"]):
                    win_found = True
            
            # G1
            if not win_found:
                idx_alvo += 1
                if idx_alvo < len(df_m1):
                    vela_res = df_m1.iloc[idx_alvo]
                    if (direcao == "CALL" and vela_res["close"] > vela_res["open"]) or (direcao == "PUT" and vela_res["close"] < vela_res["open"]):
                        win_found = True
                        
            # G2
            if not win_found:
                idx_alvo += 1
                if idx_alvo < len(df_m1):
                    vela_res = df_m1.iloc[idx_alvo]
                    if (direcao == "CALL" and vela_res["close"] > vela_res["open"]) or (direcao == "PUT" and vela_res["close"] < vela_res["open"]):
                        win_found = True
            
            # Montar Features
            feat = {
                'ativo': ativo,
                'hora': datetime.fromtimestamp(ts_m1).hour,
                'direcao': 1 if direcao == "CALL" else -1,
                'score': resultado_sinal["score"],
                'velas_espera': estado.get("velas_espera", 0),
                'isStrongBreakout': 1 if estado.get("isStrongBreakout", False) else 0,
                'isStrongCandle': 1 if estado.get("isStrongCandle", False) else 0,
                'hasOpposingWick': 1 if estado.get("hasOpposingWick", False) else 0,
                'm15Engulfing': 1 if estado.get("m15Engulfing", False) else 0,
                'regionRespected': 1 if estado.get("regionRespected", False) else 0,
                'alvo_win': 1 if win_found else 0
            }
            dataset.append(feat)
            
            # Resetar estado após emitir sinal
            estado = novo_estado()

    df_final = pd.DataFrame(dataset)
    os.makedirs('resultados', exist_ok=True)
    df_final.to_csv('resultados/ml_dataset_legacy.csv', index=False)
    
    wins = len(df_final[df_final['alvo_win'] == 1])
    losses = len(df_final[df_final['alvo_win'] == 0])
    
    print(f"\nDataset Legado Gerado! {len(df_final)} sinais salvos.")
    print(f"Wins (G0/G1/G2): {wins}")
    print(f"Losses Fatais: {losses}")

if __name__ == "__main__":
    rodar_extracao_legacy()
