import os
import glob
import pandas as pd

diretorio = 'resultados/live'
arquivos = glob.glob(os.path.join(diretorio, '*.csv'))

lucro_total = 0.0
total_wins = 0
total_losses = 0
g2_convertidos = 0

print(f"{'ATIVO':<15} | {'WINS':<5} | {'LOSSES':<7} | {'LUCRO G1'}")
print("-" * 50)

for arquivo in arquivos:
    try:
        df = pd.read_csv(arquivo)
        ativo = os.path.basename(arquivo).replace('trades_live_', '').replace('.csv', '')
        
        lucro_ativo = 0.0
        wins_ativo = 0
        loss_ativo = 0
        
        for idx, row in df.iterrows():
            status = str(row['Status']).lower()
            if status not in ['win', 'lose', 'loss']:
                continue
                
            gale = int(row['Gale'])
            
            # Se foi WIN
            if status == 'win':
                if gale <= 1:
                    # G0 ou G1 win continua sendo win com o mesmo lucro
                    lucro_ativo += float(row['Lucro'])
                    wins_ativo += 1
                else:
                    # G2 win vira LOSS, pois pararíamos no G1
                    lucro_ativo -= 3.0 # -$1 no G0 e -$2 no G1
                    loss_ativo += 1
                    g2_convertidos += 1
            # Se foi LOSS
            elif status in ['lose', 'loss']:
                # Loss que antes custava 7 agora custa 3
                lucro_ativo -= 3.0
                loss_ativo += 1
                
        lucro_total += lucro_ativo
        total_wins += wins_ativo
        total_losses += loss_ativo
        
        print(f"{ativo:<15} | {wins_ativo:<5} | {loss_ativo:<7} | ${lucro_ativo:.2f}")
    except Exception as e:
        print(f"Erro ao processar {arquivo}: {e}")

print("-" * 50)
print(f"TOTAL SIMULADO: {total_wins} Wins | {total_losses} Losses | Lucro Líquido: ${lucro_total:.2f}")
print(f"OBS: {g2_convertidos} vitórias de G2 foram convertidas em Derrota no teste.")
