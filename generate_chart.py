import pandas as pd
import matplotlib.pyplot as plt
import os

# Caminho do CSV de backtest
csv_path = r"d:\MonteCarlo\resultados\backtests\backtest_JP225-OTC_20260822_1145.csv"

# Ler o CSV
df = pd.read_csv(csv_path)

# Classificar cada operação
def classify_gale(row):
    if row['resultado'] == 'lose':
        return 'Loss (Falha no G2)'
    elif row['resultado'] == 'win':
        if row['gales_usados'] == 0:
            return 'Win de Primeira (G0)'
        elif row['gales_usados'] == 1:
            return 'Win no Gale 1 (G1)'
        elif row['gales_usados'] == 2:
            return 'Win no Gale 2 (G2)'
    return 'Outro'

df['categoria'] = df.apply(classify_gale, axis=1)

# Contar ocorrências
contagem = df['categoria'].value_counts()

# Reordenar logicamente
ordem = ['Win de Primeira (G0)', 'Win no Gale 1 (G1)', 'Win no Gale 2 (G2)', 'Loss (Falha no G2)']
contagem = contagem.reindex(ordem).fillna(0)

# Criar o gráfico
plt.figure(figsize=(10, 6))
cores = ['#2ca02c', '#98df8a', '#ffbb78', '#d62728'] # Verde forte, verde claro, laranja, vermelho
ax = contagem.plot(kind='bar', color=cores, edgecolor='black')

plt.title('Distribuição de Vitórias por Nível de Gale (JP225-OTC)', fontsize=16, fontweight='bold', pad=20)
plt.xlabel('Resultado do Trade', fontsize=12)
plt.ylabel('Quantidade de Operações', fontsize=12)
plt.xticks(rotation=0, fontsize=11)
plt.grid(axis='y', linestyle='--', alpha=0.7)

# Adicionar os números em cima de cada barra
for i, v in enumerate(contagem):
    ax.text(i, v + 1, str(int(v)), ha='center', va='bottom', fontsize=12, fontweight='bold')

# Adicionar porcentagens
total = len(df)
for i, v in enumerate(contagem):
    pct = (v / total) * 100
    ax.text(i, v / 2, f"{pct:.1f}%", ha='center', va='center', fontsize=11, fontweight='bold', color='black' if i != 3 else 'white')

# Salvar o gráfico na pasta de artefatos
output_dir = r"C:\Users\lucas\.gemini\antigravity-ide\brain\dcbd2451-56be-43cd-afb6-6a2c609cf26f"
output_path = os.path.join(output_dir, "gale_distribution.png")

plt.tight_layout()
plt.savefig(output_path, dpi=150)
print(f"Gráfico salvo em {output_path}")
