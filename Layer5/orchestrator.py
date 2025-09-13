#!/usr/bin/env python3
"""
Orquestador de Agentes - Layer 5
Gestiona y coordina los agentes SLM (tinyllama + deepseek-r1)
"""

import subprocess
import time
import signal
import sys
import os
from datetime import datetime

class AgentOrchestrator:
    def __init__(self):
        self.agents = {
            'anomaly_alert': {
                'script': 'agents/anomaly_alert_agent.py',
                'process': None,
                'description': 'Agente de Alertas Emergentes (tinyllama:1.1b)',
                'enabled': True
            },
            'predictive': {
                'script': 'agents/predictive_agent.py',
                'process': None,
                'description': 'Agente de Recomendaciones Inteligentes (deepseek-r1:8b)',
                'enabled': True
            }
        }

        # Configurar manejo de señales para cierre limpio
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def log(self, message):
        """Log con timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [Orchestrator] {message}")

    def check_dependencies(self):
        """Verifica dependencias necesarias"""
        self.log("Verificando dependencias...")

        # Verificar Ollama
        try:
            result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
            if result.returncode == 0:
                self.log("✅ Ollama disponible")

                # Verificar modelos necesarios
                models = result.stdout
                if 'tinyllama:1.1b' in models:
                    self.log("✅ tinyllama:1.1b disponible")
                else:
                    self.log("❌ tinyllama:1.1b no encontrado")
                    self.log("Ejecuta: ollama pull tinyllama:1.1b")

                if 'deepseek-r1:8b' in models:
                    self.log("✅ deepseek-r1:8b disponible")
                else:
                    self.log("❌ deepseek-r1:8b no encontrado")
                    self.log("Ejecuta: ollama pull deepseek-r1:8b")
            else:
                self.log("❌ Ollama no disponible")
                return False

        except FileNotFoundError:
            self.log("❌ Ollama no instalado")
            return False

        # Verificar broker MQTT (opcional - puede estar en otro lugar)
        self.log("📡 MQTT Broker esperado en localhost:1883")

        return True

    def start_agent(self, agent_name):
        """Inicia un agente específico"""
        agent = self.agents[agent_name]

        if not agent['enabled']:
            self.log(f"⏸️  Agente {agent_name} deshabilitado")
            return False

        if agent['process'] is not None:
            self.log(f"⚠️  Agente {agent_name} ya está ejecutándose")
            return False

        try:
            script_path = os.path.join(os.path.dirname(__file__), agent['script'])
            if not os.path.exists(script_path):
                self.log(f"❌ Script no encontrado: {script_path}")
                return False

            self.log(f"🚀 Iniciando {agent['description']}")

            # Iniciar proceso
            process = subprocess.Popen(
                ['python3', script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            agent['process'] = process
            self.log(f"✅ {agent_name} iniciado (PID: {process.pid})")
            return True

        except Exception as e:
            self.log(f"❌ Error iniciando {agent_name}: {e}")
            return False

    def stop_agent(self, agent_name):
        """Detiene un agente específico"""
        agent = self.agents[agent_name]

        if agent['process'] is None:
            self.log(f"⚠️  Agente {agent_name} no está ejecutándose")
            return

        try:
            process = agent['process']
            self.log(f"🛑 Deteniendo {agent_name} (PID: {process.pid})")

            # Intentar cierre graceful
            process.terminate()

            # Esperar hasta 5 segundos
            try:
                process.wait(timeout=5)
                self.log(f"✅ {agent_name} detenido correctamente")
            except subprocess.TimeoutExpired:
                self.log(f"⚠️  {agent_name} no respondió, forzando cierre...")
                process.kill()
                process.wait()
                self.log(f"✅ {agent_name} terminado forzadamente")

            agent['process'] = None

        except Exception as e:
            self.log(f"❌ Error deteniendo {agent_name}: {e}")

    def start_all_agents(self):
        """Inicia todos los agentes habilitados"""
        self.log("🚀 Iniciando todos los agentes...")

        success_count = 0
        for agent_name in self.agents:
            if self.start_agent(agent_name):
                success_count += 1
                # Pequeña pausa entre inicios
                time.sleep(2)

        self.log(f"✅ {success_count}/{len(self.agents)} agentes iniciados")
        return success_count > 0

    def stop_all_agents(self):
        """Detiene todos los agentes"""
        self.log("🛑 Deteniendo todos los agentes...")

        for agent_name in self.agents:
            self.stop_agent(agent_name)

        self.log("✅ Todos los agentes detenidos")

    def check_agent_health(self, agent_name):
        """Verifica el estado de un agente"""
        agent = self.agents[agent_name]

        if agent['process'] is None:
            return 'stopped'

        # Verificar si el proceso sigue ejecutándose
        poll = agent['process'].poll()
        if poll is None:
            return 'running'
        else:
            # Proceso terminado
            agent['process'] = None
            return 'crashed'

    def monitor_agents(self):
        """Monitorea el estado de los agentes"""
        self.log("🔍 Iniciando monitoreo de agentes...")

        while True:
            try:
                status_report = []

                for agent_name, agent in self.agents.items():
                    health = self.check_agent_health(agent_name)
                    status_report.append(f"{agent_name}: {health}")

                    # Reiniciar agentes que crashed (opcional)
                    if health == 'crashed' and agent['enabled']:
                        self.log(f"⚠️  {agent_name} crasheó, reiniciando...")
                        time.sleep(1)
                        self.start_agent(agent_name)

                # Log de estado cada 30 segundos
                if len(status_report) > 0:
                    self.log(f"Estado: {' | '.join(status_report)}")

                time.sleep(30)

            except KeyboardInterrupt:
                break
            except Exception as e:
                self.log(f"❌ Error en monitoreo: {e}")
                time.sleep(5)

    def signal_handler(self, signum, frame):
        """Maneja señales de cierre"""
        self.log(f"🛑 Señal recibida ({signum}), cerrando agentes...")
        self.stop_all_agents()
        sys.exit(0)

    def print_status(self):
        """Imprime el estado actual de todos los agentes"""
        print("\n" + "="*60)
        print("🤖 LAYER 5 - ORCHESTRATOR STATUS")
        print("="*60)

        for agent_name, agent in self.agents.items():
            health = self.check_agent_health(agent_name)
            status_icon = {
                'running': '🟢',
                'stopped': '🔴',
                'crashed': '🟡'
            }.get(health, '❓')

            enabled_status = "✅" if agent['enabled'] else "⏸️"
            pid = agent['process'].pid if agent['process'] else "N/A"

            print(f"{status_icon} {agent_name.upper()}")
            print(f"   Descripción: {agent['description']}")
            print(f"   Estado: {health.upper()}")
            print(f"   PID: {pid}")
            print(f"   Habilitado: {enabled_status}")
            print()

    def interactive_menu(self):
        """Menú interactivo para control de agentes"""
        while True:
            print("\n" + "="*50)
            print("🤖 LAYER 5 - CONTROL DE AGENTES")
            print("="*50)
            print("1. Iniciar todos los agentes")
            print("2. Detener todos los agentes")
            print("3. Ver estado de agentes")
            print("4. Iniciar agente específico")
            print("5. Detener agente específico")
            print("6. Iniciar monitoreo automático")
            print("7. Verificar dependencias")
            print("0. Salir")
            print("-"*50)

            try:
                choice = input("Selecciona una opción: ").strip()

                if choice == '1':
                    self.start_all_agents()
                elif choice == '2':
                    self.stop_all_agents()
                elif choice == '3':
                    self.print_status()
                elif choice == '4':
                    print("\nAgentes disponibles:")
                    for i, name in enumerate(self.agents.keys(), 1):
                        print(f"{i}. {name}")
                    try:
                        idx = int(input("Selecciona agente: ")) - 1
                        agent_name = list(self.agents.keys())[idx]
                        self.start_agent(agent_name)
                    except (ValueError, IndexError):
                        print("❌ Selección inválida")
                elif choice == '5':
                    print("\nAgentes disponibles:")
                    for i, name in enumerate(self.agents.keys(), 1):
                        print(f"{i}. {name}")
                    try:
                        idx = int(input("Selecciona agente: ")) - 1
                        agent_name = list(self.agents.keys())[idx]
                        self.stop_agent(agent_name)
                    except (ValueError, IndexError):
                        print("❌ Selección inválida")
                elif choice == '6':
                    print("🔍 Iniciando monitoreo continuo (Ctrl+C para detener)...")
                    self.monitor_agents()
                elif choice == '7':
                    self.check_dependencies()
                elif choice == '0':
                    self.stop_all_agents()
                    print("👋 ¡Hasta luego!")
                    break
                else:
                    print("❌ Opción inválida")

            except KeyboardInterrupt:
                print("\n🛑 Proceso interrumpido")
                self.stop_all_agents()
                break
            except Exception as e:
                print(f"❌ Error: {e}")

def main():
    """Función principal"""
    orchestrator = AgentOrchestrator()

    # Verificar dependencias al inicio
    if not orchestrator.check_dependencies():
        print("❌ Dependencias no satisfechas")
        sys.exit(1)

    # Si se pasa argumento, ejecutar comando directo
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == 'start':
            orchestrator.start_all_agents()
            orchestrator.monitor_agents()
        elif command == 'stop':
            orchestrator.stop_all_agents()
        elif command == 'status':
            orchestrator.print_status()
        elif command == 'monitor':
            orchestrator.monitor_agents()
        else:
            print(f"❌ Comando desconocido: {command}")
            print("Comandos disponibles: start, stop, status, monitor")
    else:
        # Modo interactivo
        orchestrator.interactive_menu()

if __name__ == "__main__":
    main()