// Dashboard JavaScript - Replica exacta de la imagen
class PrecisionTomatoDashboard {
    constructor() {
        this.socket = io();
        this.chart = null;
        this.tooltipElement = null;
        
        this.initializeComponents();
        this.setupInteractions();
        this.setupSocketListeners();
    }

    initializeComponents() {
        this.createTooltip();
        this.initializeChart();
        this.setupGreenhouseInteractions();
        console.log('🍅 Dashboard inicializado - Replica exacta');
    }

    createTooltip() {
        this.tooltipElement = document.createElement('div');
        this.tooltipElement.className = 'greenhouse-tooltip';
        this.tooltipElement.id = 'greenhouse-tooltip';
        document.body.appendChild(this.tooltipElement);
    }

    setupGreenhouseInteractions() {
        const greenhouses = document.querySelectorAll('.greenhouse-box');
        
        greenhouses.forEach(greenhouse => {
            const id = greenhouse.getAttribute('data-id');
            const days = greenhouse.getAttribute('data-days');
            
            greenhouse.addEventListener('mouseenter', (e) => {
                this.showTooltip(e, id, days);
            });
            
            greenhouse.addEventListener('mouseleave', () => {
                this.hideTooltip();
            });
            
            greenhouse.addEventListener('mousemove', (e) => {
                this.updateTooltipPosition(e);
            });
            
            greenhouse.addEventListener('click', () => {
                this.showGreenhouseDetails(id, days);
            });
        });
    }

    showTooltip(event, id, days) {
        const temperature = (20 + Math.random() * 8).toFixed(1);
        const humidity = (60 + Math.random() * 20).toFixed(1);
        const co2 = Math.round(400 + Math.random() * 200);
        
        this.tooltipElement.innerHTML = `
            <div class="font-semibold">${id}</div>
            <div class="text-xs mt-1">
                Días: ${days}<br>
                Temp: ${temperature}°C<br>
                Humedad: ${humidity}%<br>
                CO2: ${co2} ppm
            </div>
        `;
        
        this.tooltipElement.classList.add('show');
        this.updateTooltipPosition(event);
    }

    updateTooltipPosition(event) {
        const tooltip = this.tooltipElement;
        const rect = tooltip.getBoundingClientRect();
        
        let left = event.clientX + 10;
        let top = event.clientY - rect.height - 10;
        
        // Ajustar si se sale de la pantalla
        if (left + rect.width > window.innerWidth) {
            left = event.clientX - rect.width - 10;
        }
        if (top < 0) {
            top = event.clientY + 10;
        }
        
        tooltip.style.left = left + 'px';
        tooltip.style.top = top + 'px';
    }

    hideTooltip() {
        this.tooltipElement.classList.remove('show');
    }

    showGreenhouseDetails(id, days) {
        const temperature = (20 + Math.random() * 8).toFixed(1);
        const humidity = (60 + Math.random() * 20).toFixed(1);
        const co2 = Math.round(400 + Math.random() * 200);
        const light = Math.round(200 + Math.random() * 400);
        
        const hasAnomaly = Math.random() < 0.2;
        
        const details = `
🏠 Invernadero: ${id}
📅 Días para cosecha: ${days}
🌡️ Temperatura: ${temperature}°C
💧 Humedad: ${humidity}%
🌪️ CO2: ${co2} ppm
☀️ Luz PAR: ${light}
${hasAnomaly ? '⚠️ ANOMALÍA DETECTADA' : '✅ Estado Normal'}

Cultivo: Tomate
Área: ${Math.round(200 + Math.random() * 300)} m²
Estado: ${hasAnomaly ? 'Requiere atención' : 'Óptimo'}
        `;
        
        alert(details.trim());
    }

