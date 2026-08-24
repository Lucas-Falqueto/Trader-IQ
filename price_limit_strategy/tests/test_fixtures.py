import unittest
import sys
import os

# Adiciona a raiz do projeto no path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from price_limit_strategy.models import Candle, Lote
from price_limit_strategy.candle_utils import eh_vela_relevante, tem_pavio_rejeicao_abertura
from price_limit_strategy.lote_detection import detectar_lotes
from price_limit_strategy.first_register import primeiro_registro_reversao
from price_limit_strategy.signal_engine import run

class TestCenariosPDF(unittest.TestCase):
    def test_cenario_3_1_tipo1_retracao(self):
        # 3.1 — Limite Tipo 1 clássico (pág. 5)
        # Downtrend -> lote na base -> rompimento verde -> continuacao verde -> toque no canal
        candles = [
            Candle(open=105, high=105, low=102, close=102, timestamp=0), # Bearish (Downtrend)
            Candle(open=100, high=102, low=99,  close=102, timestamp=1), # Lote Base Verde (mudou cor) com pavio inferior (low=99)
            Candle(open=102, high=106, low=102, close=105, timestamp=2), # Rompimento (verde) -> topo lote = 102
            Candle(open=105, high=108, low=104, close=107, timestamp=3), # Continuação (verde)
            Candle(open=107, high=110, low=107, close=109, timestamp=4), # Vai embora
            Candle(open=109, high=110, low=105, close=106, timestamp=5), # Volta e TOCA no canal [108, 106] -> Tocou no 105
        ]
        signals = run(candles)
        self.assertTrue(any(s.tipo == 'retracao' for s in signals), "Deveria ter disparado Retração")
        
    def test_cenario_tipo2_var1_gap_minimo(self):
        # Var 1: Overlap muito pequeno. Linha Rosa é a borda do corpo!
        candles = [
            Candle(open=120, high=120, low=115, close=115, timestamp=0), # Perna Forte
            Candle(open=115, high=115, low=110, close=110, timestamp=1), # Perna Forte
            Candle(open=110, high=110, low=105, close=105, timestamp=2), # Downtrend
            Candle(open=105, high=105, low=100, close=100, timestamp=3), # Downtrend
            Candle(open=100, high=104, low=98,  close=102, timestamp=4), # Vela 1 (Verde) -> Corpo [100, 102]
            Candle(open=102.1, high=106, low=101,  close=101.8,  timestamp=5), # Vela 2 (Vermelha) -> Corpo [101.8, 102.1]
            # Overlap [101.8, 102] (0.2 pontos). c1_body=2. pct = 0.2/2 = 10% (É V1!)
            # Overlap de Resistência(PUT) -> Borda Superior = 102. Linha rosa = 102!
            Candle(open=99,  high=101, low=95,  close=96,  timestamp=6), # Vai embora (high=101, não toca)
            Candle(open=96,  high=102, low=96,  close=100, timestamp=7), # Volta e toca no 102! (Gatilho)
        ]
        signals = run(candles)
        self.assertTrue(any(s.tipo == 'tipo2' and s.candle_idx == 7 for s in signals), "Deveria detectar Var 1 (Gap Mínimo) ativando na borda")

    def test_cenario_tipo2_var2_taxa_dividida(self):
        # Var 2: Zero Overlap. Requer tocar na Azul primeiro, depois na Rosa.
        candles = [
            Candle(open=120, high=120, low=115, close=115, timestamp=0), # Perna Forte
            Candle(open=115, high=115, low=110, close=110, timestamp=1), # Perna Forte
            Candle(open=110, high=110, low=105, close=105, timestamp=2),
            Candle(open=105, high=105, low=100, close=100, timestamp=3),
            Candle(open=100, high=104, low=98,  close=102, timestamp=4), # Vela 1 (Verde) -> Corpo [100, 102]
            Candle(open=102, high=106, low=99,  close=99,  timestamp=5), # Vela 2 (Vermelha) -> Corpo [99, 102] (Taxa Dividida em 102)
            # Azul = 102. Rosa = pavio 106. (Resistência PUT)
            Candle(open=99,  high=102, low=95,  close=96,  timestamp=6), # Trava na linha azul (high=102)
            Candle(open=96,  high=106, low=96,  close=100, timestamp=7), # Vai no pavio 106! (Gatilho)
        ]
        signals = run(candles)
        self.assertTrue(any(s.tipo == 'tipo2' and s.candle_idx == 7 for s in signals), "Deveria detectar Var 2 (Taxa Dividida) após travamento")

    def test_cenario_tipo2_var3_profundo(self):
        # Var 3: Overlap grande. Entrada direta no pavio.
        candles = [
            Candle(open=120, high=120, low=115, close=115, timestamp=0),
            Candle(open=115, high=115, low=110, close=110, timestamp=1),
            Candle(open=110, high=110, low=105, close=105, timestamp=2),
            Candle(open=105, high=105, low=100, close=100, timestamp=3),
            Candle(open=100, high=104, low=98,  close=102, timestamp=4), # Vela 1 (Verde) -> Corpo [100, 102]
            Candle(open=100.5, high=106, low=95,  close=95, timestamp=5), # Vela 2 (Vermelha) -> Corpo [95, 100.5]. Overlap Profundo [100, 100.5]
            # Linha Rosa = pavio 106 (PUT).
            Candle(open=95,  high=99, low=90,  close=92,  timestamp=6), # Longe
            Candle(open=92,  high=106, low=92,  close=100, timestamp=7), # Bate no 106 direto (Gatilho)
        ]
        signals = run(candles)
        self.assertTrue(any(s.tipo == 'tipo2' and s.candle_idx == 7 for s in signals), "Deveria detectar Var 3 (Overlap Profundo)")

if __name__ == '__main__':
    unittest.main()
