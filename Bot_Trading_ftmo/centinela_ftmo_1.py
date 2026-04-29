# -*- coding: utf-8 -*-
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import time
from datetime import datetime
import joblib
import warnings
import requests
import sys
import os
from dotenv import load_dotenv

warnings.filterwarnings('ignore')

# Cargar las credenciales ocultas
load_dotenv()

# ==========================================
# CONFIGURACION / IDENTIDAD
# ==========================================
NOMBRE_CUENTA = "FTMO #1"
NUMERO_PRUEBA = 1

BROKER_PATH = r"C:\Users\vr4ux23\Documents\Bot_Trading_ftmo\MT5_FTMO_1\terminal64.exe"
MODELO_PATH = r"C:\Users\vr4ux23\Documents\Bot_Trading_ftmo\MT5_FTMO_1\modelo_rf_eurusd.pkl"
BROKER_SERVIDOR = "FTMO-Demo"

# CREDENCIALES DESDE .ENV
LOGIN_CUENTA = int(os.getenv("FTMO_LOGIN"))
PASSWORD_CUENTA = os.getenv("FTMO_PASSWORD")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SYMBOL = "EURUSD"
TIMEFRAME = mt5.TIMEFRAME_H1
PORCENTAJE_RIESGO = 0.5  
MAGIC_NUMBER = 77761
MAX_PERDIDAS_DIA = 2

# ==========================================
# 2. VARIABLES DE ESTADO GLOBALES
# ==========================================
ticket_activo = None
ganadas, perdidas, trades_hoy, perdidas_hoy = 0, 0, 0, 0
dia_actual = datetime.now().day

# ==========================================
# 3. FUNCIONES DE TELEGRAM (HTML)
# ==========================================
def enviar_telegram(mensaje):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML"}
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"⚠️ Error Telegram: {e}")

# ==========================================
# 4. CIRCUIT BREAKER DIARIO
# ==========================================
def reset_diario():
    global perdidas_hoy, trades_hoy, dia_actual
    hoy = datetime.now().day
    if hoy != dia_actual:
        perdidas_hoy, trades_hoy = 0, 0
        dia_actual = hoy
        print(f"[{NOMBRE_CUENTA}] Reset diario ejecutado.")

def circuit_breaker_activo():
    return perdidas_hoy >= MAX_PERDIDAS_DIA

# ==========================================
# 5. VERIFICACIÓN DE CIERRE
# ==========================================
def verificar_cierre_posicion():
    global ticket_activo, ganadas, perdidas, trades_hoy, perdidas_hoy
    if ticket_activo is None: return

    posicion = mt5.positions_get(ticket=ticket_activo)
    if posicion is None or len(posicion) == 0:
        time.sleep(2)
        deals = mt5.history_deals_get(position=ticket_activo)
        if deals:
            profit_neto = sum((d.profit + d.commission + d.swap) for d in deals if d.entry == 1)
            estado_str = "GANADA 🟢" if profit_neto > 0 else "PERDIDA 🔴"
            if profit_neto > 0: ganadas += 1
            else: perdidas += 1; perdidas_hoy += 1
            
            trades_hoy += 1
            win_rate = (ganadas / (ganadas + perdidas)) * 100 if (ganadas + perdidas) > 0 else 0
            msg_cierre = (
                f"🤖 <b>Centinela Reportando</b>\n"
                f"🏦 Cuenta: {NOMBRE_CUENTA} (Prueba #{NUMERO_PRUEBA})\n"
                f"📈 Par: {SYMBOL}\n"
                f"💰 Resultado: ${profit_neto:.2f}\n"
                f"📊 Estado: {estado_str}\n"
                f"📈 Win Rate: {win_rate:.1f}%\n"
                f"🔢 Trades hoy: {trades_hoy}"
            )
            enviar_telegram(msg_cierre)
            if circuit_breaker_activo():
                enviar_telegram(f"🛑 <b>Circuit Breaker Activado</b>\n🏦 {NOMBRE_CUENTA} (Prueba #{NUMERO_PRUEBA})\nBot pausado por hoy.")
        ticket_activo = None

# ==========================================
# 6. CÁLCULO DE ATR Y LOTAJE
# ==========================================
def calcular_lotaje(riesgo_usd, sl_dist_puntos):
    info = mt5.symbol_info(SYMBOL)
    if not info or info.trade_tick_size == 0: return 0.01
    sl_ticks = sl_dist_puntos / info.trade_tick_size
    lotaje = riesgo_usd / (sl_ticks * info.trade_tick_value)
    lotaje = round(lotaje / info.volume_step) * info.volume_step
    return max(info.volume_min, min(lotaje, info.volume_max))

