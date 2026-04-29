import psutil
import subprocess
import time
import os

# ==============================================================================
# RUTAS TÁCTICAS
# ==============================================================================
BROKER_PATH = r"C:\Users\vr4ux23\Documents\Bot_Trading_ftmo\MT5_FTMO_1\terminal64.exe"
SCRIPT_ARRANQUE = "supervisor_maestro.py" 

print("==================================================")
print("🔧 INICIANDO PROTOCOLO DE MANTENIMIENTO DIARIO 🔧")
print("==================================================")

# 1. Asesinar todos los procesos de Python (Bots y Supervisores), excepto este script
print("🧹 Limpiando procesos de bots en memoria...")
mi_pid = os.getpid()
for proc in psutil.process_iter(['name', 'pid']):
    if proc.info['name'] == 'python.exe' and proc.info['pid'] != mi_pid:
        try:
            proc.kill()
        except:
            pass

# 2. Asesinar MetaTrader 5 
print("💀 Apagando terminales MT5...")
for proc in psutil.process_iter(['name']):
    if proc.info['name'] == 'terminal64.exe':
        try:
            proc.kill()
        except:
            pass

print("⏳ Esperando 5 segundos para liberación de RAM...")
time.sleep(5)

# 3. Arrancar MT5 limpio (Esto aplicará cualquier actualización pendiente automáticamente)
print("🚀 Iniciando MetaTrader 5 (Aplicando parches si existen)...")
subprocess.Popen([BROKER_PATH])

# Damos 45 segundos para que cargue gráficos, aplique parches y conecte al servidor FTMO
print("⏳ Esperando 45 segundos para estabilización del núcleo...")
time.sleep(45)

# 4. Levantar la base
print(f"🤖 Desplegando Centro de Mando ({SCRIPT_ARRANQUE})...")
# Abre el supervisor en una consola nueva
subprocess.Popen(["python", SCRIPT_ARRANQUE], creationflags=subprocess.CREATE_NEW_CONSOLE)

print("✅ Mantenimiento finalizado. Ecosistema reiniciado y operativo.")
print("==================================================")
