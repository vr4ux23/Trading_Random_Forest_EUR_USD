# -*- coding: utf-8 -*-
import MetaTrader5 as mt5
import pandas as pd
import matplotlib.pyplot as plt
import joblib
import requests
import os
import time
from datetime import datetime
from dotenv import load_dotenv

# Cargar las credenciales ocultas
load_dotenv()

# ==========================================
# 1. CONFIGURACION
# ==========================================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BROKER_PATH = r"C:\Users\vr4ux23\Documents\Bot_Trading_ftmo\MT5_FTMO_1\terminal64.exe"
# Nota: Mantengo tu ruta original del modelo que apuntaba a Fundednext
MODELO_PATH = r"C:\Users\vr4ux23\Documents\Bot_Trading_Fundednext\modelo_rf_eurusd.pkl"

BROKER_SERVIDOR = "FTMO-Demo"
LOGIN_CUENTA = int(os.getenv("FTMO_LOGIN"))
PASSWORD_CUENTA = os.getenv("FTMO_PASSWORD")
SYMBOL = "EURUSD"

# ==========================================
# 2. LOGICA DE CONEXION Y DATOS
# ==========================================
def obtener_analisis_visual():
    if not mt5.initialize(path=BROKER_PATH): return None
    mt5.login(login=LOGIN_CUENTA, password=PASSWORD_CUENTA, server=BROKER_SERVIDOR)
    
    # Pedimos 50 velas para el grafico
    rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H1, 0, 50)
    mt5.shutdown()
    
    if rates is None: return None
    
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    # Calculos para el modelo
    sma20 = df['close'].rolling(window=20).mean()
    vol_avg = df['tick_volume'].rolling(window=20).mean()
    
    precio_act = df['close'].iloc[-1]
    dist_sma = (precio_act - sma20.iloc[-1]) / sma20.iloc[-1]
    v_ratio = df['tick_volume'].iloc[-1] / vol_avg.iloc[-1]
    
    # Cargar IA y predecir
    modelo = joblib.load(MODELO_PATH)
    prob = modelo.predict_proba([[dist_sma, v_ratio]])[0]
    confianza = round(max(prob) * 100, 1)
    pred = "LONG" if modelo.predict([[dist_sma, v_ratio]])[0] == 1 else "SHORT"
    
    # --- CREAR EL GRAFICO ---
    plt.style.use('dark_background') # Estilo pro
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Dibujar precio y SMA
    ax.plot(df['time'], df['close'], label='Precio EURUSD', color='#00ffcc', linewidth=2)
    ax.plot(df['time'], sma20, label='SMA 20', color='#ffcc00', linestyle='--')
    
    # Personalizacion
    plt.title(f"Analisis Quant: {SYMBOL} H1", fontsize=16, color='white', pad=20)
    ax.set_ylabel("Precio")
    ax.grid(alpha=0.2)
    
    # Cuadro de Informacion de la IA
    color_box = 'green' if confianza >= 60 else 'gray'
    info_text = (f"PRECIO: {precio_act}\n"
                 f"DIST SMA20: {round(dist_sma, 5)}\n"
                 f"VOL RATIO: {round(v_ratio, 2)}\n"
                 f"CONFIANZA IA: {confianza}% ({pred})")
    
    plt.annotate(info_text, xy=(0.02, 0.75), xycoords='axes fraction',
                 bbox=dict(boxstyle="round", fc=color_box, alpha=0.3),
                 fontsize=11, color='white')

    # Guardar imagen temporal
    nombre_img = "reporte_mercado.png"
    plt.savefig(nombre_img, dpi=150)
    plt.close()
    return nombre_img

def enviar_foto_telegram(ruta_img, caption):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    with open(ruta_img, 'rb') as f:
        requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}, files={'photo': f})
    os.remove(ruta_img) # Borrar despues de enviar

# ==========================================
# 3. MOTOR AUTOMATICO (WATCHDOG)
# ==========================================
def iniciar_visualizador_automatico():
    print("Iniciando Centinela Visual Automático...")
    
    ultimo_reporte_enviado = None
    
    while True:
        ahora = datetime.now()
        hora = ahora.hour
        minuto = ahora.minute
        
        # Dispara en los mismos horarios que el reportero de texto (2, 8, 13 y 21 hrs)
        if hora in [2, 8, 13, 21] and minuto < 5 and ultimo_reporte_enviado != hora:
            print(f"[{ahora.strftime('%H:%M:%S')}] Generando reporte visual...")
            
            imagen = obtener_analisis_visual()
            if imagen:
                texto_caption = f"📸 Snapshot Visual del Mercado - Sesion de las {hora}:00"
                enviar_foto_telegram(imagen, texto_caption)
                print("Reporte visual enviado con exito!")
                ultimo_reporte_enviado = hora
            else:
                print("Error al generar el reporte visual.")
                
        # Duerme 1 minuto y vuelve a checar la hora
        time.sleep(60)

if __name__ == "__main__":
    iniciar_visualizador_automatico()
