import streamlit as st
import paho.mqtt.client as paho
import json
import time
from streamlit_mic_recorder import mic_recorder

# ==================================================
# CONFIGURACIÓN GENERAL
# ==================================================
st.set_page_config(page_title="SmartCase AI Multimodal", layout="wide")

# Inicialización del estado global para persistencia y estabilidad
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

# Lógica de conexión única para evitar bucles de reconexión
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
# NAVEGACIÓN (Mínimo dos páginas requeridas)
# ==================================================
st.sidebar.title("🧭 Menú de Control")
pagina = st.sidebar.radio("Selecciona una sección:", ["📊 Dashboard de Sensores", "🎙️ Control Multimodal (Voz/Texto)"])

# ==================================================
# PÁGINA 1: DASHBOARD
# ==================================================
if pagina == "📊 Dashboard de Sensores":
    st.title("🏠 SmartCase: Monitoreo Físico")
    st.markdown("Interacción en tiempo real con sensores simulados en Wokwi.")

    # Indicadores visuales (Metrics)
    col1, col2, col3 = st.columns(3)
    data = st.session_state.sensor_data
    
    col1.metric("Temperatura", f"{data['temperature']} °C")
    col2.metric("Humedad", f"{data['humidity']} %")
    col3.metric("Movimiento", "⚠️ MOVIMIENTO" if data['motion'] == 1 else "✅ SEGURO")

    st.markdown("---")
    st.subheader("Controles Rápidos (Botones)")
    c1, c2 = st.columns(2)
    
    if c1.button("🚨 Activar Alarma", use_container_width=True):
        st.session_state.client.publish("cmqtt_s", json.dumps({"Act1": "ON"}))
        st.success("Comando enviado a Wokwi")

    if c2.button("🟢 Desactivar Alarma", use_container_width=True):
        st.session_state.client.publish("cmqtt_s", json.dumps({"Act1": "OFF"}))
        st.warning("Alarma desactivada")

    # Auto-refresco para datos en tiempo real
    time.sleep(2)
    st.rerun()

# ==================================================
# PÁGINA 2: CONTROL MULTIMODAL
# ==================================================
elif pagina == "🎙️ Control Multimodal (Voz/Texto)":
    st.title("🎙️ Interacción Multimodal")
    [span_1](start_span)st.info("Utiliza comandos de voz o texto para interactuar con el sistema físico[span_1](end_span).")

    # MODALIDAD 1: VOZ (Activación de Micrófono)
    st.markdown("### 🗣️ Entrada por Voz")
    st.write("Haz clic en 'Record' para hablar:")
    
    # El componente mic_recorder activa el hardware del micrófono
    audio = mic_recorder(
        start_prompt="Record 🎙️", 
        stop_prompt="Stop ⏹️", 
        key='voice_ctrl'
    )

    if audio:
        st.audio(audio['bytes'])
        st.success("Audio capturado correctamente.")
        st.caption("Nota: El audio ha sido recibido por el sistema para su procesamiento.")

    # MODALIDAD 2: TEXTO
    st.markdown("---")
    st.markdown("### ✍️ Entrada por Texto")
    comando = st.text_input("Escribe tu orden (ej: 'activar alarma'):").lower()

    if st.button("Ejecutar Comando"):
        if "activar" in comando or "prender" in comando:
            st.session_state.client.publish("cmqtt_s", json.dumps({"Act1": "ON"}))
            st.success("Comando de voz/texto enviado: Encender")
        elif "apagar" in comando or "desactivar" in comando:
            st.session_state.client.publish("cmqtt_s", json.dumps({"Act1": "OFF"}))
            st.warning("Comando de voz/texto enviado: Apagar")
        else:
            st.error("Comando no reconocido. Intenta con palabras clave como 'activar'.")

# ==================================================
# PIE DE PÁGINA (CRÉDITOS)
# ==================================================
st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    <div style='text-align: center; color: #4F8BF9; font-weight: bold;'>
        Creado por:<br>
        👨‍💻 Juan Felipe<br>
        👨‍💻 Santiago Marín
    </div>
    """, 
    unsafe_allow_html=True
)
