import time
import logging
from core.data import conectar
from core.config import IQ_EMAIL, IQ_PASSWORD

logging.basicConfig(level=logging.INFO)

api = conectar(IQ_EMAIL, IQ_PASSWORD)
print("Conectado.")

# Tenta pegar ultimas ordens
check,id = api.buy(1, "SP35-OTC", "put", 1)
print(f"Ordem enviada. Aguardando resultado... ID{id}")
historico = api.check_win_v3(id)
print("Resultado recebido:", historico)
if check:
    resultado, lucro = historico
    print(f"Resultado processado do ID {id}: Status={resultado}, Lucro=${lucro}")
else:
    print(f"Falha ao enviar ordem: {id}")