def procesar_vela():
    global ticket_activo
    if ticket_activo is not None or circuit_breaker_activo(): return

    velas = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 1, 50)
    if velas is None or len(velas) < 50: return

    df = pd.DataFrame(velas)
    df['dist_sma20'] = (df['close'] - df['close'].rolling(20).mean()) / df['close']
    df['vol_ratio'] = df['tick_volume'] / df['tick_volume'].rolling(20).mean()

    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    df['atr'] = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1).rolling(14).mean()

    ultima = df.iloc[-1]
    
    if pd.isna(ultima['dist_sma20']) or pd.isna(ultima['vol_ratio']) or pd.isna(ultima['atr']):
        return

    proba = modelo_rf.predict_proba([[ultima['dist_sma20'], ultima['vol_ratio']]])[0]
    direccion = "LONG" if proba[1] >= 0.60 else ("SHORT" if proba[0] >= 0.60 else None)

    if direccion:
        dist_sl = ultima['atr'] * 1.5
        dist_tp = ultima['atr'] * 3.0
        precio = mt5.symbol_info_tick(SYMBOL).ask if direccion == "LONG" else mt5.symbol_info_tick(SYMBOL).bid
        sl = precio - dist_sl if direccion == "LONG" else precio + dist_sl
        tp = precio + dist_tp if direccion == "LONG" else precio - dist_tp
        
        # --- CORRECCION: RIESGO DINAMICO BASADO EN BALANCE REAL ---
        balance_actual = mt5.account_info().balance
        riesgo_en_dinero = balance_actual * (PORCENTAJE_RIESGO / 100)
        lotaje = calcular_lotaje(riesgo_en_dinero, dist_sl)
        # --------------------------------------------------------
        
        prob_confianza = max(proba) * 100
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": SYMBOL, 
            "volume": float(lotaje), 
            "type": mt5.ORDER_TYPE_BUY if direccion == "LONG" else mt5.ORDER_TYPE_SELL,
            "price": float(precio), "sl": float(sl), "tp": float(tp),
            "magic": MAGIC_NUMBER, "comment": f"ML_{NOMBRE_CUENTA}", "type_filling": mt5.ORDER_FILLING_IOC,
        }

        res = mt5.order_send(request)
        if res.retcode == mt5.TRADE_RETCODE_DONE:
            ticket_activo = res.order
            
            msg_abrir = (
                f"🤖 <b>Centinela Reportando</b>\n"
                f"🏦 Cuenta: {NOMBRE_CUENTA} (Prueba #{NUMERO_PRUEBA})\n"
                f"📈 Par: {SYMBOL}\n"
                f"💰 Lote: {lotaje}\n"
                f"✅ Estado: Orden ejecutada\n"
                f"📊 Dirección: {direccion}\n"
                f"🎯 Entrada: {precio:.5f}\n"
                f"🛑 SL: {sl:.5f}\n"
                f"🎯 TP: {tp:.5f}\n"
                f"🧠 Confianza RF: {prob_confianza:.1f}%"
            )
            enviar_telegram(msg_abrir)

# ==========================================
# 7. CONEXIÓN EN DOS PASOS
# ==========================================
def conectar_mt5():
    print("Iniciando Terminal...")
    if not mt5.initialize(path=BROKER_PATH):
        print(f"❌ Error al abrir MT5. Código: {mt5.last_error()}")
        return False
        
    print("Iniciando Login...")
    for i in range(3):
        if mt5.login(login=LOGIN_CUENTA, password=PASSWORD_CUENTA, server=BROKER_SERVIDOR):
            return True
        print(f"⚠️ Fallo login. Reintento {i+1}/3... Error Code: {mt5.last_error()}")
        time.sleep(5)
    return False

print(f"Conectando a {NOMBRE_CUENTA}...")
if not conectar_mt5():
    exit()

try:
    modelo_rf = joblib.load(MODELO_PATH)
except Exception as e:
    print(f"❌ Error al cargar modelo: {e}"); mt5.shutdown(); exit()

msg_inicio = (
    f"🤖 <b>Centinela Reportando</b>\n"
    f"🏦 Cuenta: {NOMBRE_CUENTA} (Prueba #{NUMERO_PRUEBA})\n"
    f"📈 Par: {SYMBOL}\n"
    f"⚡ Estado: Sistema iniciado\n"
    f"💰 Capital: ${mt5.account_info().balance:,.2f}"
)
enviar_telegram(msg_inicio)

print(f"📡 Radar activo en {NOMBRE_CUENTA}. Vigilando mercado...")

ultima_hora = -1
try:
    while True:
        ahora = datetime.now()
        reset_diario()
        verificar_cierre_posicion()
        if ahora.minute == 0 and ahora.hour != ultima_hora:
            procesar_vela()
            ultima_hora = ahora.hour
            time.sleep(60)
        time.sleep(10)
except Exception as e:
    enviar_telegram(f"⚠️ <b>Loop colapsado</b>\n🏦 {NOMBRE_CUENTA}\n📝 {str(e)}")
finally:
    mt5.shutdown()
