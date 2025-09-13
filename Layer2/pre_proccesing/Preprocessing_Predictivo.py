
import paho.mqtt.client as mqtt
import json
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from io import StringIO
import os

# --- Configuración ---
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_RAW = "invernadero/sensores/raw"
OUTPUT_CSV = "features_predictivas.csv"
WINDOW = "1h"

# --- Buffer Global ---
data_buffer = pd.DataFrame()

# --- Lógica de Procesamiento ---
def to_numeric_df(df, exclude_cols):
    for c in df.columns:
        if c in exclude_cols: continue
        if df[c].dtype == 'object': df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", "."), errors="coerce")
    return df

def add_trend_slope(group, cols):
    res = {}
    if group.shape[0] <= 1:
        for c in cols: res[f"{c}__slope"] = np.nan
        return pd.Series(res)
    t0 = group["time"].min()
    x = (group["time"] - t0).dt.total_seconds().values.reshape(-1, 1)
    for c in cols:
        y = group[c].values
        mask = np.isfinite(y)
        if mask.sum() >= 2:
            lr = LinearRegression()
            lr.fit(x[mask], y[mask])
            res[f"{c}__slope"] = lr.coef_[0]
        else:
            res[f"{c}__slope"] = np.nan
    return pd.Series(res)

def process_predictive_window(df_chunk):
    print(f"Procesando ventana de datos con {len(df_chunk)} filas...")
    df = df_chunk.copy()
    batch_cols = [c for c in df.columns if c.lower().startswith("batch")]
    exclude_cols = set(["time", "Unnamed: 0"] + batch_cols)
    df = to_numeric_df(df, exclude_cols=exclude_cols)
    all_numeric = [c for c in df.select_dtypes(include=[np.number]).columns if c not in exclude_cols]
    keep_keywords = ["vip", "air", "Cum_irr", "water_sup", "EC_drain_PC", "pH_drain_PC", "Tot_PAR", "AssimLight", "Tot_PAR_Lamps", "Vent", "Pipe", "HumDef", "Tair", "Rhair"]
    relevant_cols = sorted(set([c for c in all_numeric if any(k.lower() in c.lower() for k in keep_keywords)] + ['Cum_irr']))
    df["window_start"] = df["time"].dt.floor(WINDOW)
    def pct25(x): return np.nanpercentile(x, 25)
    def pct75(x): return np.nanpercentile(x, 75)
    def rng(x): return np.nanmax(x) - np.nanmin(x)
    agg_dict = {f"{c}__{agg}": (c, agg_func) for c in relevant_cols for agg, agg_func in [("mean", "mean"), ("median", "median"), ("min", "min"), ("max", "max"), ("std", "std"), ("p25", pct25), ("p75", pct75), ("range", rng)]}
    feat_base = df.groupby("window_start").agg(**agg_dict).reset_index()
    trend_parts = []
    for win_start, g in df.groupby("window_start"): 
        part = add_trend_slope(g[["time"] + relevant_cols].copy(), relevant_cols).to_frame().T
        part["window_start"] = win_start
        trend_parts.append(part)
    feat_trend = pd.concat(trend_parts, ignore_index=True)
    features_win = pd.merge(feat_base, feat_trend, on="window_start", how="left")
    print(f"Ventana procesada. Shape de features: {features_win.shape}")
    return features_win

# --- Funciones MQTT ---
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0: print(f"Conectado al Broker y suscrito a '{MQTT_TOPIC_RAW}'")
    else: print(f"Fallo al conectar, código: {rc}")
    client.subscribe(MQTT_TOPIC_RAW)

def on_message(client, userdata, msg):
    global data_buffer
    try:
        payload_str = msg.payload.decode('utf-8')
        new_row_df = pd.read_json(StringIO(payload_str), typ='series').to_frame().T

        # Log datos recibidos para debugging
        timestamp = new_row_df.iloc[0].get('time', 'N/A')

        new_row_df['time'] = pd.to_datetime(new_row_df['time'], errors='coerce')
        if new_row_df.empty or pd.isna(new_row_df['time'].iloc[0]):
            print(f"[Preprocessing] Mensaje con timestamp inválido: {timestamp}")
            return

        data_buffer = pd.concat([data_buffer, new_row_df], ignore_index=True)
        data_buffer['time'] = pd.to_datetime(data_buffer['time'])

        # Log del buffer cada 10 mensajes
        if len(data_buffer) % 10 == 0:
            print(f"[Preprocessing] Buffer: {len(data_buffer)} filas, último timestamp: {data_buffer['time'].iloc[-1]}")

        first_window = data_buffer['time'].iloc[0].floor(WINDOW)
        last_window = data_buffer['time'].iloc[-1].floor(WINDOW)

        if first_window < last_window:
            df_to_process = data_buffer[data_buffer['time'] < last_window]
            print(f"[Preprocessing] Procesando ventana: {first_window} a {last_window} ({len(df_to_process)} filas)")

            features_df = process_predictive_window(df_to_process)
            if not features_df.empty:
                print(f"[Preprocessing] ✅ Escribiendo {len(features_df)} fila(s) de features en {OUTPUT_CSV}")
                features_df.to_csv(OUTPUT_CSV, mode='a', header=not os.path.exists(OUTPUT_CSV), index=False)

                # Publicar features al topic MQTT para modelo predictivo
                for _, row in features_df.iterrows():
                    feature_data = {
                        "timestamp": row["window_start"].isoformat() if pd.notna(row["window_start"]) else None,
                        "features": row.drop("window_start").to_dict(),
                        "source": "preprocessing_predictive"
                    }
                    client.publish("invernadero/features_predictivas", json.dumps(feature_data, default=str))

            data_buffer = data_buffer[data_buffer['time'] >= last_window].reset_index(drop=True)
            print(f"[Preprocessing] Buffer limpiado. {len(data_buffer)} filas restantes.")

    except Exception as e:
        print(f"[Preprocessing] Ocurrió un error en on_message: {e}")
        import traceback
        traceback.print_exc()

# --- Lógica Principal ---
if __name__ == "__main__":
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    print(f"Conectando al broker en {MQTT_BROKER}...")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    print("Servicio de pre-procesamiento PREDICTIVO iniciado. Acumulando datos...")
    client.loop_forever()
