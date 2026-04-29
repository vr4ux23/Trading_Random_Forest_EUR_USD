# -*- coding: utf-8 -*-
import matplotlib
matplotlib.use('Agg') 
import MetaTrader5 as mt5
import pandas as pd
import matplotlib.pyplot as plt
import joblib
import requests
import os
import time
import warnings
from datetime import datetime
from dotenv import load_dotenv

warnings.filterwarnings('ignore')

# Cargar las credenciales ocultas
load_dotenv()

# ==========================================
# CONFIGURACION
# ==========================================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BROKER_PATH = r"C:\Users\vr4ux23\Documents\Bot_Trading_ftmo\MT5_FTMO_1\terminal64.exe"
MODELO_PATH = r"C:\Users\vr4ux23\Documents\Bot_Trading_ftmo\MT5_FTMO_1\modelo_rf_eurusd.pkl"

BROKER_SERVIDOR = "FTMO-Demo"
LOGIN_CUENTA = int(os.getenv("FTMO_LOGIN"))
PASSWORD_CUENTA = os.getenv("FTMO_PASSWORD")
SYMBOL = "EURUSD"

def generar_diagnostico_y_foto(modelo):
    rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H1, 0, 50)
    if rates is None or len(rates) == 0: return None, None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    sma20 = df['close'].rolling(window=20).mean()
    vol_avg = df['tick_volume'].rolling(window=20).mean()
    precio_act = df['close'].iloc[-1]
    dist_sma = (precio_act - sma20.iloc[-1]) / sma20.iloc[-1]
    v_ratio = df['tick_volume'].iloc[-1] / vol_avg.iloc[-1]
    prob = modelo.predict_proba([[dist_sma, v_ratio]])[0]
    confianza = round(max(prob) * 100, 1)
    direccion = "COMPRA (LONG)" if modelo.predict([[dist_sma, v_ratio]])[0] == 1 else "VENTA (SHORT)"
    
    txt_dist = "tranquilo cerca de su promedio" if abs(dist_sma) < 0.0015 else "muy estirado respecto a su media"
    txt_vol = "hay poco interes de los bancos" if v_ratio < 1.0 else "hay fuerte movimiento institucional"
    
    # --- TEXTO ORIGINAL RESTAURADO ---
    diagnostico = (
        f"🔍 <b>DIAGNOSTICO FLASH</b>\n\n"
        f"El precio actual es de <b>{precio_act}</b>. "
        f"Lo veo {txt_dist} y noto que {txt_vol}.\n\n"
        f"🤖 <b>Veredicto IA:</b>\n"
        f"Mi confianza es del <b>{confianza}%</b> para una operacion de {direccion}. "
    )
    
    if confianza < 60:
        diagnostico += "Aun no es suficiente para disparar, prefiero seguir vigilando. 😴"
    else:
        diagnostico += "¡Ojo! El modelo ve una oportunidad clara aqui. ⚡"

    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(df['time'], df['close'], label='Precio', color='#00ffcc', linewidth=2)
    ax.plot(df['time'], sma20, label='SMA 20', color='#ffcc00', linestyle='--')
    color_box = 'green' if confianza >= 60 else 'gray'
    plt.annotate(f"IA: {confianza}%", xy=(0.02, 0.9), xycoords='axes fraction',
                 bbox=dict(boxstyle="round", fc=color_box, alpha=0.5), color='white')
    nombre_img = "reporte_info.png"
    plt.savefig(nombre_img, dpi=100); plt.close()
    return nombre_img, diagnostico

def iniciar_escucha_info():
    print("--- MONITOR REMOTO: COMANDO /info ACTIVO ---")
    if not mt5.initialize(path=BROKER_PATH): return
    mt5.login(login=LOGIN_CUENTA, password=PASSWORD_CUENTA, server=BROKER_SERVIDOR)
    modelo = joblib.load(MODELO_PATH)
    ultimo_id = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={ultimo_id + 1}&timeout=10"
            updates = requests.get(url).json().get("result", [])
            for update in updates:
                ultimo_id = update["update_id"]
                if "message" in update and "text" in update["message"]:
                    if update["message"]["text"] == "/info":
                        img, txt = generar_diagnostico_y_foto(modelo)
                        if img:
                            with open(img, 'rb') as f:
                                requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto", 
                                              data={'chat_id': TELEGRAM_CHAT_ID, 'caption': txt, 'parse_mode': 'HTML'}, files={'photo': f})
                            if os.path.exists(img): os.remove(img)
        except: time.sleep(2)
        time.sleep(1)

if __name__ == "__main__":
    iniciar_escucha_info()
