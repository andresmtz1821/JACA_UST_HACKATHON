
import paho.mqtt.client as mqtt
import json
import pandas as pd
import numpy as np
from io import StringIO
import os
import random
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

# --- Configuración ---
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_RAW = "invernadero/sensores/raw"
OUTPUT_CSV = "alertas.csv"
TRAINING_CSV_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'GreenhouseClimate.csv')

# --- Modelo de Detección de Anomalías ---
model = None
scaler = None
# Usamos las mismas columnas que el simulador puede alterar para el entrenamiento
feature_cols = [
    "Tair", "Rhair", "HumDef", "AssimLight", "Tot_PAR",
    "EnScr", "BlackScr", "VentLee", "Ventwind", "CO2air"
]

def train_model():
    """
    Carga los datos históricos, los procesa y entrena un modelo Isolation Forest.
    """
    global model, scaler
    print("[iForest Model] Cargando datos de entrenamiento...")
    try:
        df = pd.read_csv(TRAINING_CSV_PATH, low_memory=False)
        df.columns = [c.strip() for c in df.columns]
        if "%time" in df.columns:
            df = df.rename(columns={"%time": "time"})

        # Limpiar datos y seleccionar features, eliminando filas con NAs en nuestras columnas
        df_features = df[feature_cols].dropna()

        # Escalar los datos es una buena práctica para modelos basados en distancia/densidad
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(df_features)
        
        print("[iForest Model] Entrenando modelo Isolation Forest...")
        # Usamos contamination='auto' para que el modelo estime el % de outliers
        model = IsolationForest(contamination='auto', random_state=42, n_jobs=-1)
        model.fit(X_scaled)
        print("[iForest Model] Modelo entrenado y listo para detectar anomalías.")
        return True

    except Exception as e:
        print(f"[iForest Model] Error crítico al entrenar el modelo: {e}")
        return False

# --- Funciones MQTT ---
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[iForest Model] Conectado y suscrito a '{MQTT_TOPIC_RAW}'")
        client.subscribe(MQTT_TOPIC_RAW)
    else:
        print(f"[iForest Model] Fallo al conectar, código: {rc}")

def on_message(client, userdata, msg):
    """
    Callback que se ejecuta con cada mensaje recibido del broker MQTT.
    """
    if not model:
        print("[iForest Model] El modelo aún no está listo, ignorando mensaje.")
        return

    try:
        payload_str = msg.payload.decode('utf-8')
        new_row = pd.read_json(StringIO(payload_str), typ='series')

        # Log de datos recibidos para debugging
        timestamp = new_row.get('time', 'N/A')

        # 1. Preparar los datos del mensaje para la predicción
        features_data = pd.to_numeric(new_row[feature_cols], errors='coerce')

        # Si alguna de nuestras features es NaN después de la conversión, no podemos predecir.
        if features_data.isnull().any():
            missing_cols = features_data[features_data.isnull()].index.tolist()
            print(f"[iForest Model] Mensaje con datos faltantes en {missing_cols}. Time: {timestamp}")
            return

        features = features_data.values.reshape(1, -1)
        features_scaled = scaler.transform(features)

        # 2. Predecir si el dato es una anomalía
        prediction = model.predict(features_scaled)
        anomaly_score = model.score_samples(features_scaled)[0]  # Score de anomalía

        # 3. Actuar si se detecta una anomalía (predicción = -1)
        if prediction[0] == -1:
            print(f"[iForest Model] 🚨 ANOMALÍA DETECTADA! Time: {timestamp}")
            print(f"[iForest Model] Score: {anomaly_score:.4f}, Features: T={features_data['Tair']:.1f}°C, H={features_data['Rhair']:.1f}%, CO2={features_data['CO2air']:.0f}ppm")

            alerta_df = new_row.to_frame().T
            alerta_df['prediction'] = -1 # Añadimos la marca de anomalía
            alerta_df['anomaly_score'] = anomaly_score  # Añadir score

            # Escribir en CSV. Añadir cabecera solo si el archivo no existe.
            alerta_df.to_csv(OUTPUT_CSV, mode='a', header=not os.path.exists(OUTPUT_CSV), index=False)

            # Publicar anomalía al topic MQTT para los agentes
            anomaly_alert = {
                "timestamp": timestamp,
                "anomaly_score": float(anomaly_score),
                "detected_values": {
                    "Tair": float(features_data['Tair']),
                    "Rhair": float(features_data['Rhair']),
                    "CO2air": float(features_data['CO2air']),
                    "AssimLight": float(features_data['AssimLight'])
                },
                "source": "iforest_model"
            }

            client.publish("invernadero/anomalias", json.dumps(anomaly_alert))

        else:
            # Log menos frecuente para datos normales
            if random.randint(1, 10) == 1:  # Solo 10% de los datos normales
                print(f"[iForest Model] Normal - Time: {timestamp}, T={features_data['Tair']:.1f}°C, Score: {anomaly_score:.4f}")

    except Exception as e:
        print(f"[iForest Model] Ocurrió un error en on_message: {e}")
        import traceback
        traceback.print_exc()

# --- Lógica Principal ---
if __name__ == "__main__":
    # Entrenamos el modelo una vez al iniciar el script
    if not train_model():
        print("[iForest Model] No se pudo iniciar el servicio por fallo en el entrenamiento del modelo.")
        exit()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    print(f"[iForest Model] Conectando al broker en {MQTT_BROKER}...")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)

    print("[iForest Model] Servicio iniciado. Esperando mensajes para detectar anomalías...")
    client.loop_forever()
