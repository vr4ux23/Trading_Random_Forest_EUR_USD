# -*- coding: utf-8 -*-
import MetaTrader5 as mt5
import requests
import time
import warnings
import os
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
BROKER_SERVIDOR = "FTMO-Demo"
LOGIN_CUENTA = int(os.getenv("FTMO_LOGIN"))
PASSWORD_CUENTA = os.getenv("FTMO_PASSWORD")

def obtener_log_resultados():
    acc = mt5.account_info()
    if acc is None: return "❌ Error: Sin conexión a la cuenta."

    # Obtener trades de HOY
    desde = datetime.now().replace(hour=0, minute=0, second=0)
    hasta = datetime.now()
    deals = mt5.history_deals_get(desde, hasta)
    
    tabla = "<b>N° | Tipo | Profit | Estado</b>\n"
    ganados, perdidas, profit_hoy = 0, 0, 0.0
    
    if deals:
        count = 1
        for d in deals:
            if d.entry == 1: # Solo cierres
                tipo = "BUY" if d.type == mt5.ORDER_TYPE_SELL else "SELL"
                pneto = d.profit + d.commission + d.swap
                profit_hoy += pneto
                icono = "🟢" if pneto > 0 else "🔴"
                if pneto > 0: ganados += 1
                else: perdidas += 1
                tabla += f"{count} | {tipo} | ${pneto:.2f} | {icono}\n"
                count += 1
    else:
        tabla += "<i>Sin movimientos hoy.</i>"

    resumen = (
        f"📊 <b>RESULTADOS HOY: {acc.name}</b>\n"
        f"🏦 Balance: <b>${acc.balance:,.2f}</b>\n"
        f"📈 Profit Hoy: <b>${profit_hoy:.2f}</b>\n\n"
        f"🏆 <b>DESEMPEÑO:</b>\n"
        f"✅ Win: {ganados} | ❌ Loss: {perdidas}\n"
        f"🎯 WR: {(ganados/(ganados+perdidas)*100 if (ganados+perdidas)>0 else 0):.1f}%\n\n"
        f"📋 <b>TABLA:</b>\n{tabla}"
    )
    return resumen

def iniciar_escucha_resultados():
    print("--- MONITOR REMOTO: COMANDO /resultados ACTIVO ---")
    if not mt5.initialize(path=BROKER_PATH): return
    mt5.login(login=LOGIN_CUENTA, password=PASSWORD_CUENTA, server=BROKER_SERVIDOR)
    
    ultimo_id = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={ultimo_id + 1}&timeout=10"
            updates = requests.get(url).json().get("result", [])
            for update in updates:
                ultimo_id = update["update_id"]
                if "message" in update and "text" in update["message"]:
                    if update["message"]["text"] == "/resultados":
                        txt = obtener_log_resultados()
                        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                                      data={'chat_id': TELEGRAM_CHAT_ID, 'text': txt, 'parse_mode': 'HTML'})
        except: time.sleep(2)
        time.sleep(1)

if __name__ == "__main__":
    iniciar_escucha_resultados()
