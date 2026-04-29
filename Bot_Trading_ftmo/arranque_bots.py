import subprocess
import time

print("==================================================")
print("🚀 LANZADOR MAESTRO DE BOTS INICIADO 🚀")
print("==================================================")

# Lista de los scripts que conforman tu batallón
# Asegúrate de poner los nombres EXACTOS de tus archivos .py
escuadron = [
    "supervisor_maestro.py",  # Tu bot de Telegram (La Torre de Control)
    "centinela_orb_v5.py"     # El bot agresivo del Nasdaq (La Espada)
    # "tu_bot_anterior.py"    # Tu bot seguro (El Escudo) -> Agrégalo aquí si aplica
]

print(f"Desplegando un total de {len(escuadron)} unidades tácticas...\n")

for bot in escuadron:
    print(f"Abriendo terminal independiente para: {bot}")
    
    # La instrucción CREATE_NEW_CONSOLE es la magia que crea una ventana negra nueva para cada uno
    subprocess.Popen(["python", bot], creationflags=subprocess.CREATE_NEW_CONSOLE)
    
    # Pausa táctica de 3 segundos entre cada bot para no saturar el procesador del servidor
    time.sleep(3)

print("\n✅ Todo el escuadrón ha sido desplegado exitosamente.")
print("Este lanzador maestro cerrará sus comunicaciones en 5 segundos...")
time.sleep(5)