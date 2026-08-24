from typing import List
from .models import Candle, Signal
from .lote_detection import detectar_lotes
from .limit_type1 import processar_limite_tipo1
from .limit_type2 import processar_limite_tipo2
from .first_register import primeiro_registro_reversao, primeiro_registro_novo_preco

def run(candles: List[Candle]) -> List[Signal]:
    """
    Motor central da estratégia isolada.
    Recebe o histórico de velas e retorna os sinais finais de alta/baixa confiança.
    """
    sinais_finais = []
    
    if len(candles) < 2:
        return sinais_finais
        
    # 1. Detectar Lotes
    lotes = detectar_lotes(candles)
    
    # 2. Processar canais de Limite de Preço (Tipo 1 e Tipo 2)
    sinais_t1 = processar_limite_tipo1(candles, lotes)
    sinais_t2 = processar_limite_tipo2(candles)
    
    todos_limites = sinais_t1 + sinais_t2
    
    # 3. Mapear os índices que são Primeiro Registro
    reg_reversao = primeiro_registro_reversao(candles)
    reg_novo = primeiro_registro_novo_preco(candles)
    
    set_registros = set(reg_reversao + reg_novo)
    
    # 4. Combinação (Sinal Sniper)
    for limite in todos_limites:
        # A "mágica": A vela que ativou o limite também é um primeiro registro?
        alta_confianca = (limite.indice_vela in set_registros)
        
        # Pode haver outras lógicas de confiança aqui
        sinais_finais.append(Signal(
            alta_confianca=alta_confianca,
            direcao=limite.direcao,
            candle_idx=limite.indice_vela,
            descricao=f"{limite.tipo.upper()} (Canal {limite.channel.top:.5f}-{limite.channel.bottom:.5f})",
            tipo=limite.tipo
        ))
        
    # Ordenar por índice cronológico
    sinais_finais.sort(key=lambda s: s.candle_idx)
    return sinais_finais
