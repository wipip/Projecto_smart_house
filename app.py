import paho.mqtt.client as paho
import time
import streamlit as st
import json
import platform

# ==================================================
# CONFIGURACIÓN STREAMLIT
# ==================================================

st.set_page_config(
    page_title="SmartCase AI",
    layout="wide"
)

# ==================================================
# VARIABLES
# ==================================================

broker = "157.230.214.127"
port = 1883

if "conexion_estado" not in st.session_state:
    st.session_state.conexion_estado = "Sin conexión"

if "sensor_data" not in st.session_state:
    st.session_state.sensor_data = {
        "temperature": 0,
        "humidity": 0,
        "motion": 0
    }

# ==================================================
# CALLBACKS MQTT
# ==================================================

def on_connect(client, userdata, flags, rc):

    if rc == 0:
        st.session_state.conexion_estado = "Conectado"

        client.subscribe("smartcase/sensors")

    else:
        st.session_state.conexion_estado = "Error"

def on_publish(client, userdata, result):
    pass

def on_message(client, userdata, message):

    try:

        payload = json.loads(message.payload.decode("utf-8"))

        st.session_state.sensor_data = payload

    except:
        pass

# ==================================================
# CLIENTE MQTT
# ==================================================

client = paho.Client("SmartCaseAI")

client.on_connect = on_connect
client.on_message = on_message
client.on_publish = on_publish

try:
    client.connect(broker, port)
    client.loop_start()

except:
    st.session_state.conexion_estado = "Error"

# ==================================================
# HEADER
# ==================================================

st.title("SmartCase AI")
st.subheader("Sistema Inteligente Multimodal")

st.write("Versión Python:", platform.python_version())

# ==================================================
# ESTADO CONEXIÓN
# ==================================================

st.markdown("## Estado del sistema")

if st.session_state.conexion_estado == "Conectado":
    st.success("Conectado a MQTT / Wokwi")

elif st.session_state.conexion_estado == "Error":
    st.error("Error de conexión")

else:
    st.warning("Sin conexión")

# ==================================================
# DASHBOARD SENSORES
# ==================================================

st.markdown("## Dashboard en tiempo real")

col1, col2, col3 = st.columns(3)

col1.metric(
    "Temperatura",
    f"{st.session_state.sensor_data['temperature']} °C"
)

col2.metric(
    "Humedad",
    f"{st.session_state.sensor_data['humidity']} %"
)

motion_state = (
    "Detectado"
    if st.session_state.sensor_data["motion"] == 1
    else "No detectado"
)

col3.metric(
    "Movimiento",
    motion_state
)

# ==================================================
# CONTROLES
# ==================================================

st.markdown("## Controles inteligentes")

colA, colB = st.columns(2)

# ---------------- ALARMA ON ----------------

if colA.button("Activar alarma"):

    try:

        message = json.dumps({
            "Act1": "ON"
        })

        client.publish(
            "cmqtt_s",
            message
        )

        st.success("Alarma activada")

    except:

        st.error("No se pudo enviar")

# ---------------- ALARMA OFF ----------------

if colB.button("Desactivar alarma"):

    try:

        message = json.dumps({
            "Act1": "OFF"
        })

        client.publish(
            "cmqtt_s",
            message
        )

        st.warning("Alarma desactivada")

    except:

        st.error("No se pudo enviar")

# ==================================================
# CONTROL ANALÓGICO
# ==================================================

st.markdown("## Control de intensidad")

values = st.slider(
    "Selecciona intensidad",
    0.0,
    100.0
)

st.write("Valor:", values)

if st.button("Enviar valor"):

    try:

        message = json.dumps({
            "Analog": float(values)
        })

        client.publish(
            "cmqtt_a",
            message
        )

        st.success("Valor enviado")

    except:

        st.error("Error enviando valor")

# ==================================================
# INFORMACIÓN TÉCNICA
# ==================================================

with st.expander("Información técnica"):

    st.markdown("""
    ### Tecnologías usadas

    - ESP32
    - MQTT
    - Streamlit
    - Wokwi
    - Python

    ### Funciones

    - Comunicación en tiempo real
    - Sensores físicos
    - Automatización
    - Dashboard inteligente
    - Interacción multimodal
    """)

# ==================================================
# AUTO REFRESH
# ==================================================

time.sleep(1)
st.rerun()
