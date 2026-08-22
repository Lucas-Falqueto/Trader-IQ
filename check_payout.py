from data import conectar
from config import IQ_EMAIL, IQ_PASSWORD

api = conectar(IQ_EMAIL, IQ_PASSWORD)
payout = api.get_all_profit()
print(payout.get("SP35-OTC"))
print(payout.get("JP225-OTC"))
print(payout.get("EURUSD-OTC"))
