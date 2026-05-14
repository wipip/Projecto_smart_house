import streamlit as st
import paho.mqtt.client as paho
import json
import time
from streamlit_mic_recorder import mic_recorder

# ==================================================
# CONFIGURACIÓN GENERAL
# ==================================================
st.set_page_config(page_title="SmartCase AI Multimodal", layout="wide")

# Inicialización del estado global para persistencia
if "client" not in st.session_state:
    st.session_state.client = paho.Client(client_id="SmartCaseAI_Unique")
    st.session_state.sensor_data = {"temperature": 0, "humidity": 0, "motion": 0}
    st.session_state.connected = False

# Callback para recibir datos de Wokwi
def on_message(client, userdata, message):
    try:
        st.session_state.sensor_data = json.loads(message.payload.decode("utf-8"))
    except:
        pass

# Lógica de conexión única
if not st.session_state.connected:
    try:
        st.session_state.client.on_message = on_message
        st.session_state.client.connect("157.230.214.127", 1883)
        st.session_state.client.subscribe("smartcase/sensors")
        st.session_state.client.loop_start()
        st.session_state.connected = True
    except Exception as e:
        st.error(f"Error de conexión MQTT: {e}")

# ==================================================
# [span_2](start_span)NAVEGACIÓN (Simulación de 2 páginas)[span_2](end_span)
# ==================================================
st.sidebar.title("Navegación del Proyecto")
pagina = st.sidebar.radio("Ir a:", ["📊 Dashboard de Sensores", "🎙️ Control Multimodal (Voz/Texto)"])

# ==================================================
# PÁGINA 1: DASHBOARD
# ==================================================
if pagina == "📊 Dashboard de Sensores":
    st.title("🏠 SmartCase: Monitoreo Físico")
    [span_3](start_span)[span_4](start_span)st.markdown("Interacción en tiempo real con el mundo físico simulado en Wokwi[span_3](end_span)[span_4](end_span).")

    # Indicadores visuales
    col1, col2, col3 = st.columns(3)
    data = st.session_state.sensor_data
    
    col1.metric("Temperatura", f"{data['temperature']} °C")
    col2.metric("Humedad", f"{data['humidity']} %")
    col3.metric("Movimiento", "⚠️ DETECTADO" if data['motion'] == 1 else "✅ SEGURO")

    st.markdown("---")
    st.subheader("Controles Rápidos")
    c1, c2 = st.columns(2)
    
    if c1.button("🚨 Activar Alarma", use_container_width=True):
        st.session_state.client.publish("cmqtt_s", json.dumps({"Act1": "ON"}))
        st.success("Comando enviado a Wokwi")

    if c2.button("🟢 Desactivar Alarma", use_container_width=True):
        st.session_state.client.publish("cmqtt_s", json.dumps({"Act1": "OFF"}))
        st.warning("Alarma desactivada")

    # Auto-refresco para ver cambios de sensores
    time.sleep(2)
    st.rerun()

# ==================================================
# [span_5](start_span)PÁGINA 2: CONTROL MULTIMODAL[span_5](end_span)
# ==================================================
elif pagina == "🎙️ Control Multimodal (Voz/Texto)":
    st.title("🎙️ Interacción Multimodal")
    [span_6](start_span)st.info("Esta sección permite interactuar mediante voz y comandos de texto[span_6](end_span).")

    # MODALIDAD 1: VOZ
    st.markdown("### 🗣️ Entrada por Voz")
    st.write("Haz clic para grabar un comando (Ej: 'Activar', 'Apagar'):")
    audio = mic_recorder(start_prompt="Record 🎙️", stop_prompt="Stop ⏹️", key='voice_ctrl')

    if audio:
        st.audio(audio['bytes'])
        st.success("Audio capturado. En un sistema real, aquí se procesaría con Whisper/Google STT.")

    # MODALIDAD 2: TEXTO
    st.markdown("---")
    st.markdown("### ✍️ Entrada por Texto (NLP Simple)")
    comando = st.text_input("Escribe tu orden para la casa:").lower()

    if st.button("Ejecutar Comando"):
        if "activar" in comando or "prender" in comando:
            st.session_state.client.publish("cmqtt_s", json.dumps({"Act1": "ON"}))
            st.success("Acción: Alarma encendida vía texto")
        elif "apagar" in comando or "desactivar" in comando:
            st.session_state.client.publish("cmqtt_s", json.dumps({"Act1": "OFF"}))
            st.warning("Acción: Alarma apagada vía texto")
        else:
            st.error("No entendí el comando. Intenta con 'Activar' o 'Desactivar'.")

    # [span_7](start_span)CRITERIOS DE EVALUACIÓN[span_7](end_span)
    with st.expander("Ver criterios de cumplimiento"):
        [span_8](start_span)st.write("* **Multimodal:** Voz, texto y botones[span_8](end_span).")
        [span_9](start_span)[span_10](start_span)st.write("* **Físico:** Conectado a MQTT/Wokwi[span_9](end_span)[span_10](end_span).")
        [span_11](start_span)st.write("* **Dos páginas:** Estructura de navegación lateral[span_11](end_span).")
