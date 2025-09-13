const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const mqtt = require('mqtt');
const cors = require('cors');
const path = require('path');
require('dotenv').config();

const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"]
  }
});

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('public'));
app.set('view engine', 'ejs');
app.set('views', './views');

// MQTT Configuration
const MQTT_BROKER = process.env.MQTT_BROKER || 'mqtt://localhost:1883';
const mqttClient = mqtt.connect(MQTT_BROKER);

// Data storage (en producción usar base de datos)
let dashboardData = {
  sensors: {},
  alerts: [],
  predictions: {},
  systemStatus: {
    layer1: { status: 'online', lastUpdate: new Date() },
    layer2: { status: 'online', lastUpdate: new Date() },
    layer5: { status: 'online', lastUpdate: new Date() }
  },
  statistics: {
    totalAlerts: 0,
    criticalAlerts: 0,
    anomaliesDetected: 0
  }
};

// MQTT Event Handlers
mqttClient.on('connect', () => {
  console.log('🔗 Connected to MQTT Broker');

  // Suscribirse a topics relevantes
  const topics = [
    'invernadero/sensores/raw',
    'invernadero/alertas/emergentes',
    'invernadero/predicciones',
    'invernadero/anomalias'
  ];

  topics.forEach(topic => {
    mqttClient.subscribe(topic, (err) => {
      if (!err) {
        console.log(`📡 Subscribed to ${topic}`);
      }
    });
  });
});

mqttClient.on('message', (topic, message) => {
  try {
    const data = JSON.parse(message.toString());

    switch (topic) {
      case 'invernadero/sensores/raw':
        handleSensorData(data);
        break;
      case 'invernadero/alertas/emergentes':
        handleEmergencyAlert(data);
        break;
      case 'invernadero/predicciones':
        handlePredictionData(data);
        break;
      case 'invernadero/anomalias':
        handleAnomalyData(data);
        break;
    }

    // Emit to all connected clients
    io.emit('dataUpdate', {
      topic,
      data,
      timestamp: new Date()
    });

  } catch (error) {
    console.error(`❌ Error processing MQTT message from ${topic}:`, error);
  }
});

// Data Handlers
function handleSensorData(data) {
  const sensorId = `sensor_${Date.now()}`;
  dashboardData.sensors[sensorId] = {
    ...data,
    timestamp: new Date(),
    status: 'active'
  };

  // Mantener solo los últimos 100 registros
  const sensorKeys = Object.keys(dashboardData.sensors);
  if (sensorKeys.length > 100) {
    delete dashboardData.sensors[sensorKeys[0]];
  }
}

function handleEmergencyAlert(data) {
  const alert = {
    id: `alert_${Date.now()}`,
    ...data,
    timestamp: new Date(),
    acknowledged: false
  };

  dashboardData.alerts.unshift(alert);
  dashboardData.statistics.totalAlerts++;

  if (data.severity === 'CRITICAL') {
    dashboardData.statistics.criticalAlerts++;
  }

  // Mantener solo las últimas 50 alertas
  if (dashboardData.alerts.length > 50) {
    dashboardData.alerts = dashboardData.alerts.slice(0, 50);
  }

  // Emit specific alert event
  io.emit('newAlert', alert);
}

function handlePredictionData(data) {
  dashboardData.predictions = {
    ...data,
    timestamp: new Date()
  };
}

function handleAnomalyData(data) {
  dashboardData.statistics.anomaliesDetected++;
}

// Routes
app.get('/', (req, res) => {
  res.render('dashboard', {
    title: 'Smart Forecasting for Tomato Greenhouses',
    data: dashboardData
  });
});

app.get('/api/dashboard-data', (req, res) => {
  res.json(dashboardData);
});

app.post('/api/alerts/:id/acknowledge', (req, res) => {
  const alertId = req.params.id;
  const alert = dashboardData.alerts.find(a => a.id === alertId);

  if (alert) {
    alert.acknowledged = true;
    alert.acknowledgedAt = new Date();
    res.json({ success: true, alert });
  } else {
    res.status(404).json({ error: 'Alert not found' });
  }
});

// Socket.io for real-time updates
io.on('connection', (socket) => {
  console.log('👤 Client connected:', socket.id);

  // Send current data to new client
  socket.emit('initialData', dashboardData);

  socket.on('requestData', () => {
    socket.emit('dataUpdate', dashboardData);
  });

  socket.on('acknowledgeAlert', (alertId) => {
    const alert = dashboardData.alerts.find(a => a.id === alertId);
    if (alert) {
      alert.acknowledged = true;
      io.emit('alertAcknowledged', alertId);
    }
  });

  socket.on('disconnect', () => {
    console.log('👤 Client disconnected:', socket.id);
  });
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date(),
    mqtt: mqttClient.connected ? 'connected' : 'disconnected',
    uptime: process.uptime()
  });
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`🚀 Dashboard server running on port ${PORT}`);
  console.log(`📊 Access dashboard at: http://localhost:${PORT}`);
});