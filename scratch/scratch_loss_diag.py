import os
import glob
import pandas as pd

# Analisa todos os losses fatais (Gale 2 perdido) para encontrar padrões
diretorio = 'resultados/live_limit'
arquivos = glob.glob(os.path.join(diretorio, '*.csv'))

print("=== ANATOMIA DOS LOSSES FATAIS (G2) ===\n")

for arquivo in arquivos:
    df = pd.read_csv(arquivo)
    ativo = os.path.basename(arquivo).replace('trades_live_', '').replace('.csv', '')
    
    losses = df[(df['Status'].str.lower().isin(['lose', 'loss'])) & (df['Gale'] >= 2)]
    
    if losses.empty:
        continue
    
    print(f"[{ativo}] {len(losses)} loss(es) fatal(is):")
    for _, row in losses.iterrows():
        print(f"  {row['Data']} | {row['Direcao']} | Gale:{row['Gale']} | Valor:${row['Valor']} | Lucro:${row['Lucro']}")
    
    # Mostra as operações ao redor do loss para ver contexto temporal
    for _, loss_row in losses.iterrows():
        loss_dt = pd.to_datetime(loss_row['Data'])
        df['dt'] = pd.to_datetime(df['Data'])
        vizinhos = df[(df['dt'] >= loss_dt - pd.Timedelta(minutes=5)) & 
                      (df['dt'] <= loss_dt + pd.Timedelta(minutes=5))]
        if len(vizinhos) > 1:
            print(f"  -> Contexto temporal do loss ({loss_row['Data']}):")
            for _, v in vizinhos.iterrows():
                marker = "<<< LOSS" if v['Data'] == loss_row['Data'] else ""
                print(f"     {v['Data']} | {v['Direcao']} | Gale:{v['Gale']} | {v['Status']} {marker}")
    print()
