import pandas as pd
import xgboost as xgb
from sklearn.tree import DecisionTreeClassifier, export_text

def analisar_legacy():
    try:
        df = pd.read_csv('resultados/ml_dataset_legacy.csv')
    except Exception as e:
        print(f"Erro ao carregar dataset: {e}")
        return

    # O alvo é 1 para Win, 0 para Loss
    # Mas para focar nos losses, tratamos Loss como a classe positiva (1) e Win como (0)
    df['is_loss'] = df['alvo_win'].apply(lambda x: 1 if x == 0 else 0)
    
    X = df.drop(['alvo_win', 'is_loss', 'ativo'], axis=1)
    y = df['is_loss']
    
    total = len(df)
    losses = df['is_loss'].sum()
    wins = total - losses
    
    print("\n=== ESTUDO QUANTITATIVO: XGBoost Loss Mining (Engine Original) ===")
    print(f"Total de Operações Analisadas: {total}")
    print(f"Fatais (Losses): {losses} | Sucessos (Wins): {wins}")
    print("-" * 50)
    
    if losses == 0:
        print("Nenhum loss encontrado! Impossível treinar modelo de falha.")
        return
        
    scale_pos_weight = wins / losses if losses > 0 else 1
    
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.05,
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        eval_metric='auc'
    )
    
    model.fit(X, y)
    
    print("\n[XGBoost] Top Variáveis Mais Causadoras de Loss no Engine Antigo:")
    importances = pd.Series(model.feature_importances_, index=X.columns).sort_values(ascending=False)
    for feat, imp in importances.head(5).items():
        print(f" -> {feat:<25}: {imp:.2%}")
        
    print("-" * 50)
    
    dt = DecisionTreeClassifier(max_depth=3, class_weight='balanced', random_state=42)
    dt.fit(X, y)
    
    print("\n[Regras de Ouro] Árvore de Decisão do Setup Clássico:")
    print(" (Class '1' significa ALTO RISCO DE LOSS. Class '0' significa WIN PROVÁVEL)")
    
    tree_rules = export_text(dt, feature_names=list(X.columns))
    print(tree_rules)

if __name__ == "__main__":
    analisar_legacy()
