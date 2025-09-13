#!/usr/bin/env python3
"""
Simulador de Cosechas v5 - Re-sampling Inteligente
Layer 1

NUEVA ESTRATEGIA:
- Usa el dataset original GreenhouseClimate.csv con datos reales del invernadero
- Hace re-sampling inteligente para crear múltiples cosechas simuladas
- Cada cosecha progresa de ~45 días a ~0 días de forma realista
- Intervalos de 12 horas como requiere el modelo predictivo
"""

import paho.mqtt.client as mqtt
import pandas as pd
import json
import time
import os
import numpy as np
from datetime import datetime, timedelta
import random

# --- Configuración ---
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_MODEL_DATA = "invernadero/model/data_12h"

# Dataset original del invernadero con datos reales
GREENHOUSE_DATA_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'GreenhouseClimate.csv')

SIMULATION_SPEED_SECONDS = 2.0

# Configuración de las cosechas simuladas
NUM_COSECHAS = 3  # Número de cosechas a simular
DIAS_POR_COSECHA = 45  # Días desde inicio hasta cosecha
PERIODOS_12H_POR_COSECHA = DIAS_POR_COSECHA * 2  # 90 períodos de 12h por cosecha

class GreenhouseSimulator:
    def __init__(self):
        self.simulation_index = 0
        self.cosechas_dataset = None
        self.current_cosecha = 0
        self.create_simulated_harvests()

        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client.on_connect = self.on_connect

        print("🌱 Simulador v5 (Re-sampling Inteligente) inicializado")
        print(f"   Dataset: {os.path.basename(GREENHOUSE_DATA_PATH)}")
        print(f"   Cosechas simuladas: {NUM_COSECHAS}")
        print(f"   Frecuencia: {SIMULATION_SPEED_SECONDS}s por período")

    def create_simulated_harvests(self):
        """
        Crea múltiples cosechas simuladas basadas en re-sampling del dataset original
        """
        try:
            print("🔄 Cargando dataset original del invernadero...")
            
            # 1. CARGAR DATASET ORIGINAL
            df_original = pd.read_csv(GREENHOUSE_DATA_PATH, low_memory=False)
            
            # Limpiar nombres de columnas
            df_original.columns = [col.strip() for col in df_original.columns]
            if "%time" in df_original.columns:
                df_original = df_original.rename(columns={"%time": "time"})
            
            # 2. SELECCIONAR SOLO VARIABLES QUE NECESITA EL MODELO
            required_columns = ['CO2air', 'Cum_irr', 'EC_drain_PC', 'HumDef',
                               'PipeGrow', 'PipeLow', 'Rhair', 'Tair', 'Tot_PAR', 'pH_drain_PC']
            
            # Verificar que todas las columnas existen
            missing_cols = [col for col in required_columns if col not in df_original.columns]
            if missing_cols:
                print(f"❌ Columnas faltantes: {missing_cols}")
                print(f"   Columnas disponibles: {list(df_original.columns)}")
                exit()
            
            # 3. LIMPIAR Y PREPARAR DATOS BASE
            df_base = df_original[required_columns].copy()
            for col in required_columns:
                df_base[col] = pd.to_numeric(df_base[col], errors='coerce')
            
            # Eliminar filas con NaN
            df_base = df_base.dropna()
            print(f"✅ Datos base preparados: {len(df_base)} registros limpios")
            
            # 4. CREAR MÚLTIPLES COSECHAS POR RE-SAMPLING
            all_harvests = []
            
            for cosecha_id in range(NUM_COSECHAS):
                print(f"   🌾 Creando cosecha #{cosecha_id}...")
                
                # Re-sampling: tomar muestras aleatorias del dataset original
                sample_indices = np.random.choice(len(df_base), size=PERIODOS_12H_POR_COSECHA, replace=True)
                cosecha_data = df_base.iloc[sample_indices].copy().reset_index(drop=True)
                
                # Añadir información de cosecha
                cosecha_data['cosecha'] = cosecha_id
                
                # Crear progresión temporal realista: 45 días -> 0 días
                tiempo_final_values = np.linspace(45.0, 0.5, PERIODOS_12H_POR_COSECHA)
                cosecha_data['tiempo_final'] = tiempo_final_values
                
                # Timestamps simulados (cada 12h)
                start_date = datetime(2024, 1, 1) + timedelta(days=cosecha_id * 50)  # Separar cosechas
                timestamps = [start_date + timedelta(hours=12*i) for i in range(PERIODOS_12H_POR_COSECHA)]
                cosecha_data['__time__'] = timestamps
                
                # Añadir variabilidad estacional sutil a los datos
                cosecha_data = self.add_seasonal_variation(cosecha_data, cosecha_id)
                
                all_harvests.append(cosecha_data)
            
            # 5. COMBINAR TODAS LAS COSECHAS
            self.cosechas_dataset = pd.concat(all_harvests, ignore_index=True)
            
            # 6. RENOMBRAR COLUMNAS COMO ESPERA EL MODELO
            self.cosechas_dataset.rename(columns={
                'CO2air': 'CO2air__mean', 'Cum_irr': 'Cum_irr__mean', 'EC_drain_PC': 'EC_drain_PC__mean',
                'HumDef': 'HumDef__mean', 'PipeGrow': 'PipeGrow__mean', 'PipeLow': 'PipeLow__mean',
                'Rhair': 'Rhair__mean', 'Tair': 'Tair__mean', 'Tot_PAR': 'Tot_PAR__mean',
                'pH_drain_PC': 'pH_drain_PC__mean'
            }, inplace=True)
            
            # 7. IDENTIFICAR COLUMNAS NUMÉRICAS
            self.numeric_cols = ['CO2air__mean', 'Cum_irr__mean', 'EC_drain_PC__mean', 'HumDef__mean',
                                'PipeGrow__mean', 'PipeLow__mean', 'Rhair__mean', 'Tair__mean',
                                'Tot_PAR__mean', 'pH_drain_PC__mean', 'tiempo_final']
            
            print(f"✅ {NUM_COSECHAS} cosechas simuladas creadas exitosamente!")
            print(f"   Total de períodos: {len(self.cosechas_dataset)}")
            print(f"   Rango tiempo_final: {self.cosechas_dataset['tiempo_final'].min():.1f} - {self.cosechas_dataset['tiempo_final'].max():.1f} días")
            
        except Exception as e:
            print(f"CRITICAL: Error creando cosechas simuladas. {e}")
            import traceback
            traceback.print_exc()
            exit()
    
    def add_seasonal_variation(self, cosecha_data, cosecha_id):
        """
        Añade variación estacional sutil para hacer cada cosecha única
        """
        # Factores estacionales diferentes por cosecha
        seasonal_factors = {
            'CO2air__mean': 1.0 + (cosecha_id * 0.02),  # 2% por cosecha
            'Tair__mean': 1.0 + (cosecha_id * 0.01),    # 1% por cosecha  
            'Rhair__mean': 1.0 + (np.sin(cosecha_id) * 0.05),  # Variación sinusoidal
            'Tot_PAR__mean': 1.0 + (cosecha_id * 0.015)  # 1.5% por cosecha
        }
        
        for col, factor in seasonal_factors.items():
            if col.replace('__mean', '') in cosecha_data.columns:
                original_col = col.replace('__mean', '')
                cosecha_data[original_col] *= factor
        
        return cosecha_data

    def on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            print("🔗 Simulador v5 conectado al Broker MQTT!")
        else:
            print(f"❌ Fallo al conectar, código: {rc}")

    def simulate(self):
        """
        Ejecuta la simulación de cosechas con progresión temporal realista
        """
        try:
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        except Exception as e:
            print(f"❌ Error al conectar: {e}")
            return

        self.mqtt_client.loop_start()
        print(f"\n🚀 Iniciando simulación de {NUM_COSECHAS} cosechas...")
        print(f"   Total períodos: {len(self.cosechas_dataset)}")
        print("   Presiona CTRL+C para detener.\n")

        try:
            while True:
                # Obtener el período actual
                row = self.cosechas_dataset.iloc[self.simulation_index]
                payload = row.to_dict()

                # CONVERSIÓN A TIPOS CORRECTOS
                for col in self.numeric_cols:
                    if col in payload and pd.notna(payload[col]):
                        payload[col] = float(payload[col])

                # AÑADIR RUIDO SUTIL A DATOS PRINCIPALES (EXCEPTO tiempo_final)
                main_numeric_cols = [col for col in self.numeric_cols if col != 'tiempo_final']
                for col in main_numeric_cols:
                    if col in payload and pd.notna(payload[col]):
                        base_value = payload[col]
                        if abs(base_value) > 0.001:
                            # Ruido muy sutil: 0.3% para mantener realismo
                            noise_magnitude = abs(base_value) * 0.003
                            noise = np.random.normal(0, noise_magnitude)
                            payload[col] += noise

                # ESTANDARIZAR CAMPOS PARA EL MODELO
                if 'cosecha' in payload:
                    payload['harvest_number'] = payload['cosecha']
                
                if 'tiempo_final' in payload:
                    payload['tiempo_final'] = float(payload['tiempo_final'])

                # Timestamp para la simulación
                payload['timestamp'] = datetime.now().isoformat()

                # PUBLICAR AL MODELO PREDICTIVO
                try:
                    message_json = json.dumps(payload, default=str)
                    self.mqtt_client.publish(MQTT_TOPIC_MODEL_DATA, message_json)
                    
                    # LOGS CON PROGRESO DETALLADO
                    cosecha_num = payload.get('cosecha', 'N/A')
                    dias_restantes = payload.get('tiempo_final', 'N/A')
                    temp = payload.get('Tair__mean', 'N/A')
                    co2 = payload.get('CO2air__mean', 'N/A')
                    timestamp = payload.get('__time__', 'N/A')
                    
                    # Calcular progreso dentro de la cosecha actual
                    if isinstance(cosecha_num, (int, float)) and not pd.isna(cosecha_num):
                        cosecha_rows = self.cosechas_dataset[self.cosechas_dataset['cosecha'] == cosecha_num]
                        if len(cosecha_rows) > 0:
                            cosecha_start_idx = cosecha_rows.index[0]
                            progress_within_harvest = self.simulation_index - cosecha_start_idx + 1
                            progress_pct = (progress_within_harvest / PERIODOS_12H_POR_COSECHA) * 100
                            
                            print(f"🌾 Cosecha #{int(cosecha_num)} | "
                                  f"Progreso: {progress_pct:.1f}% ({progress_within_harvest}/{PERIODOS_12H_POR_COSECHA}) | "
                                  f"Días: {dias_restantes:.1f} | "
                                  f"T: {temp:.1f}°C | CO2: {co2:.0f}ppm")
                    
                except Exception as e:
                    print(f"❌ Error al publicar: {e}")
                    continue

                # AVANZAR AL SIGUIENTE PERÍODO
                self.simulation_index = (self.simulation_index + 1) % len(self.cosechas_dataset)
                
                # MENSAJE ESPECIAL AL COMPLETAR UNA COSECHA
                if self.simulation_index % PERIODOS_12H_POR_COSECHA == 0:
                    completed_harvest = self.simulation_index // PERIODOS_12H_POR_COSECHA
                    if completed_harvest < NUM_COSECHAS:
                        print(f"\n✅ ¡Cosecha #{completed_harvest - 1} completada! Iniciando cosecha #{completed_harvest}...\n")

                time.sleep(SIMULATION_SPEED_SECONDS)

        except KeyboardInterrupt:
            print("\n🛑 Simulación detenida por el usuario.")
        except Exception as e:
            print(f"❌ Error en simulación: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            print("🔌 Cliente MQTT desconectado.")

def main():
    simulator = GreenhouseSimulator()
    simulator.simulate()

if __name__ == "__main__":
    main()
