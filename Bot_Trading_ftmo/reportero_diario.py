# -*- coding: utf-8 -*-
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import joblib
import requests
import time
import os
from datetime import datetime
from dotenv import load_dotenv

# Cargar las credenciales ocultas
load_dotenv()

# ==========================================
# 1. CONFIGURACIÓN Y CREDENCIALES
# ==========================================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BROKER_PATH = r"C:\Users\vr4ux23\Documents\Bot_Trading_ftmo\MT5_FTMO_1\terminal64.exe"
MODELO_PATH = r"C:\Users\vr4ux23\Documents\Bot_Trading_ftmo\MT5_FTMO_1\modelo_rf_eurusd.pkl"

BROKER_SERVIDOR = "FTMO-Demo"
LOGIN_CUENTA = int(os.getenv("FTMO_LOGIN"))
PASSWORD_CUENTA = os.getenv("FTMO_PASSWORD")
SYMBOL = "EURUSD"
TIMEFRAME = mt5.TIMEFRAME_H1

# ==========================================
# 2. VARIABLES DE SEGUIMIENTO DIARIO
# ==========================================
stats_diarias = {
    "velas_analizadas": 0,
    "señales_ejecutadas": 0,
    "señales_descartadas": 0,
    "mejor_confianza": 0.0,
    "mejor_direccion": "",
    "menor_confianza": 100.0
}

ultima_alerta_preseñal = None
ultimo_reporte_enviado = None

# ==========================================
# 3. FUNCIONES CORE
# ==========================================
def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Telegram enviado.")
    except Exception as e:
        print(f"Error Telegram: {e}")

def conectar_mt5():
    if not mt5.initialize(path=BROKER_PATH):
        return False
    for i in range(3):
        if mt5.login(login=LOGIN_CUENTA, password=PASSWORD_CUENTA, server=BROKER_SERVIDOR):
            return True
        time.sleep(5)
    return False

def obtener_datos_mercado():
    rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, 21)
    if rates is None or len(rates) < 21:
        return None
    
    df = pd.DataFrame(rates)
    df['close'] = df['close'].astype(float)
    df['tick_volume'] = df['tick_volume'].astype(float)
    
    precio_actual = df['close'].iloc[-1]
    volumen_actual = df['tick_volume'].iloc[-1]
    
    sma20 = df['close'].iloc[:-1].mean()
    volumen_promedio_20 = df['tick_volume'].iloc[:-1].mean()
    
    dist_sma20 = (precio_actual - sma20) / sma20
    vol_ratio = volumen_actual / volumen_promedio_20 if volumen_promedio_20 > 0 else 0
    
    return {
        "precio": round(precio_actual, 5),
        "dist_sma20": round(dist_sma20, 5),
        "vol_ratio": round(vol_ratio, 2)
    }

def generar_explicacion(dist_sma20, vol_ratio, confianza, umbral=60.0):
    texto_dist = "dentro del rango normal de la media móvil" if abs(dist_sma20) < 0.0015 else "alejado de su media histórica"
    texto_vol = "no supera el umbral institucional" if vol_ratio < 1.0 else "muestra fuerte inyección de capital"
    
    decision = "SÍ" if confianza >= umbral else "NO"
    
    razon = (f"El precio está {texto_dist} (dist_sma20 = {dist_sma20}) y el volumen "
             f"{texto_vol} (vol_ratio = {vol_ratio}). El modelo asigna una probabilidad "
             f"del {confianza}% de éxito.")
    
    return decision, razon

def resetear_stats():
    global stats_diarias
    stats_diarias = {
        "velas_analizadas": 0, "señales_ejecutadas": 0, "señales_descartadas": 0,
        "mejor_confianza": 0.0, "mejor_direccion": "", "menor_confianza": 100.0
    }

