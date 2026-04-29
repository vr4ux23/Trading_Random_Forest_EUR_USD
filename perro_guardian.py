import MetaTrader5 as mt5
import time
import psutil
import subprocess
import os
from dotenv import load_dotenv

load_dotenv()

BROKER_PATH = r"C:\Users\vr4ux23\Documents\Bot_Trading_ftmo\MT5_FTMO_1\terminal64.exe"
SCRIPT_ARRANQUE = "supervisor_maestro.py"

def matar_proceso_congelado():
    """Busca y asesina cualquier instancia de MT5 bloqueada"""
    eliminado = False
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] == 'terminal64.exe':
            print("💀 Objetivo localizado. Eliminando terminal64.exe bloqueado...")
            proc.kill()
            eliminado = True
    
    if eliminado:
        time.sleep(5) # Dar tiempo al sistema operativo para limpiar la memoria

def protocolo_vigilancia():
    print("==================================================")
    print("🛡️ PERRO GUARDIÁN ACTIVO Y VIGILANDO 🛡️")
    print("==================================================")
    
    # Bucle infinito de vigilancia (Revisa cada 60 segundos)
    while True:
        # Intentamos obtener el estado de la terminal
        # Si hay un LiveUpdate, esto devolverá None o lanzará un error
        info_terminal = mt5.terminal_info()
        
        if info_terminal is None:
            print("\n❌ ALERTA CRÍTICA: Pérdida de pulso con MT5 (Posible LiveUpdate o Crash).")
            print("🔄 Iniciando Protocolo de Resurrección...")
            
            # 1. Ejecutar Orden 66 (Limpiar el terreno)
            matar_proceso_congelado()
            
            # 2. Relanzar MT5 (Forzando la actualización automática en el arranque)
            print("🚀 Relanzando MT5...")
            subprocess.Popen([BROKER_PATH])
            
            # Damos 40 segundos de gracia para que MT5 aplique el parche, abra y conecte a FTMO
            print("⏳ Esperando 40 segundos para estabilización del núcleo...")
            time.sleep(40)
            
            # 3. Reconectamos el Guardián al nuevo MT5
            if mt5.initialize(path=BROKER_PATH):
                print("✅ Enlace con el nuevo MT5 restaurado.")
                
                # 4. Levantar la base (Tu script de arranque)
                print(f"🤖 Desplegando {SCRIPT_ARRANQUE} para reactivar bots y Telegram...")
                # Usamos subprocess para abrir una nueva ventana/proceso con tus bots
                subprocess.Popen(["python", SCRIPT_ARRANQUE], creationflags=subprocess.CREATE_NEW_CONSOLE)
                
                print("🟢 Ecosistema restaurado. Volviendo a vigilancia silenciosa...\n")
            else:
                print("❌ Fallo crítico. MT5 no pudo revivir. Requiere intervención humana.")
                
        # Descanso táctico antes del siguiente chequeo
        time.sleep(60)

if __name__ == "__main__":
    # Primer enlace de arranque
    if mt5.initialize(path=BROKER_PATH):
        protocolo_vigilancia()
    else:
        print("❌ El Perro Guardián no pudo conectar inicialmente a MT5. Revisa la ruta.")
