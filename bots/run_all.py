import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import subprocess
import os
import time
import sys

# Lista dos ativos validados no backtest
ATIVOS_PARA_RODAR = [
    "EURUSD-OTC", 
    "SP35-OTC", 
    "JP225-OTC",
    "JP225",
    "UK100",
    "US100",
    "US500",
]

def iniciar_robos():
    processos = []
    print("🚀 Iniciando portfólio de robôs...")

    for ativo in ATIVOS_PARA_RODAR:
        env_vars = os.environ.copy()
        env_vars["ATIVO"] = ativo
        
        # Inicia uma instância separada do main.py para cada ativo
        # O prefixo sys.executable garante que ele usa o mesmo ambiente virtual (venv)
        p = subprocess.Popen([sys.executable, os.path.join(os.path.dirname(__file__), "main.py")], env=env_vars)
        processos.append({"ativo": ativo, "processo": p})
        
        print(f"✅ Robô ligado para {ativo} (PID: {p.pid})")
        time.sleep(2)  # Pausa breve para não sobrecarregar o login da corretora

    print("\n🎯 Todos os robôs estão operando simultaneamente!")
    print("Pressione CTRL + C a qualquer momento para desligar todos de uma vez.\n")

    try:
        # Fica aguardando os processos (loop infinito enquanto eles rodam)
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
