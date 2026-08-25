import os
import sys
import time
import pandas as pd
from datetime import datetime

from iqoptionapi.stable_api import IQ_Option
from core.config import IQ_EMAIL, IQ_PASSWORD, ACCOUNT_TYPE
from core.data import buscar_candles_historico
from price_limit_strategy.candle_utils import calcular_tamanho_medio
from main_limit import df_para_candles
from price_limit_strategy.signal_engine import run as run_signal_engine

# Suprime prints da IQ Option
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

def extrair_features(sinal, candles_puros):
    idx = sinal.candle_idx
    vela_gatilho = candles_puros[idx]
    
    # ATR local (10 velas)
    atr = calcular_tamanho_medio(candles_puros[:idx], lookback=10)
    if atr == 0: atr = 0.00001 # Prevenir div/0
    
    # Extrair Tamanho do Canal a partir da descricao "RETRAÇÃO (Canal 1.10230-1.10210)"
    try:
        coords = sinal.descricao.split("Canal ")[1].replace(")", "").split("-")
        tamanho_canal = abs(float(coords[0]) - float(coords[1]))
    except:
        tamanho_canal = 0.0001
        
    tamanho_canal_pct_atr = tamanho_canal / atr
    
    # Distância para SMA
    distancia_sma = abs(vela_gatilho.close - vela_gatilho.sma)
    distancia_sma_pct_atr = distancia_sma / atr
    
    # Corpo Vela Gatilho
    def calc_corpo_pct(vela):
        total = vela.high - vela.low
        if total == 0: return 0
        return abs(vela.close - vela.open) / total
    
    # Direção a Favor
    def direcao_favor(vela, dir_trade):
        if dir_trade == "CALL":
            return 1 if vela.is_bullish else -1
        else:
            return 1 if vela.is_bearish else -1

    # Aceleração Contrária (quantas velas contrárias seguidas antes do gatilho)
    aceleracao_contra = 0
    for i in range(idx - 1, max(0, idx - 10), -1):
        if direcao_favor(candles_puros[i], sinal.direcao) == -1:
            aceleracao_contra += 1
        else:
            break

    features = {
        'hora': datetime.fromtimestamp(vela_gatilho.timestamp).hour,
        'tipo_sinal': 0 if sinal.tipo == 'retracao' else 1,
        'direcao': 1 if sinal.direcao == 'CALL' else -1,
        'tamanho_canal_pct_atr': tamanho_canal_pct_atr,
        'distancia_sma_pct_atr': distancia_sma_pct_atr,
        'rsi': vela_gatilho.rsi,
        'vela_gatilho_corpo_pct': calc_corpo_pct(vela_gatilho),
        'aceleracao_velas_contra': aceleracao_contra,
        'vela_1_antes_corpo_pct': calc_corpo_pct(candles_puros[idx-1]) if idx >= 1 else 0,
        'vela_1_antes_favor': direcao_favor(candles_puros[idx-1], sinal.direcao) if idx >= 1 else 0,
        'vela_2_antes_corpo_pct': calc_corpo_pct(candles_puros[idx-2]) if idx >= 2 else 0,
        'vela_2_antes_favor': direcao_favor(candles_puros[idx-2], sinal.direcao) if idx >= 2 else 0,
    }
    return features

def rodar_extracao():
    ativos = ["SP35-OTC", "JP225-OTC", "EURUSD-OTC", "AUDJPY-OTC"]
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
        df = buscar_candles_historico(api, ativo, 60, count_velas, lote=1000)
        if df.empty:
            continue
        
        from main_limit import calcular_indicadores
        df = calcular_indicadores(df)
        candles_puros = df_para_candles(df)
        
        print(f"[{ativo}] Processando motor de sinais...")
        sinais_gerados = run_signal_engine(candles_puros)
        
        # Filtramos Tipo 2, pois não operamos. Mas mantemos TODOS os Sinais de Alta Confiança originais (com ou sem filtro nosso).
        # Vamos pegar até sinais que não passaram no nosso filtro de aceleração para a IA aprender a importância dele.
        for s in sinais_gerados:
            if s.tipo == "tipo2" or not s.alta_confianca:
                continue
                
            idx = s.candle_idx
            
            # Simular Resultado (G0, G1, G2)
            win_found = False
            idx_alvo = idx + 1
            
            # G0
            if idx_alvo < len(candles_puros):
                vela = candles_puros[idx_alvo]
                if (s.direcao == "CALL" and vela.is_bullish) or (s.direcao == "PUT" and vela.is_bearish):
                    win_found = True
            
            # G1
            if not win_found:
                idx_alvo += 1
                if idx_alvo < len(candles_puros):
                    vela = candles_puros[idx_alvo]
                    if (s.direcao == "CALL" and vela.is_bullish) or (s.direcao == "PUT" and vela.is_bearish):
                        win_found = True
                        
            # G2
            if not win_found:
                idx_alvo += 1
                if idx_alvo < len(candles_puros):
                    vela = candles_puros[idx_alvo]
                    if (s.direcao == "CALL" and vela.is_bullish) or (s.direcao == "PUT" and vela.is_bearish):
                        win_found = True
            
            feat = extrair_features(s, candles_puros)
            feat['ativo'] = ativo
            feat['alvo_win'] = 1 if win_found else 0
            
            dataset.append(feat)

    df_final = pd.DataFrame(dataset)
    
    os.makedirs('resultados', exist_ok=True)
    df_final.to_csv('resultados/ml_dataset.csv', index=False)
    print(f"\nDataset gerado! {len(df_final)} sinais salvos em 'resultados/ml_dataset.csv'.")
    wins = len(df_final[df_final['alvo_win'] == 1])
    losses = len(df_final[df_final['alvo_win'] == 0])
    print(f"Wins (G0/G1/G2): {wins}")
    print(f"Losses Fatais: {losses}")

if __name__ == "__main__":
    rodar_extracao()
