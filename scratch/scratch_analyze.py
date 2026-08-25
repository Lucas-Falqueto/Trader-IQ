import time
from datetime import datetime
from core.config import IQ_EMAIL, IQ_PASSWORD
from core.data import conectar, buscar_candles
import pandas as pd

api = conectar(IQ_EMAIL, IQ_PASSWORD)

def calcular_indicadores(df: pd.DataFrame) -> pd.DataFrame:
    df["sma"] = df["close"].rolling(window=100).mean().fillna(0)
    df["sma20"] = df["close"].rolling(window=20).mean().fillna(0)
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    df["rsi"] = (100 - (100 / (1 + rs))).fillna(50)
    return df

print("="*50)
for ativo in ["AUDJPY-OTC", "DOLLARINDEX"]:
    df = buscar_candles(api, ativo, 60, 150)
    df = calcular_indicadores(df)
    
    for idx, row in df.iterrows():
        ts = int(row.get("ts", 0))
        if ts == 0: continue
        dt = datetime.fromtimestamp(ts)
        
        # Filtra os horários que o bot acusou bloqueio
        if dt.hour == 20 and dt.minute in [54, 55, 56, 57, 58, 59]:
            print(f"[{ativo}] {dt.strftime('%H:%M:%S')} - Close: {row['close']:.6f} | SMA 100: {row['sma']:.6f} | RSI: {row['rsi']:.1f}")
            
            # Análise de aceleração (força das velas anteriores)
            if idx >= 3:
                c1 = df.iloc[idx-1]
                c2 = df.iloc[idx-2]
                c3 = df.iloc[idx-3]
                
                print(f"   Vela anterior (t-1): {'ALTA' if c1['close'] >= c1['open'] else 'BAIXA'}")
                print(f"   Vela anterior (t-2): {'ALTA' if c2['close'] >= c2['open'] else 'BAIXA'}")
                print(f"   Vela anterior (t-3): {'ALTA' if c3['close'] >= c3['open'] else 'BAIXA'}")
                print("-" * 30)
