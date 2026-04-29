import MetaTrader5 as mt5
from datetime import datetime

mt5.initialize()

# Usar EURUSD que siempre tiene tick disponible
mt5.symbol_select("EURUSD", True)
tick = mt5.symbol_info_tick("EURUSD")

hora_servidor = datetime.fromtimestamp(tick.time)
hora_local = datetime.now()
diferencia = hora_servidor - hora_local
horas_diff = round(diferencia.total_seconds() / 3600)

print(f"Hora servidor FTMO:  {hora_servidor.strftime('%H:%M:%S')}")
print(f"Hora local Azure:    {hora_local.strftime('%H:%M:%S')}")
print(f"Diferencia:          {horas_diff} horas")
print(f"Apertura NY (09:30) en hora local Azure: {9 + horas_diff}:30")

mt5.shutdown()