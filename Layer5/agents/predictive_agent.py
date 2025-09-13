#!/usr/bin/env python3
"""
Agente de Recomendaciones Inteligentes - Layer 5
Utiliza deepseek-r1:8b para interpretar resultados predictivos y generar recomendaciones estratégicas
"""

import paho.mqtt.client as mqtt
import pandas as pd
import json
import requests
import time
from datetime import datetime, timedelta
import os

# --- Configuración ---
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_PREDICTIONS = "invernadero/predicciones"
MQTT_TOPIC_RECOMMENDATIONS = "invernadero/recomendaciones"

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "deepseek-r1:8b"

# Paths de archivos de datos
FEATURES_CSV_PATH = "../Layer2/pre_proccesing/features_predictivas.csv"
ALERTAS_CSV_PATH = "../Layer2/tinyml_model/alertas.csv"

class PredictiveAgent:
    def __init__(self):
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message

        # Cache para evitar procesar los mismos datos
        self.processed_predictions = set()
        self.last_analysis_time = None

        # Contexto histórico
        self.environmental_context = {
            "optimal_ranges": {
                "temperature": {"min": 18, "max": 28},
                "humidity": {"min": 60, "max": 80},
                "co2": {"min": 400, "max": 800},
                "light": {"min": 100, "max": 300}
            },
            "growth_stages": {
                "seedling": {"days": 30, "temp_ideal": 22, "humidity_ideal": 70},
                "vegetative": {"days": 60, "temp_ideal": 24, "humidity_ideal": 65},
                "flowering": {"days": 45, "temp_ideal": 26, "humidity_ideal": 60},
                "fruiting": {"days": 90, "temp_ideal": 23, "humidity_ideal": 65}
            }
        }

    def on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            print(f"[Predictive Agent] Conectado al broker MQTT")
            client.subscribe(MQTT_TOPIC_PREDICTIONS)
            # Iniciar análisis periódico
            self.start_periodic_analysis()
        else:
            print(f"[Predictive Agent] Error de conexión: {rc}")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            self.process_prediction(payload)
        except Exception as e:
            print(f"[Predictive Agent] Error procesando mensaje: {e}")

    def start_periodic_analysis(self):
        """Inicia análisis periódico cada 5 minutos"""
        import threading
        def periodic_analysis():
            while True:
                try:
                    self.analyze_current_conditions()
                    time.sleep(300)  # 5 minutos
                except Exception as e:
                    print(f"[Predictive Agent] Error en análisis periódico: {e}")
                    time.sleep(60)  # Retry en 1 minuto

        analysis_thread = threading.Thread(target=periodic_analysis, daemon=True)
        analysis_thread.start()

    def analyze_current_conditions(self):
        """Analiza condiciones actuales y genera recomendaciones"""
        try:
            current_data = self.load_current_data()
            if not current_data:
                return

            # Generar análisis completo
            analysis = self.comprehensive_analysis(current_data)

            if analysis:
                recommendation = {
                    "timestamp": datetime.now().isoformat(),
                    "analysis": analysis,
                    "agent": "predictive_recommendations",
                    "confidence": self.calculate_confidence(current_data)
                }

                # Publicar recomendación
                self.mqtt_client.publish(MQTT_TOPIC_RECOMMENDATIONS, json.dumps(recommendation))
                print(f"[Predictive Agent] Recomendación publicada: {analysis['summary'][:50]}...")

        except Exception as e:
            print(f"[Predictive Agent] Error en análisis: {e}")

    def load_current_data(self):
        """Carga datos actuales de sensores y características"""
        data = {}

        try:
            # Cargar features predictivas
            if os.path.exists(FEATURES_CSV_PATH):
                df_features = pd.read_csv(FEATURES_CSV_PATH)
                if not df_features.empty:
                    data['features'] = df_features.tail(1).to_dict('records')[0]

            # Cargar alertas recientes
            if os.path.exists(ALERTAS_CSV_PATH):
                df_alerts = pd.read_csv(ALERTAS_CSV_PATH)
                recent_alerts = df_alerts[df_alerts['prediction'] == -1].tail(5)
                data['recent_anomalies'] = recent_alerts.to_dict('records')

            return data if data else None

        except Exception as e:
            print(f"[Predictive Agent] Error cargando datos: {e}")
            return None

    def comprehensive_analysis(self, data):
        """Realiza análisis comprensivo usando deepseek-r1:8b"""
        try:
            prompt = self.create_analysis_prompt(data)
            analysis_text = self.query_ollama(prompt)

            return {
                "summary": analysis_text,
                "prediction": self.extract_prediction_insights(data),
                "recommendation": analysis_text,
                "priority_actions": self.extract_priority_actions(analysis_text),
                "risk_assessment": self.assess_risks(data)
            }

        except Exception as e:
            print(f"[Predictive Agent] Error en análisis comprensivo: {e}")
            return None

    def create_analysis_prompt(self, data):
        """Crea prompt detallado para análisis predictivo"""
        features = data.get('features', {})
        anomalies = data.get('recent_anomalies', [])

        temp_avg = features.get('Tair_mean', 0)
        humidity_avg = features.get('Rhair_mean', 0)
        co2_avg = features.get('CO2air_mean', 0)
        light_avg = features.get('AssimLight_mean', 0)

        prompt = f"""Eres un experto consultor en agricultura de precisión para cultivo de tomates en invernadero.

DATOS ACTUALES DEL INVERNADERO:
- Temperatura promedio: {temp_avg:.1f}°C
- Humedad promedio: {humidity_avg:.1f}%
- CO2 promedio: {co2_avg:.0f} ppm
- Luz PAR promedio: {light_avg:.0f}

RANGOS ÓPTIMOS PARA TOMATE:
- Temperatura: 18-28°C (ideal: 22-24°C)
- Humedad: 60-80% (ideal: 65-70%)
- CO2: 400-800 ppm (ideal: 600-700 ppm)
- Luz PAR: 100-300 (ideal: 200-250)

ANOMALÍAS RECIENTES: {len(anomalies)} detectadas en las últimas mediciones

SOLICITUD:
Genera un análisis estratégico de 200-300 palabras que incluya:

1. DIAGNÓSTICO: Estado actual del microclima vs condiciones óptimas
2. PRONÓSTICO: Impacto esperado en el crecimiento y rendimiento de tomates
3. RECOMENDACIONES ESPECÍFICAS:
   - Ajustes inmediatos (próximas 24h)
   - Estrategias a mediano plazo (1-2 semanas)
   - Optimizaciones estacionales

4. ALERTAS PREVENTIVAS: Riesgos a monitorear

Enfócate en maximizar la productividad y calidad de los tomates. Usa lenguaje técnico pero comprensible para productores agrícolas.
"""
        return prompt

    def extract_prediction_insights(self, data):
        """Extrae insights predictivos de los datos"""
        features = data.get('features', {})

        # Análisis básico de tendencias
        insights = []

        temp = features.get('Tair_mean', 0)
        if temp > 28:
            insights.append("Riesgo de estrés térmico - puede reducir cuajado de frutos")
        elif temp < 18:
            insights.append("Temperatura subóptima - crecimiento lento esperado")

        humidity = features.get('Rhair_mean', 0)
        if humidity > 85:
            insights.append("Alta humedad - riesgo de enfermedades fúngicas")
        elif humidity < 50:
            insights.append("Baja humedad - estrés hídrico y mala polinización")

        return insights

    def extract_priority_actions(self, analysis_text):
        """Extrae acciones prioritarias del análisis"""
        # Buscar palabras clave que indiquen acciones prioritarias
        priority_keywords = [
            "inmediato", "urgente", "crítico", "ajustar", "reducir", "aumentar",
            "activar", "desactivar", "revisar", "monitorear"
        ]

        sentences = analysis_text.split('.')
        priority_actions = []

        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in priority_keywords):
                priority_actions.append(sentence.strip())

        return priority_actions[:3]  # Top 3 acciones

    def assess_risks(self, data):
        """Evalúa riesgos basado en datos actuales"""
        features = data.get('features', {})
        anomalies = data.get('recent_anomalies', [])

        risk_level = "LOW"
        risk_factors = []

        # Evaluar temperatura
        temp = features.get('Tair_mean', 0)
        if temp > 30 or temp < 15:
            risk_level = "HIGH"
            risk_factors.append("Temperatura extrema")
        elif temp > 28 or temp < 18:
            risk_level = "MEDIUM" if risk_level == "LOW" else risk_level
            risk_factors.append("Temperatura subóptima")

        # Evaluar anomalías recientes
        if len(anomalies) > 3:
            risk_level = "HIGH"
            risk_factors.append("Múltiples anomalías detectadas")
        elif len(anomalies) > 1:
            risk_level = "MEDIUM" if risk_level == "LOW" else risk_level
            risk_factors.append("Anomalías ocasionales")

        return {
            "level": risk_level,
            "factors": risk_factors,
            "score": len(risk_factors) * 10
        }

    def calculate_confidence(self, data):
        """Calcula nivel de confianza en las recomendaciones"""
        features = data.get('features', {})

        # Verificar completitud de datos
        required_fields = ['Tair_mean', 'Rhair_mean', 'CO2air_mean']
        available_data = sum(1 for field in required_fields if features.get(field, 0) > 0)

        base_confidence = (available_data / len(required_fields)) * 100

        # Ajustar por anomalías
        anomalies = len(data.get('recent_anomalies', []))
        if anomalies > 2:
            base_confidence *= 0.8  # Reducir confianza si hay muchas anomalías

        return min(95, max(50, base_confidence))  # Entre 50% y 95%

    def process_prediction(self, prediction_data):
        """Procesa datos de predicción del modelo externo"""
        prediction_id = f"{prediction_data.get('timestamp', time.time())}"

        if prediction_id not in self.processed_predictions:
            self.processed_predictions.add(prediction_id)

            # Integrar con análisis propio
            enhanced_analysis = {
                "external_prediction": prediction_data,
                "internal_analysis": self.analyze_current_conditions(),
                "timestamp": datetime.now().isoformat(),
                "agent": "predictive_integration"
            }

            self.mqtt_client.publish(MQTT_TOPIC_RECOMMENDATIONS, json.dumps(enhanced_analysis))

    def query_ollama(self, prompt):
        """Consulta el modelo SLM local"""
        try:
            payload = {
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.8,
                    "max_tokens": 500,
                    "top_p": 0.9
                }
            }

            response = requests.post(OLLAMA_URL, json=payload, timeout=60)
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "Error generando análisis").strip()
            else:
                return "Análisis no disponible temporalmente"

        except Exception as e:
            print(f"[Predictive Agent] Error consultando Ollama: {e}")
            return "Error en análisis predictivo - revisar condiciones manualmente"

    def start(self):
        """Inicia el agente"""
        print("[Predictive Agent] Iniciando agente de recomendaciones inteligentes...")
        self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        self.mqtt_client.loop_forever()

if __name__ == "__main__":
    agent = PredictiveAgent()
    agent.start()