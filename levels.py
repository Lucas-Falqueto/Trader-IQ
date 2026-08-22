import pandas as pd
from config import VELAS_SR


def marcar_niveis(df_m15: pd.DataFrame) -> dict:
    """
    Marca suporte e resistência usando o topo/fundo do pavio
    das 3 penúltimas velas fechadas do M15.

    Args:
        df_m15: DataFrame com colunas high e low, ordenado por tempo.
                Deve conter pelo menos 4 velas (3 penúltimas + a atual).

    Returns:
        {"resistencia": float, "suporte": float}
    """
    # Exclui a vela atual (última) e pega as N penúltimas fechadas
    fechadas = df_m15.iloc[-(VELAS_SR + 1):-1]
    resistencia = fechadas["high"].max()
    suporte = fechadas["low"].min()
    return {"resistencia": resistencia, "suporte": suporte}
