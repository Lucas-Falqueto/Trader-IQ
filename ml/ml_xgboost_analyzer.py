import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.metrics import classification_report

def analisar():
    print("=== ESTUDO QUANTITATIVO: XGBoost Loss Mining ===")
    
    try:
        df = pd.read_csv('dataset_xgboost_filtered.csv')
    except Exception as e:
        print(f"Erro ao carregar dataset: {e}")
        return

    # Analisar o dataset completo da Estratégia Price Limit
    
    # O alvo é 1 para Win, 0 para Loss
    # Mas para focar nos losses, podemos tratar Loss como a classe positiva (1) e Win como (0)
    # Assim o modelo tenta "achar" o Loss.
    df['alvo_loss'] = 1 - df['alvo_win']
    
    # Remover colunas que não são features matemáticas puras
    cols_to_drop = [c for c in ['alvo_win', 'alvo_loss', 'ativo'] if c in df.columns]
    X = df.drop(columns=cols_to_drop)
    y = df['alvo_loss']
    
    print(f"Total de Operações Analisadas: {len(df)}")
    print(f"Fatais (Losses): {y.sum()} | Sucessos (Wins): {len(df) - y.sum()}")
    print("-" * 50)
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # Treinar XGBoost para extrair Importância
    # max_depth pequeno para evitar overfitting, scale_pos_weight para balancear a classe minoritária (Loss)
    scale_pos_weight = (len(y_train) - sum(y_train)) / sum(y_train) if sum(y_train) > 0 else 1
    
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.05,
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        eval_metric='auc'
    )
    
    model.fit(X_train, y_train)
    
    print("\n[XGBoost] Top 5 Variáveis Mais Causadoras de Loss (Feature Importance):")
    importances = pd.Series(model.feature_importances_, index=X.columns).sort_values(ascending=False)
    for feat, imp in importances.head(5).items():
        print(f" -> {feat:<25}: {imp:.2%}")
        
    print("-" * 50)
    
    # Para extrair regras legíveis por humanos, vamos treinar uma Árvore de Decisão simples no XGBoost proxy
    # (Surrogate model)
    dt = DecisionTreeClassifier(max_depth=3, class_weight='balanced', random_state=42)
    dt.fit(X, y)
    
    print("\n[Regras de Ouro] Árvore de Decisão Simplificada para Evitar Losses:")
    print(" (Class '1' significa ALTO RISCO DE LOSS. Class '0' significa WIN PROVÁVEL)")
    
    tree_rules = export_text(dt, feature_names=list(X.columns))
    print(tree_rules)

if __name__ == "__main__":
    analisar()