    initializeChart() {
        const ctx = document.getElementById('progressChart');
        if (!ctx) return;

        // Datos del gráfico basados en la imagen
        this.chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Invernaderos', 'B1', 'Invernaderos', 'B3', 'Invernaderos', 'Invernaderos', 'B6', 'Invernaderos'],
                datasets: [{
                    data: [7, 5, 4, 6, 3, 5, 2, 4],
                    backgroundColor: [
                        '#ef4444', // Rojo
                        '#f59e0b', // Amarillo
                        '#f59e0b', // Amarillo
                        '#22c55e', // Verde
                        '#f59e0b', // Amarillo
                        '#22c55e', // Verde
                        '#f59e0b', // Amarillo
                        '#22c55e'  // Verde
                    ],
                    borderWidth: 0,
                    borderRadius: 4,
                    borderSkipped: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            color: '#9ca3af',
                            font: {
                                size: 10
                            }
                        },
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        beginAtZero: true,
                        max: 8,
                        ticks: {
                            color: '#9ca3af',
                            font: {
                                size: 10
                            },
                            stepSize: 2
                        },
                        grid: {
                            color: 'rgba(156, 163, 175, 0.1)'
                        }
                    }
                },
                elements: {
                    bar: {
                        backgroundColor: function(context) {
                            return context.dataset.backgroundColor[context.dataIndex];
                        }
                    }
                }
            }
        });
    }

    setupInteractions() {
        // Actualizar datos cada 30 segundos
        setInterval(() => {
            this.updateData();
        }, 30000);

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'r' || e.key === 'R') {
                location.reload();
            }
            if (e.key === 'Escape') {
                this.hideTooltip();
            }
        });

        // Resize handler
        window.addEventListener('resize', () => {
            if (this.chart) {
                this.chart.resize();
            }
        });
    }

    updateData() {
        // Simular pequeños cambios en los datos
        console.log('📊 Actualizando datos simulados...');
        
        // Aquí se integrarían los datos reales del pipeline MQTT
        this.simulateDataChanges();
    }

    simulateDataChanges() {
        // Simular cambios en algunos invernaderos
        const greenhouses = document.querySelectorAll('.greenhouse-box');
        greenhouses.forEach(greenhouse => {
            const currentDays = parseInt(greenhouse.getAttribute('data-days'));
            
            // Pequeña probabilidad de cambio
            if (Math.random() < 0.1) {
                const newDays = Math.max(1, currentDays + (Math.random() < 0.5 ? -1 : 0));
                greenhouse.setAttribute('data-days', newDays);
                const daysElement = greenhouse.querySelector('.greenhouse-days');
                if (daysElement) {
                    daysElement.textContent = newDays;
                }
            }
        });
    }

    setupSocketListeners() {
        this.socket.on('connect', () => {
            console.log('🔗 Conectado al servidor dashboard');
        });

        this.socket.on('disconnect', () => {
            console.log('❌ Desconectado del servidor dashboard');
        });

        this.socket.on('dataUpdate', (update) => {
            this.handleRealDataUpdate(update);
        });

        this.socket.on('newAlert', (alert) => {
            this.displayRealAlert(alert);
        });
    }

    handleRealDataUpdate(update) {
        console.log('📡 Actualización de datos real:', update.topic);
        
        // Integrar datos reales del pipeline MQTT
        switch (update.topic) {
            case 'invernadero/sensores/raw':
                this.updateSensorData(update.data);
                break;
            case 'invernadero/anomalias':
                this.updateAnomalies(update.data);
                break;
            case 'invernadero/alertas/emergentes':
                this.displayRealAlert(update.data);
                break;
            case 'invernadero/predicciones':
                this.updatePredictions(update.data);
                break;
        }
    }

    updateSensorData(data) {
        // Actualizar datos de sensores con información real
        if (data) {
            console.log('🌡️ Datos de sensores actualizados:', {
                temperatura: data.Tair,
                humedad: data.Rhair,
                co2: data.CO2air,
                luz: data.AssimLight
            });
        }
    }

    updateAnomalies(data) {
        // Actualizar anomalías basadas en datos reales
        if (data && data.prediction === -1) {
            console.log('⚠️ Anomalía detectada:', data);
            // Aquí se actualizaría la visualización de anomalías
        }
    }

    displayRealAlert(alert) {
        console.log('🚨 Alerta real recibida:', alert);
        // Mostrar alerta real en el panel lateral
    }

    updatePredictions(data) {
        console.log('🔮 Predicciones actualizadas:', data);
        // Actualizar las recomendaciones del modelo predictivo
    }
}

// Inicializar dashboard cuando la página esté lista
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new PrecisionTomatoDashboard();
});

// Función global para compatibilidad
window.acknowledgeAlert = function() {
    console.log('✅ Alerta reconocida');
};