# ==========================================
# 4. CICLO PRINCIPAL
# ==========================================
def iniciar_reportero():
    global stats_diarias, ultima_alerta_preseñal, ultimo_reporte_enviado
    
    print("Iniciando Reportero Quant...")
    try:
        modelo_rf = joblib.load(MODELO_PATH)
        print("Cerebro RF cargado correctamente.")
    except Exception as e:
        print(f"Error al cargar modelo: {e}")
        return

    enviar_telegram("🤖 <b>Reportero Diario Iniciado</b>\n\nMonitoreando métricas del modelo RF en paralelo.")

    while True:
        if not conectar_mt5():
            time.sleep(60)
            continue
            
        ahora = datetime.now()
        hora = ahora.hour
        minuto = ahora.minute
        
        datos = obtener_datos_mercado()
        if datos:
            X_actual = pd.DataFrame([{"dist_sma20": datos["dist_sma20"], "vol_ratio": datos["vol_ratio"]}])
            prediccion = modelo_rf.predict(X_actual)[0]
            probabilidades = modelo_rf.predict_proba(X_actual)[0]
            confianza = round(max(probabilidades) * 100, 1)
            direccion = "LONG" if prediccion == 1 else "SHORT"
            
            if minuto < 5 and ultimo_reporte_enviado != hora: 
                stats_diarias["velas_analizadas"] += 1
                if confianza >= 60.0:
                    stats_diarias["señales_ejecutadas"] += 1
                else:
                    stats_diarias["señales_descartadas"] += 1
                    
                if confianza > stats_diarias["mejor_confianza"]:
                    stats_diarias["mejor_confianza"] = confianza
                    stats_diarias["mejor_direccion"] = direccion
                if confianza < stats_diarias["menor_confianza"]:
                    stats_diarias["menor_confianza"] = confianza

            decision, razon = generar_explicacion(datos["dist_sma20"], datos["vol_ratio"], confianza)

            if hora in [2, 8, 13] and minuto < 5 and ultimo_reporte_enviado != hora:
                sesion = "Asia" if hora == 2 else "Londres" if hora == 8 else "Nueva York"
                msg_sesion = (
                    f"📊 <b>Reporte de Sesión</b>\n"
                    f"⏰ Sesión: {sesion}\n"
                    f"📈 Par: {SYMBOL}\n"
                    f"💹 Precio actual: {datos['precio']}\n"
                    f"📐 Distancia SMA20: {datos['dist_sma20'] * 100:.2f}%\n"
                    f"📦 Volumen ratio: {datos['vol_ratio']}\n"
                    f"🧠 Confianza RF actual: {confianza}% ({direccion})\n"
                    f"🎯 ¿Señal activa?: <b>{decision}</b>\n\n"
                    f"📝 <b>Razón:</b> {razon}"
                )
                enviar_telegram(msg_sesion)
                ultimo_reporte_enviado = hora

            elif hora == 21 and minuto < 5 and ultimo_reporte_enviado != hora:
                msg_cierre = (
                    f"📅 <b>Resumen del día {SYMBOL}</b>\n\n"
                    f"📊 Velas analizadas hoy: {stats_diarias['velas_analizadas']}\n"
                    f"🎯 Señales generadas: {stats_diarias['señales_ejecutadas'] + stats_diarias['señales_descartadas']}\n"
                    f"⚡ Señales ejecutadas (>60%): {stats_diarias['señales_ejecutadas']}\n"
                    f"😴 Señales descartadas (<60%): {stats_diarias['señales_descartadas']}\n"
                    f"📈 Mejor confianza del día: {stats_diarias['mejor_confianza']}% ({stats_diarias['mejor_direccion']})\n"
                    f"📉 Menor confianza del día: {stats_diarias['menor_confianza']}%\n\n"
                    f"💤 <b>Insight del Modelo:</b>\n"
                    f"El comportamiento promedio hoy mantuvo un dist_sma20 de {datos['dist_sma20']} "
                    f"y un vol_ratio de {datos['vol_ratio']}, explicando el rechazo sistemático de operaciones."
                )
                enviar_telegram(msg_cierre)
                ultimo_reporte_enviado = hora
                resetear_stats()

            if 55.0 <= confianza < 60.0:
                if ultima_alerta_preseñal != hora:
                    msg_pre = (
                        f"⚡ <b>Alerta Pre-Señal</b>\n"
                        f"📈 Par: {SYMBOL} H1\n"
                        f"🧠 Confianza: {confianza}% (umbral: 60%)\n"
                        f"📐 dist_sma20: {datos['dist_sma20']}\n"
                        f"📦 vol_ratio: {datos['vol_ratio']}\n\n"
                        f"📝 <i>El modelo {direccion} está cerca de disparar pero no alcanza el umbral de confianza aún. Atento a la próxima hora.</i>"
                    )
                    enviar_telegram(msg_pre)
                    ultima_alerta_preseñal = hora

        mt5.shutdown()
        time.sleep(300)

if __name__ == "__main__":
    iniciar_reportero()
