import subprocess
import time
import os
import sys
import requests
from datetime import datetime
from dotenv import load_dotenv

# Cargar las credenciales ocultas
load_dotenv()

# =========================================================
# CONFIGURACIÓN TÁCTICA
# =========================================================
TG_TOKEN = os.getenv("TELEGRAM_TOKEN")
TG_CHAT  = os.getenv("TELEGRAM_CHAT_ID")
HORA_RESETEO = "17:05"  # 5:05 PM (Hora del servidor Azure)

ultimo_envio_tg = 0 

def enviar_telegram(mensaje):
    global ultimo_envio_tg
    ahora = time.time()
    
    if ahora - ultimo_envio_tg < 30:
        return 
        
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT, "text": f"🛡️ [CENTRO DE MANDO]:\n{mensaje}"}
    try: 
        requests.post(url, json=payload, timeout=5)
        ultimo_envio_tg = ahora 
    except: 
        pass

# =========================================================
# MAPA TÁCTICO DE ESCUADRONES (10 Unidades)
# =========================================================
escuadron = [
    {"nombre": "Exness 1",           "carpeta": r"C:\Users\vr4ux23\Documents\Bot_Trading_exness",      "script": "centinela_exness_1.py"},
    {"nombre": "Audacity",           "carpeta": r"C:\Users\vr4ux23\Documents\Bot_Trading_Audacity",    "script": "centinela_audacity.py"},
    {"nombre": "Alpha Capital",      "carpeta": r"C:\Users\vr4ux23\Documents\Bot_Trading_Alpha",       "script": "centinela_alpha_capital.py"},
    {"nombre": "FTMO Principal",      "carpeta": r"C:\Users\vr4ux23\Documents\Bot_Trading_ftmo",        "script": "centinela_ftmo_1.py"},
    {"nombre": "Telegram Info",      "carpeta": r"C:\Users\vr4ux23\Documents\Bot_Trading_ftmo",        "script": "centinela_remoto_info.py"},
    {"nombre": "Telegram Resultados","carpeta": r"C:\Users\vr4ux23\Documents\Bot_Trading_ftmo",        "script": "centinela_remoto_resultados.py"},
    {"nombre": "Visualizador Gráfico","carpeta": r"C:\Users\vr4ux23\Documents\Bot_Trading_ftmo",       "script": "centinela_visual.py"},
    {"nombre": "Reportero Diario",   "carpeta": r"C:\Users\vr4ux23\Documents\Bot_Trading_ftmo",        "script": "reportero_diario.py"},
    {"nombre": "FundedNext",         "carpeta": r"C:\Users\vr4ux23\Documents\Bot_Trading_Fundednext",  "script": "centinela_funded_next.py"},
    # Unidad de Soporte integrada (Corregida al Escritorio según tu última actualización)
    {"nombre": "Perro Guardián",     "carpeta": r"C:\Users\vr4ux23\Desktop",                           "script": "perro_guardian.py"}
]

procesos = {}

def desplegar_centinela(bot_info):
    ts = datetime.now().strftime('%H:%M:%S')
    print(f"🚀 [{ts}] Desplegando [{bot_info['nombre']}]...")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    # Usamos sys.executable para garantizar que use el mismo Python que el Supervisor
    return subprocess.Popen([sys.executable, bot_info['script']], cwd=bot_info['carpeta'], env=env)

def matar_todo():
    print("🧹 [MANTENIMIENTO] Limpiando escuadrones para reseteo diario...")
    for nombre, proc in procesos.items():
        try: proc.terminate()
        except: pass
    time.sleep(5)

def main():
    print("==================================================")
    print("🛡️  CENTRO DE MANDO: SUPERVISOR v2.3 (BLINDADO)  🛡️")
    print("==================================================")

    # 1. ARRANQUE INICIAL
    for bot in escuadron:
        procesos[bot["nombre"]] = desplegar_centinela(bot)
        time.sleep(8) # Pausa para que MT5 procese las conexiones

    enviar_telegram("🛡️ Centro de Mando v2.3 ONLINE. Escuadrones en posición.")

    # 2. BUCLE DE VIGILANCIA Y RESETEO
    while True:
        ahora = datetime.now().strftime("%H:%M")
        
        # Lógica de Reseteo Diario Interno
        if ahora == HORA_RESETEO:
            enviar_telegram("🔄 Iniciando Reseteo Diario Programado...")
            matar_todo()
            for bot in escuadron:
                procesos[bot["nombre"]] = desplegar_centinela(bot)
                time.sleep(8)
            time.sleep(60) 

        for bot in escuadron:
            nombre = bot["nombre"]
            proceso = procesos.get(nombre)
            
            if proceso is None or proceso.poll() is not None:
                ts = datetime.now().strftime('%H:%M:%S')
                msg = f"⚠️ [{ts}] ALERTA: [{nombre}] caído. Reiniciando..."
                print(msg)
                enviar_telegram(msg)
                procesos[nombre] = desplegar_centinela(bot)
                time.sleep(3)
                    
        time.sleep(10)

if __name__ == "__main__":
    main()
