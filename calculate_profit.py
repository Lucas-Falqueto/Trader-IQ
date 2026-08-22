import os
import pandas as pd
import glob

diretorio = r"d:\MonteCarlo\resultados\live"
arquivos_csv = glob.glob(os.path.join(diretorio, "*.csv"))

lucro_total = 0.0
total_operacoes = 0
wins = 0
losses = 0

print(f"{'Data/Hora':<20} | {'Ativo':<12} | {'Lucro':<8} | {'Status'}")
print("-" * 55)

for arquivo in arquivos_csv:
    try:
        df = pd.read_csv(arquivo)
        for _, row in df.iterrows():
            # Conta operações finalizadas
            status = str(row.get('Status', '')).lower()
            if status in ['win', 'lose']:
                lucro = float(row.get('Lucro', 0.0))
                lucro_total += lucro
                total_operacoes += 1
                
                if status == 'win':
                    wins += 1
                elif status == 'lose':
                    losses += 1
                
                print(f"{row['Data']:<20} | {row['Ativo']:<12} | ${lucro:<7.2f} | {status.upper()}")
    except Exception as e:
        pass

print("-" * 55)
print(f"Total de Operações : {total_operacoes}")
print(f"Vitórias (Wins)    : {wins}")
print(f"Derrotas (Loses)   : {losses}")
print(f"LUCRO LÍQUIDO TOTAL: ${lucro_total:.2f}")
