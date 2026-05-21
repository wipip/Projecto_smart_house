import streamlit as st
import paho.mqtt.client as mqtt
import json
from streamlit_autorefresh import st_autorefresh

# ==============================================================================
# 1. CONFIGURACIÓN DE LA PÁGINA Y AUTO-REFRESCO
# ==============================================================================
st.set_page_config(
    page_title="SmartCase Dashboard",
    page_icon="🏠",
    layout="wide"
)

# Forzar a Streamlit a actualizar la interfaz de forma silenciosa cada 2 segundos.
# Esto asegura que los datos que guarda MQTT en el session_state se pinten en vivo.
st_autorefresh(interval=2000, key="mqtt_data_refresh")

# ==============================================================================
# 2. INICIALIZACIÓN DEL ESTADO GLOBAL (SESSION STATE)
# ==============================================================================
# Creamos las variables de memoria interna si es la primera vez que corre la app
if "temp" not in st.session_state:
    st.session_state.temp = 0.0
if "hum" not in st.session_state:
    st.session_state.hum = 0.0
if "motion" not in st.session_state:
    st.session_state.motion = 0
if "estado_alarma" not in st.session_state:
    st.session_state.estado_alarma = "OFF"
if "estado_voz" not in st.session_state:
    st.session_state.estado_voz = "OFF"

# ==============================================================================
# 3. FUNCIONES DE RESPALDO (CALLBACKS) DE MQTT
# ==============================================================================
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Conectado exitosamente al Broker MQTT")
        # Nos suscribimos al canal de salida de sensores de Wokwi
        client.subscribe("smartcase/sensors")
    else:
        print(f"Error de conexión al broker. Código: {rc}")

def on_message(client, userdata, message):
    try:
        # Decodificamos el buffer de texto plano enviado por el ESP32
        payload_str = message.payload.decode("utf-8")
        datos = json.loads(payload_str)
        
        # Guardamos los valores reales del JSON dentro de la memoria de Streamlit
        st.session_state.temp = float(datos.get("temperature", 0.0))
        st.session_state.hum = float(datos.get("humidity", 0.0))
        st.session_state.motion = int(datos.get("motion", 0))
    except Exception as e:
        print(f"Error al procesar el mensaje JSON entrante: {e}")

# ==============================================================================
# 4. ARRANQUE DEL CLIENTE MQTT ASÍNCRONO
# ==============================================================================
if "mqtt_client" not in st.session_state:
    broker_ip = "157.230.214.127"
    puerto = 1883
    
    nuevo_cliente = mqtt.Client()
    nuevo_cliente.on_connect = on_connect
    nuevo_cliente.on_message = on_message
    
    try:
        nuevo_cliente.connect(broker_ip, puerto, 60)
        # loop_start() abre un hilo independiente para que la web no se trabe
        nuevo_cliente.loop_start()
        # Almacenamos el cliente activo en el estado para reutilizarlo al enviar comandos
        st.session_state.mqtt_client = nuevo_cliente
    except Exception as e:
        st.error(f"No se pudo conectar al servidor MQTT: {e}")

# ==============================================================================
# 5. DISEÑO DE LA INTERFAZ VISUAL (DASHBOARD)
# ==============================================================================
st.title("🏠 Sistema de Control Residencial - SmartCase")
st.markdown("Monitoreo de sensores en tiempo real y panel de control remoto.")
st.divider()

# --- SECCIÓN A: TELEMETRÍA EN VIVO (MÉTRICAS) ---
st.subheader("📊 Estado de los Sensores en Vivo (Wokwi)")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="🌡️ Temperatura Ambiente", 
        value=f"{st.session_state.temp:.2f} °C",
        delta=None
    )

with col2:
    st.metric(
        label="💧 Humedad Relativa", 
        value=f"{st.session_state.hum:.2f} %",
        delta=None
    )

with col3:
    # Mostramos una alerta visual interactiva si el PIR se activa
    if st.session_state.motion == 1:
        st.error("🚨 ¡MOVIMIENTO DETECTADO EN LA CASA!")
    else:
        st.success("🟢 Zona Segura - Sin Actividad")

st.divider()

# --- SECCIÓN B: PANEL DE CONTROL DE ACTUADORES (ENVIAR COMANDOS) ---
st.subheader("🎛️ Panel de Mandos y Actuadores")
st.markdown("Los botones envían señales JSON directamente hacia el canal `cmqtt_s` de Wokwi.")

col_btn1, col_btn2, col_btn3 = st.columns(3)

# Función auxiliar para armar el JSON y publicarlo
def enviar_comando_mqtt(llave, valor):
    if "mqtt_client" in st.session_state:
        # Formato del mensaje estructurado esperado por el callback del ESP32
        comando = {llave: valor}
        json_comando = json.dumps(comando)
        st.session_state.mqtt_client.publish("cmqtt_s", json_comando)

with col_btn1:
    st.write("**Sistema de Alarma General**")
    if st.button("🚨 Encender Alarma", use_container_width=True):
        enviar_comando_mqtt("Act1", "ON")
        st.session_state.estado_alarma = "ON"
        st.info("Comando enviado: Encender Alarma (Servo 180°, Buzzer y LED 2)")
        
    if st.button("🛑 Apagar Alarma", use_container_width=True):
        enviar_comando_mqtt("Act1", "OFF")
        st.session_state.estado_alarma = "OFF"
        st.success("Comando enviado: Apagar Alarma (Servo 0° y Silenciar)")

with col_btn2:
    st.write("**Acceso (Simulación Facial)**")
    if st.button("🔓 Conceder Acceso (Abrir Puerta)", use_container_width=True):
        enviar_comando_mqtt("door", "OPEN")
        st.warning("Comando enviado: Abrir puerta temporalmente")
        
    if st.button("🔒 Denegar Acceso (Alerta)", use_container_width=True):
        enviar_comando_mqtt("door", "DENY")
        st.error("Comando enviado: Bloquear acceso y parpadear alerta")

with col_btn3:
    st.write("**Módulo de Voz / Texto**")
    if st.button("💡 Activar LED de Voz", use_container_width=True):
        enviar_comando_mqtt("VozAct", "ON")
        st.session_state.estado_voz = "ON"
        st.info("Comando enviado: Encender LED Exclusivo por Voz (Pin 5)")
        
    if st.button("🔌 Desactivar LED de Voz", use_container_width=True):
        enviar_comando_mqtt("VozAct", "OFF")
        st.session_state.estado_voz = "OFF"
        st.success("Comando enviado: Apagar LED de Voz (Pin 5)")

# --- SECCIÓN C: PIE DE PÁGINA INFORMATIVO ---
st.sidebar.subheader("⚙️ Configuración de Red")
st.sidebar.text(f"Broker IP: 157.230.214.127")
st.sidebar.text("Puerto: 1883")
st.sidebar.divider()
st.sidebar.write("**Monitoreo de Variables Internas:**")
st.sidebar.json({
    "Alarma General": st.session_state.estado_alarma,
    "Módulo Voz": st.session_state.estado_voz,
    "Sensor DHT22 Coordenadas": "GPIO 16 (Etiqueta 4)"
})
