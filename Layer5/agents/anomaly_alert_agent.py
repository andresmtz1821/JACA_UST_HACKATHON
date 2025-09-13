#!/usr/bin/env python3
"""
Agente de Alertas Emergentes - Layer 5
Utiliza tinyllama:1.1b para interpretar anomalías y generar alertas críticas inmediatas
"""

import paho.mqtt.client as mqtt
import pandas as pd
import json
import requests
import time
from datetime import datetime
import os

# --- Configuración ---
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_ANOMALIES = "invernadero/anomalias"
MQTT_TOPIC_ALERTS = "invernadero/alertas/emergentes"

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "tinyllama:1.1b"

# Path del archivo de alertas
ALERTAS_CSV_PATH = "../Layer2/tinyml_model/alertas.csv"

class AnomalyAlertAgent:
    def __init__(self):
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.processed_alerts = set()  # Para evitar duplicados

    def on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            print(f"[Anomaly Alert Agent] Conectado al broker MQTT")
            client.subscribe(MQTT_TOPIC_ANOMALIES)
            # También monitoreamos el archivo CSV directamente
            self.monitor_csv_file()
        else:
            print(f"[Anomaly Alert Agent] Error de conexión: {rc}")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            self.process_anomaly(payload)
        except Exception as e:
            print(f"[Anomaly Alert Agent] Error procesando mensaje: {e}")

    def monitor_csv_file(self):
        """Monitorea el archivo alertas.csv para nuevas anomalías"""
        if not os.path.exists(ALERTAS_CSV_PATH):
            print(f"[Anomaly Alert Agent] Archivo {ALERTAS_CSV_PATH} no encontrado")
            return

        try:
            df = pd.read_csv(ALERTAS_CSV_PATH)
            anomalies = df[df['prediction'] == -1]

            for _, row in anomalies.iterrows():
                row_id = f"{row['time']}-{row.get('Tair', 0)}"
                if row_id not in self.processed_alerts:
                    self.process_anomaly(row.to_dict())
                    self.processed_alerts.add(row_id)
        except Exception as e:
            print(f"[Anomaly Alert Agent] Error leyendo CSV: {e}")

    def process_anomaly(self, anomaly_data):
        """Procesa una anomalía y genera alerta con SLM"""
        try:
            # Crear prompt para el SLM
            prompt = self.create_alert_prompt(anomaly_data)

            # Consultar SLM
            alert_message = self.query_ollama(prompt)

            # Crear alerta estructurada
            alert = {
                "timestamp": datetime.now().isoformat(),
                "severity": self.determine_severity(anomaly_data),
                "message": alert_message,
                "raw_data": anomaly_data,
                "agent": "anomaly_alert"
            }

            # Publicar alerta
            self.mqtt_client.publish(MQTT_TOPIC_ALERTS, json.dumps(alert))
            print(f"[Anomaly Alert Agent] Alerta publicada: {alert_message[:50]}...")

        except Exception as e:
            print(f"[Anomaly Alert Agent] Error procesando anomalía: {e}")

    def create_alert_prompt(self, data):
        """Crea prompt específico para generar alertas de invernadero"""
        temp = data.get('Tair', 'N/A')
        humidity = data.get('Rhair', 'N/A')
        co2 = data.get('CO2air', 'N/A')
        light = data.get('AssimLight', 'N/A')

        prompt = f"""Eres un experto en agricultura de invernaderos de tomate. Se detectó una ANOMALÍA crítica.

Datos del sensor:
- Temperatura: {temp}°C
- Humedad: {humidity}%
- CO2: {co2} ppm
- Luz: {light}
- Tiempo: {data.get('time', 'N/A')}

Genera UNA alerta CONCISA y CRÍTICA (máximo 80 caracteres) que indique:
1. El problema específico
2. La acción inmediata requerida

Usa emojis para urgencia. Formato: "🚨 [PROBLEMA] - [ACCIÓN]"
"""
        return prompt

    def determine_severity(self, data):
        """Determina la severidad de la alerta basada en los datos"""
        temp = float(data.get('Tair', 0))
        humidity = float(data.get('Rhair', 0))
        co2 = float(data.get('CO2air', 0))

        # Lógica de severidad para tomates
        if temp > 35 or temp < 10:
            return "CRITICAL"
        elif humidity > 90 or humidity < 40:
            return "HIGH"
        elif co2 > 1000 or co2 < 300:
            return "MEDIUM"
        else:
            return "LOW"

    def query_ollama(self, prompt):
        """Consulta el modelo SLM local"""
        try:
            payload = {
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "max_tokens": 100
                }
            }

            response = requests.post(OLLAMA_URL, json=payload, timeout=30)
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "Error generando alerta").strip()
            else:
                return f"🚨 ANOMALÍA DETECTADA - Revisar sistema"

        except Exception as e:
            print(f"[Anomaly Alert Agent] Error consultando Ollama: {e}")
            return f"🚨 ANOMALÍA CRÍTICA - Intervención necesaria"

    def start(self):
        """Inicia el agente"""
        print("[Anomaly Alert Agent] Iniciando agente de alertas emergentes...")
        self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)

        # Loop para monitorear CSV periódicamente
        import threading
        def csv_monitor():
            while True:
                self.monitor_csv_file()
                time.sleep(5)  # Revisa cada 5 segundos

        csv_thread = threading.Thread(target=csv_monitor, daemon=True)
        csv_thread.start()

        # Mantener conexión MQTT
        self.mqtt_client.loop_forever()

if __name__ == "__main__":
    agent = AnomalyAlertAgent()
    agent.start()