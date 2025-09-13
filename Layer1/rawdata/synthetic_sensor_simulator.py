#!/usr/bin/env python3
"""
Simulador de Sensores Sintéticos - Layer 1
Genera datos sintéticos realistas de invernadero basados en patrones del dataset original
pero con variaciones naturales y ciclos diurnos/nocturnos
"""

import paho.mqtt.client as mqtt
import pandas as pd
import json
import time
import os
import random
import numpy as np
from datetime import datetime, timedelta

# --- Configuración ---
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_RAW = "invernadero/sensores/raw"
ORIGINAL_CSV_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'GreenhouseClimate.csv')
SIMULATION_SPEED_SECONDS = 0.5  # Velocidad de simulación

# --- Lógica de Anomalías ---
MIN_ANOMALY_INTERVAL = 30
MAX_ANOMALY_INTERVAL = 100

class GreenhouseSyntheticSimulator:
    def __init__(self):
        # Cargar dataset original solo para extraer rangos y patrones
        self.learn_patterns()

        # Variables de estado del invernadero
        self.current_time = datetime.now()
        self.base_conditions = {
            "Tair": 23.0,      # Temperatura base
            "Rhair": 70.0,     # Humedad base
            "CO2air": 600.0,   # CO2 base
            "AssimLight": 150.0, # Luz base
            "Tot_PAR": 200.0,
            "HumDef": 4.0,
            "EnScr": 50.0,
            "BlackScr": 50.0,
            "VentLee": 10.0,
            "Ventwind": 5.0,
            "PipeGrow": 25.0,
            "PipeLow": 20.0
        }

        # Patrones circadianos (24 horas)
        self.circadian_patterns = {
            "Tair": {"amplitude": 6.0, "offset": 0},      # ±6°C variación diaria
            "Rhair": {"amplitude": 15.0, "offset": 12},   # ±15% humedad, pico al mediodía
            "CO2air": {"amplitude": 150.0, "offset": 6},  # ±150ppm, mínimo en la mañana
            "AssimLight": {"amplitude": 150.0, "offset": 0}, # ±150 luz, pico al mediodía
            "Tot_PAR": {"amplitude": 100.0, "offset": 0}
        }

        # Configurar MQTT
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client.on_connect = self.on_connect

        # Control de anomalías
        self.next_anomaly_count = random.randint(MIN_ANOMALY_INTERVAL, MAX_ANOMALY_INTERVAL)
        self.message_count = 0

    def learn_patterns(self):
        """Aprende patrones del dataset original para generar datos realistas"""
        try:
            df = pd.read_csv(ORIGINAL_CSV_PATH, low_memory=False)
            df.columns = [c.strip() for c in df.columns]
            if "%time" in df.columns:
                df = df.rename(columns={"%time": "time"})

            # Extraer estadísticas para cada variable
            self.variable_stats = {}
            numeric_cols = ["Tair", "Rhair", "CO2air", "AssimLight", "Tot_PAR", "HumDef",
                          "EnScr", "BlackScr", "VentLee", "Ventwind", "PipeGrow", "PipeLow"]

            for col in numeric_cols:
                if col in df.columns:
                    values = pd.to_numeric(df[col], errors='coerce').dropna()
                    self.variable_stats[col] = {
                        "min": values.min(),
                        "max": values.max(),
                        "mean": values.mean(),
                        "std": values.std()
                    }

            print("[Synthetic Simulator] Patrones aprendidos del dataset original")

        except Exception as e:
            print(f"[Synthetic Simulator] Error leyendo dataset original: {e}")
            # Usar valores por defecto si no se puede leer el dataset
            self.variable_stats = {}

    def on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            print("Simulador sintético conectado al Broker MQTT!")
        else:
            print(f"Fallo al conectar, código: {rc}")

    def get_time_factor(self, hour):
        """Calcula factor basado en la hora del día (0-23)"""
        # Convertir hora a radianes para función sinusoidal
        return np.sin(2 * np.pi * (hour - 6) / 24)  # Pico al mediodía (12h)

    def generate_realistic_value(self, variable, base_value, hour):
        """Genera valor realista para una variable considerando patrones circadianos"""

        # Factor de tiempo (ciclo diurno/nocturno)
        time_factor = self.get_time_factor(hour)

        # Obtener patrón circadiano si existe
        if variable in self.circadian_patterns:
            pattern = self.circadian_patterns[variable]
            circadian_variation = pattern["amplitude"] * np.sin(2 * np.pi * (hour + pattern["offset"]) / 24)
        else:
            circadian_variation = 0

        # Ruido aleatorio pequeño para variabilidad natural
        noise = np.random.normal(0, base_value * 0.02)  # 2% de ruido

        # Calcular valor final
        value = base_value + circadian_variation + noise

        # Aplicar límites realistas basados en estadísticas del dataset
        if variable in self.variable_stats:
            stats = self.variable_stats[variable]
            value = np.clip(value, stats["min"] * 0.8, stats["max"] * 1.2)

        return round(value, 2)

    def generate_synthetic_row(self):
        """Genera una fila completa de datos sintéticos"""
        current_hour = self.current_time.hour + self.current_time.minute / 60.0

        # Generar valores principales con patrones circadianos
        synthetic_data = {}

        # Variables principales del invernadero
        synthetic_data["Tair"] = self.generate_realistic_value("Tair", self.base_conditions["Tair"], current_hour)
        synthetic_data["Rhair"] = self.generate_realistic_value("Rhair", self.base_conditions["Rhair"], current_hour)
        synthetic_data["CO2air"] = self.generate_realistic_value("CO2air", self.base_conditions["CO2air"], current_hour)
        synthetic_data["AssimLight"] = max(0, self.generate_realistic_value("AssimLight", self.base_conditions["AssimLight"], current_hour))
        synthetic_data["Tot_PAR"] = max(0, self.generate_realistic_value("Tot_PAR", self.base_conditions["Tot_PAR"], current_hour))

        # Variables de control del invernadero
        synthetic_data["HumDef"] = abs(self.generate_realistic_value("HumDef", self.base_conditions["HumDef"], current_hour))
        synthetic_data["EnScr"] = np.clip(self.generate_realistic_value("EnScr", self.base_conditions["EnScr"], current_hour), 0, 100)
        synthetic_data["BlackScr"] = np.clip(self.generate_realistic_value("BlackScr", self.base_conditions["BlackScr"], current_hour), 0, 100)
        synthetic_data["VentLee"] = max(0, self.generate_realistic_value("VentLee", self.base_conditions["VentLee"], current_hour))
        synthetic_data["Ventwind"] = max(0, self.generate_realistic_value("Ventwind", self.base_conditions["Ventwind"], current_hour))

        # Variables de calefacción
        synthetic_data["PipeGrow"] = max(0, self.generate_realistic_value("PipeGrow", self.base_conditions["PipeGrow"], current_hour))
        synthetic_data["PipeLow"] = max(0, self.generate_realistic_value("PipeLow", self.base_conditions["PipeLow"], current_hour))

        # Variables adicionales con valores más estáticos
        synthetic_data["Cum_irr"] = round(1.0 + random.uniform(0, 0.5), 1)
        synthetic_data["EC_drain_PC"] = round(6.0 + random.uniform(0.2, 0.6), 1)
        synthetic_data["pH_drain_PC"] = round(6.3 + random.uniform(0.1, 0.4), 1)
        synthetic_data["water_sup"] = random.randint(10, 20)

        # Tiempo actual
        synthetic_data["time"] = self.current_time.strftime("%m/%d/%y %H:%M")

        # Variables de setpoint (valores objetivo)
        synthetic_data.update({
            "assim_sp": 100, "assim_vip": 100,
            "co2_sp": 600, "co2_vip": 600,
            "co2_dos": round(random.uniform(0.001, 0.005), 4),
            "dx_sp": 2.2, "dx_vip": 2.2,
            "t_heat_sp": round(synthetic_data["Tair"] - random.uniform(1, 3), 1),
            "t_heat_vip": round(synthetic_data["Tair"] - random.uniform(1, 3), 1),
            "t_vent_sp": round(synthetic_data["Tair"] + random.uniform(2, 4), 1),
            "t_ventlee_vip": round(synthetic_data["Tair"] + random.uniform(2, 4), 1),
            "t_ventwind_vip": round(synthetic_data["Tair"] + random.uniform(3, 5), 1),
            "window_pos_lee_sp": 0, "window_pos_lee_vip": 0,
            "water_sup_intervals_sp_min": 120, "water_sup_intervals_vip_min": 120
        })

        # Variables adicionales con valores por defecto
        for var in ["int_blue_sp", "int_blue_vip", "int_farred_sp", "int_farred_vip",
                   "int_red_sp", "int_red_vip", "int_white_sp", "int_white_vip"]:
            synthetic_data[var] = 1000

        for var in ["scr_blck_sp", "scr_blck_vip"]:
            synthetic_data[var] = 96

        for var in ["scr_enrg_sp", "scr_enrg_vip"]:
            synthetic_data[var] = random.randint(90, 100)

        # Variables con NaN por defecto
        for var in ["t_grow_min_sp", "t_grow_min_vip", "t_rail_min_sp", "t_rail_min_vip"]:
            synthetic_data[var] = np.nan

        # Lamps siempre igual a Tot_PAR para simplificar
        synthetic_data["Tot_PAR_Lamps"] = synthetic_data["Tot_PAR"]

        return synthetic_data

    def inject_anomaly(self, data):
        """Inyecta una anomalía realista en los datos"""
        data_copy = data.copy()

        # Variables que pueden tener anomalías
        anomaly_candidates = ["Tair", "Rhair", "CO2air", "AssimLight", "Tot_PAR",
                             "VentLee", "Ventwind", "EnScr", "BlackScr"]

        # Seleccionar variable para anomalía
        anomaly_var = random.choice(anomaly_candidates)
        original_value = data_copy[anomaly_var]

        # Tipos de anomalías realistas
        anomaly_types = {
            "Tair": [("spike_high", lambda x: x * random.uniform(1.4, 1.8)),
                     ("spike_low", lambda x: x * random.uniform(0.3, 0.6))],
            "Rhair": [("spike_high", lambda x: min(100, x * random.uniform(1.3, 1.5))),
                      ("spike_low", lambda x: x * random.uniform(0.4, 0.7))],
            "CO2air": [("depletion", lambda x: x * random.uniform(0.2, 0.5)),
                       ("excess", lambda x: x * random.uniform(1.8, 2.5))],
            "AssimLight": [("failure", lambda x: x * random.uniform(0.1, 0.3)),
                           ("overexposure", lambda x: x * random.uniform(2.0, 3.0))],
            "VentLee": [("stuck_open", lambda x: x * random.uniform(3.0, 5.0)),
                        ("stuck_closed", lambda x: x * random.uniform(0.1, 0.3))]
        }

        if anomaly_var in anomaly_types:
            anomaly_type, transform = random.choice(anomaly_types[anomaly_var])
            data_copy[anomaly_var] = round(transform(original_value), 2)
        else:
            # Anomalía genérica
            data_copy[anomaly_var] = round(original_value * random.uniform(2.0, 4.0), 2)
            anomaly_type = "generic_spike"

        print(f"*** ANOMALÍA INYECTADA: {anomaly_var} = {data_copy[anomaly_var]} (fue {original_value}) - Tipo: {anomaly_type} ***")
        return data_copy

    def simulate(self):
        """Ejecuta la simulación principal"""
        try:
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        except Exception as e:
            print(f"Error al conectar: {e}")
            return

        self.mqtt_client.loop_start()
        print(f"Iniciando simulación sintética. Anomalías cada {MIN_ANOMALY_INTERVAL}-{MAX_ANOMALY_INTERVAL} mensajes.")
        print("Presiona CTRL+C para detener.")

        try:
            while True:
                # Generar datos sintéticos
                synthetic_row = self.generate_synthetic_row()

                # Verificar si inyectar anomalía
                if self.message_count >= self.next_anomaly_count:
                    synthetic_row = self.inject_anomaly(synthetic_row)
                    # Programar siguiente anomalía
                    offset = random.randint(MIN_ANOMALY_INTERVAL, MAX_ANOMALY_INTERVAL)
                    self.next_anomaly_count = self.message_count + offset
                    print(f"Próxima anomalía programada para mensaje: {self.next_anomaly_count}")

                # Publicar datos
                payload = json.dumps(synthetic_row)
                self.mqtt_client.publish(MQTT_TOPIC_RAW, payload)

                self.message_count += 1

                # Avanzar tiempo simulado (5 minutos por iteración)
                self.current_time += timedelta(minutes=5)

                # Log cada 20 mensajes
                if self.message_count % 20 == 0:
                    print(f"[Msg {self.message_count}] T:{synthetic_row['Tair']}°C, H:{synthetic_row['Rhair']}%, CO2:{synthetic_row['CO2air']}ppm")

                time.sleep(SIMULATION_SPEED_SECONDS)

        except KeyboardInterrupt:
            print("\nSimulación detenida por el usuario.")
        finally:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            print("Cliente MQTT desconectado.")

def main():
    simulator = GreenhouseSyntheticSimulator()
    simulator.simulate()

if __name__ == "__main__":
    main()