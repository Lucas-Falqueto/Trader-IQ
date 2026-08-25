import os
import glob
import pandas as pd

diretorio = 'resultados/live'
arquivos = glob.glob(os.path.join(diretorio, '*.csv'))

lucro_total = 0.0
total_wins = 0
total_losses = 0

print(f"{'ATIVO':<15} | {'WINS':<5} | {'LOSSES':<7} | {'LUCRO'}")
print("-" * 50)

for arquivo in arquivos:
    try:
        df = pd.read_csv(arquivo)
        ativo = os.path.basename(arquivo).replace('trades_live_', '').replace('.csv', '')
        
        # Ignorar bloqueados e pegar wins/losses
        df_validos = df[df['Status'].str.lower().isin(['win', 'lose', 'loss'])]
        
        lucro_ativo = df_validos['Lucro'].sum()
        wins_ativo = len(df_validos[df_validos['Status'].str.lower() == 'win'])
        loss_ativo = len(df_validos[df_validos['Status'].str.lower().isin(['lose', 'loss'])])
        
        lucro_total += lucro_ativo
        total_wins += wins_ativo
        total_losses += loss_ativo
        
        print(f"{ativo:<15} | {wins_ativo:<5} | {loss_ativo:<7} | ${lucro_ativo:.2f}")
    except Exception as e:
        print(f"Erro ao processar {arquivo}: {e}")

print("-" * 50)
print(f"TOTAL GERAL: {total_wins} Wins | {total_losses} Losses | Lucro Líquido: ${lucro_total:.2f}")
