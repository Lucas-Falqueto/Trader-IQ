from dataclasses import dataclass
from typing import Optional

@dataclass
class Candle:
    open: float
    high: float
    low: float
    close: float
    timestamp: int
    rsi: float = 50.0
    sma: float = 0.0
    sma20: float = 0.0

    @property
    def is_bullish(self) -> bool:
        return self.close >= self.open
        
    @property
    def is_bearish(self) -> bool:
        return self.close < self.open

    @property
    def body_top(self) -> float:
        return max(self.open, self.close)

    @property
    def body_bottom(self) -> float:
        return min(self.open, self.close)

    @property
    def upper_wick(self) -> float:
        return self.high - self.body_top

    @property
    def lower_wick(self) -> float:
        return self.body_bottom - self.low
        
    @property
    def total_size(self) -> float:
        return self.high - self.low

@dataclass
class Lote:
    start_idx: int
    end_idx: int
    top: float
    bottom: float
    direction: str  # "CALL" (Alta) ou "PUT" (Baixa)
    opening_wick: float # Pavio de abertura (rejeição no início do movimento)

@dataclass
class ReferenceChannel:
    top: float
    bottom: float
    start_idx: int
    
@dataclass
class PriceLimitSignal:
    channel: ReferenceChannel
    ativo_em: int
    tipo: str  # "retracao" ou "reversao" ou "tipo2"
    indice_vela: int
    direcao: str # "CALL" ou "PUT"

@dataclass
class Signal:
    alta_confianca: bool
    direcao: str
    candle_idx: int
    descricao: str
    tipo: str = "retracao"
