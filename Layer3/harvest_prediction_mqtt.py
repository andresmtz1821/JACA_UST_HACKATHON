#!/usr/bin/env python3
"""
Capa 3: Modelo Predictivo de Cosecha - Integración MQTT
Usa exactamente el modelo Nadaraya-Watson del Model.ipynb pero integrado al pipeline MQTT
"""

import pandas as pd
import numpy as np
import json
import os
import time
import paho.mqtt.client as mqtt
from datetime import datetime, timedelta
import logging

# --- Configuración ---
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_MODEL_DATA = "invernadero/model/data_12h"
MQTT_TOPIC_PREDICTIONS = "invernadero/predicciones"

TRAINING_DATA = os.path.join(os.path.dirname(__file__), '..', 'dataset_batches_5min_cosecha_ult24h_DEBUG.csv')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HarvestPredictionMQTT:
    def __init__(self):
        self.model_ready = False
        self.X_train = None
        self.Y_train = None
        self.cols_continuas = None
        self.main_cols = ['CO2air__mean', 'Cum_irr__mean', 'EC_drain_PC__mean', 'HumDef__mean',
                         'PipeGrow__mean', 'PipeLow__mean', 'Rhair__mean', 'Tair__mean',
                         'Tot_PAR__mean', 'pH_drain_PC__mean']

        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.load_model()

    def load_model(self):
        try:
            logger.info("Cargando modelo como en Model.ipynb...")
            df = pd.read_csv(TRAINING_DATA, low_memory=False)
            
            # 1. Crear la columna 'tiempo_final' primero
            df['__time__'] = pd.to_datetime(df['__time__'])
            df['tiempo_final'] = df.groupby('cosecha')['__time__'].transform(lambda x: (x.max() - x).dt.total_seconds() / 86400)

            # 2. Renombrar columnas para consistencia del modelo
            df.rename(columns={
                'CO2air': 'CO2air__mean', 'Cum_irr': 'Cum_irr__mean', 'EC_drain_PC': 'EC_drain_PC__mean',
                'HumDef': 'HumDef__mean', 'PipeGrow': 'PipeGrow__mean', 'PipeLow': 'PipeLow__mean',
                'Rhair': 'Rhair__mean', 'Tair': 'Tair__mean', 'Tot_PAR': 'Tot_PAR__mean',
                'pH_drain_PC': 'pH_drain_PC__mean'
            }, inplace=True)

            # 3. Ahora, convertir a numérico (la columna 'tiempo_final' ya existe)
            for col in self.main_cols + ['tiempo_final']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df.dropna(subset=self.main_cols + ['tiempo_final'], inplace=True)
            
            data = df.copy()
            
            # --- Creación de Lags ---
            cols_continuas = self.main_cols.copy()
            lags = 10
            lag_cols = []
            for p in range(1, lags):
                for c in cols_continuas:
                    col_name = f"{c}-{p}"
                    data[col_name] = data[c].shift(p)
                    mean_val = data[col_name].mean()
                    data[col_name] = data[col_name].fillna(mean_val)
                    lag_cols.append(col_name)
            
            data.dropna(inplace=True)
            
            self.cols_continuas = cols_continuas + lag_cols
            self.X_train = data[self.cols_continuas].values
            self.Y_train = data['tiempo_final'].values
            self.model_ready = True

            logger.info(f"✅ Modelo cargado con {len(data)} muestras")
            logger.info(f"Features: {len(self.cols_continuas)} (incluye {len(lag_cols)} lags)")
            logger.info(f"Rango tiempo_final: {self.Y_train.min():.1f} - {self.Y_train.max():.1f}")

        except Exception as e:
            logger.error(f"Error cargando modelo: {e}", exc_info=True)

    def nw_class_prob_vectorized(self, X, Y, x, h=1.0):
        try:
            X = np.asarray(X, dtype=np.float64)
            Y = np.asarray(Y, dtype=np.float64)
            x = np.asarray(x, dtype=np.float64)

            if np.any(np.isnan(X)) or np.any(np.isnan(Y)) or np.any(np.isnan(x)):
                logger.error("Datos contienen NaN")
                return np.mean(Y) if len(Y) > 0 else 35.0

            d = X.shape[1]
            Sigma = np.cov(X, rowvar=False) * h**2 + 1e-6 * np.eye(d)
            inv_Sigma = np.linalg.inv(Sigma)
            det_Sigma = np.linalg.det(Sigma)

            diffs = X - x
            mdist2 = np.einsum('ij,jk,ik->i', diffs, inv_Sigma, diffs)
            weights = np.exp(-0.5 * mdist2) / np.sqrt((2 * np.pi)**d * det_Sigma)

            weight_sum = np.sum(weights)
            if weight_sum <= 1e-50:
                logger.warning(f"Suma de pesos muy pequeña: {weight_sum}. Usando fallback.")
                closest_idx = np.argmin(mdist2)
                return Y[closest_idx]

            weighted_prob = np.sum(weights * Y) / weight_sum
            return weighted_prob if not np.isnan(weighted_prob) else np.mean(Y)

        except Exception as e:
            logger.error(f"Error en Nadaraya-Watson: {e}", exc_info=True)
            return np.mean(Y) if len(Y) > 0 else 35.0

    def prepare_features_for_prediction(self, data_row):
        try:
            main_features = [float(data_row.get(col, np.mean(self.X_train[:, i]))) for i, col in enumerate(self.main_cols)]
            
            current_vector = np.array(main_features)
            
            train_main_features = self.X_train[:, :10]
            distances = np.sum((train_main_features - current_vector)**2, axis=1)
            closest_idx = np.argmin(distances)
            
            closest_lags = self.X_train[closest_idx, 10:]
            
            all_features = np.concatenate([current_vector, closest_lags])

            logger.info(f"Usando fila similar del entrenamiento (idx {closest_idx}) para lags.")
            logger.info(f"✅ Features preparadas: {len(all_features)} valores, rango [{all_features.min():.2f}, {all_features.max():.2f}]")
            
            return all_features

        except Exception as e:
            logger.error(f"Error preparando features: {e}", exc_info=True)
            return self.X_train[0].copy()

    def predict_harvest_days(self, features_row):
        if not self.model_ready:
            logger.warning("Modelo no está listo")
            return None
        
        x = self.prepare_features_for_prediction(features_row)
        # Usar bandwidth más permisivo para datos con ruido sintético (2.5 en lugar de 1.0)
        prediction = self.nw_class_prob_vectorized(self.X_train, self.Y_train, x, h=2.5)
        return prediction

    def on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            logger.info("Conectado al broker MQTT")
            client.subscribe(MQTT_TOPIC_MODEL_DATA)
            logger.info(f"Suscrito a: {MQTT_TOPIC_MODEL_DATA}")
        else:
            logger.error(f"Fallo al conectar MQTT, código: {rc}")

    def on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode('utf-8'))
            # Manejar tanto 'harvest_number' como 'cosecha' para compatibilidad
            harvest_id = data.get('harvest_number', data.get('cosecha', 'N/A'))
            dias_reales = data.get('tiempo_final', 'N/A')
            
            logger.info(f"📨 Mensaje recibido - Cosecha: {harvest_id}, Días Reales: {dias_reales}")
            
            prediction = self.predict_harvest_days(data)

            if prediction is not None:
                self.publish_prediction(prediction, data, client)
            else:
                logger.error("No se pudo generar predicción")

        except Exception as e:
            logger.error(f"Error procesando mensaje MQTT: {e}", exc_info=True)

    def publish_prediction(self, prediction, source_data, client):
        try:
            prediction_rounded = round(float(prediction), 1)
            
            status_map = {
                (0, 25): ("CRÍTICO", "red"),
                (25, 35): ("PRÓXIMO", "orange"),
                (35, 45): ("NORMAL", "green"),
            }
            status, color = next(((s, c) for (lower, upper), (s, c) in status_map.items() if lower <= prediction_rounded < upper), ("EXTENDIDO", "yellow"))

            # Obtener harvest_number con compatibilidad
            harvest_id = source_data.get('harvest_number', source_data.get('cosecha'))
            
            prediction_result = {
                "timestamp": datetime.now().isoformat(),
                "harvest_number": harvest_id,
                "days_to_harvest_real": source_data.get('tiempo_final'),
                "tiempo_final_dias_pred": prediction_rounded,
                "status": status,
                "color": color,
                "model": "nadaraya_watson_v3"
            }

            payload = json.dumps(prediction_result)
            client.publish(MQTT_TOPIC_PREDICTIONS, payload)
            logger.info(f"🚀 PREDICCIÓN (Cosecha {prediction_result['harvest_number']}): {prediction_rounded} días (Real: {prediction_result['days_to_harvest_real']}) -> {status}")

        except Exception as e:
            logger.error(f"Error publicando predicción: {e}", exc_info=True)

    def run(self):
        try:
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            logger.info("🌱 Modelo de Predicción de Cosecha v3 iniciado")
            logger.info(f"   Algoritmo: Nadaraya-Watson (Corregido)")
            logger.info(f"   Suscrito a: {MQTT_TOPIC_MODEL_DATA}")
            logger.info(f"   Publicando en: {MQTT_TOPIC_PREDICTIONS}")
            self.mqtt_client.loop_forever()
        except KeyboardInterrupt:
            logger.info("\n🛑 Modelo detenido por el usuario")
        except Exception as e:
            logger.error(f"Error en ejecución: {e}", exc_info=True)
        finally:
            self.mqtt_client.disconnect()
            logger.info("Cliente MQTT desconectado")

def main():
    model = HarvestPredictionMQTT()
    model.run()

if __name__ == "__main__":
    main()
