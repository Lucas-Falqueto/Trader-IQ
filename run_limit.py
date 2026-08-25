import subprocess
import os
import time
import sys

# Lista dos ativos validados no backtest
ATIVOS_PARA_RODAR = [
    "EURUSD-OTC", 
    "SP35-OTC", 
    "JP225-OTC",
    "AUDJPY-OTC",
    "DOLLARINDEX"
]

def iniciar_robos():
    processos = []
    print("🚀 Iniciando portfólio da ESTRATÉGIA PRICE LIMIT...")

    for ativo in ATIVOS_PARA_RODAR:
        env_vars = os.environ.copy()
        env_vars["ATIVO"] = ativo
        
        # Inicia uma instância separada do main_limit.py para cada ativo
        p = subprocess.Popen([sys.executable, "main_limit.py"], env=env_vars)
        processos.append({"ativo": ativo, "processo": p})
        
        print(f"✅ Robô Limit ligado para {ativo} (PID: {p.pid})")
        time.sleep(2)

    print("\n🎯 Todos os robôs Price Limit estão operando simultaneamente!")
    print("Pressione CTRL + C a qualquer momento para desligar todos de uma vez.\n")

    try:
        for p in processos:
            p["processo"].wait()
    except KeyboardInterrupt:
        print("\n🛑 Sinal de parada recebido! Desligando todos os robôs...")
        for p in processos:
            p["processo"].terminate()
            print(f"Robô {p['ativo']} encerrado.")
        print("Operações finalizadas.")

if __name__ == "__main__":
    iniciar_robos()
