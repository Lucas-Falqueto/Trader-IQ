import os
import sys
import pandas as pd
from datetime import datetime

from core.data import conectar, buscar_candles_historico
from price_limit_strategy.signal_engine import run as run_signal_engine
from price_limit_strategy.candle_utils import calcular_tamanho_medio
from main_limit import df_para_candles
from core.config import IQ_EMAIL, IQ_PASSWORD

def extract_features(sinal, candles_puros):
    idx = sinal.candle_idx
    vela_gatilho = candles_puros[idx]
    
    atr = calcular_tamanho_medio(candles_puros[:idx], lookback=10)
    if atr == 0: atr = 0.00001
    
    tamanho_canal = 0.0
    if "Canal" in sinal.descricao:
        try:
            coords = sinal.descricao.split("Canal ")[1].replace(")", "").split("-")
            tamanho_canal = abs(float(coords[0]) - float(coords[1]))
        except:
            pass
            
    tamanho_canal_pct_atr = tamanho_canal / atr
    distancia_sma = abs(vela_gatilho.close - vela_gatilho.sma)
    distancia_sma_pct_atr = distancia_sma / atr
    
    def calc_corpo_pct(vela):
        total = vela.high - vela.low
        if total == 0: return 0
        return abs(vela.close - vela.open) / total
    
    def direcao_favor(vela, dir_trade):
        if dir_trade == "CALL":
            return 1 if vela.is_bullish else -1
        else:
            return 1 if vela.is_bearish else -1

    aceleracao_contra = 0
    for i in range(idx - 1, max(0, idx - 10), -1):
        if direcao_favor(candles_puros[i], sinal.direcao) == -1:
            aceleracao_contra += 1
        else:
            break

    return {
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

print("Conectando IQ...")
api = conectar(IQ_EMAIL, IQ_PASSWORD)
ativos = ["EURUSD-OTC", "SP35-OTC", "JP225-OTC"]
dataset = []

for ativo in ativos:
    print(f"Analisando {ativo}...")
    df_m1 = buscar_candles_historico(api, ativo, 60, 10 * 24 * 60)
    df_m15 = buscar_candles_historico(api, ativo, 900, int(10 * 24 * 4))
    
    df_m1["sma"] = df_m1["close"].rolling(window=100).mean().fillna(0)
    df_m1["sma20"] = df_m1["close"].rolling(window=20).mean().fillna(0)
    df_m15["sma10"] = df_m15["close"].rolling(window=10).mean().fillna(0)
    
    df_m15_sorted = df_m15[['ts', 'close', 'sma10']].sort_values('ts').rename(columns={'close': 'close_m15'})
    df_m1_sorted = df_m1.sort_values('ts')
    df_m1 = pd.merge_asof(df_m1_sorted, df_m15_sorted, on='ts', direction='backward')
    
    delta = df_m1["close"].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    df_m1["rsi"] = 100 - (100 / (1 + rs))
    df_m1["rsi"] = df_m1["rsi"].fillna(50)
    
    candles_puros = df_para_candles(df_m1)
    sinais_gerados = run_signal_engine(candles_puros)
    
    for s in sinais_gerados:
        if s.tipo == "tipo2" or not s.alta_confianca:
            continue
            
        idx = s.candle_idx
        vela_gatilho = candles_puros[idx]
        hora = datetime.fromtimestamp(vela_gatilho.timestamp).hour
        if hora >= 23 or hora < 7:
            continue
            
        row_original = df_m1.iloc[idx]
        close_m15 = float(row_original.get("close_m15", 0))
        sma_m15 = float(row_original.get("sma10", 0))
        macro_bearish = close_m15 < sma_m15 and sma_m15 > 0
        macro_bullish = close_m15 > sma_m15 and sma_m15 > 0
        if s.direcao == "CALL" and macro_bearish: continue
        if s.direcao == "PUT" and macro_bullish: continue
        
        atr = calcular_tamanho_medio(candles_puros[:idx], lookback=10)
        if atr == 0: atr = 0.00001
        distancia_sma = abs(vela_gatilho.close - vela_gatilho.sma)
        if (distancia_sma / atr) > 6.5: continue
        
        tamanho_canal = 0.0
        if "Canal" in s.descricao:
            try:
                coords = s.descricao.split("Canal ")[1].replace(")", "").split("-")
                tamanho_canal = abs(float(coords[0]) - float(coords[1]))
            except: pass
        if tamanho_canal > 0 and (tamanho_canal / atr) > 4.0: continue

        passou_indicador = False
        if s.direcao == "CALL":
            if vela_gatilho.close > vela_gatilho.sma and vela_gatilho.rsi < 80:
                passou_indicador = True
                if idx >= 2:
                    if candles_puros[idx-1].is_bearish and candles_puros[idx-2].is_bearish: passou_indicador = False
        else:
            if vela_gatilho.close < vela_gatilho.sma and vela_gatilho.rsi > 20:
                passou_indicador = True
                if idx >= 2:
                    if candles_puros[idx-1].is_bullish and candles_puros[idx-2].is_bullish: passou_indicador = False
                    
        if passou_indicador and idx >= 1:
            vela_anterior = candles_puros[idx - 1]
            tam_ant = vela_anterior.high - vela_anterior.low
            corpo_pct_ant = abs(vela_anterior.close - vela_anterior.open) / tam_ant if tam_ant > 0 else 0
            if corpo_pct_ant <= 0.01: passou_indicador = False
            
            tam_gatilho = vela_gatilho.high - vela_gatilho.low
            corpo_pct_gatilho = abs(vela_gatilho.close - vela_gatilho.open) / tam_gatilho if tam_gatilho > 0 else 0
            if corpo_pct_gatilho > 0.90: passou_indicador = False

        if not passou_indicador:
            continue
            
        win_found = False
        idx_alvo = idx + 1
        for _ in range(3):
            if idx_alvo < len(candles_puros):
                vela = candles_puros[idx_alvo]
                if (s.direcao == "CALL" and vela.is_bullish) or (s.direcao == "PUT" and vela.is_bearish):
                    win_found = True
                    break
            idx_alvo += 1
            
        feat = extract_features(s, candles_puros)
        feat['resultado'] = 1 if win_found else 0
        dataset.append(feat)

df = pd.DataFrame(dataset)
df.to_csv("dataset_xgboost_filtered.csv", index=False)
print(f"Salvo {len(df)} entradas ultra-filtradas (Losses: {len(df[df['resultado']==0])})")
