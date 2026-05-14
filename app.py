import streamlit as st
import paho.mqtt.client as paho
import json
import time
import numpy as np

from streamlit_mic_recorder import mic_recorder
from keras.models import load_model
from PIL import Image

# ==================================================
# CONFIGURACIÓN GENERAL
# ==================================================

st.set_page_config(
    page_title="SmartCase AI Multimodal",
    layout="wide"
)

# ==================================================
# MQTT + ESTADO GLOBAL
# ==================================================

if "client" not in st.session_state:

    st.session_state.client = paho.Client(
        client_id=f"SmartCaseAI_{time.time()}"
    )

    st.session_state.sensor_data = {
        "temperature": 0,
        "humidity": 0,
        "motion": 0
    }

    st.session_state.connected = False

# ==================================================
# CALLBACK MQTT
# ==================================================

def on_message(client, userdata, message):

    try:

        st.session_state.sensor_data = json.loads(
            message.payload.decode("utf-8")
        )

    except:
        pass

# ==================================================
# CONEXIÓN MQTT
# ==================================================

if not st.session_state.connected:

    try:

        st.session_state.client.on_message = on_message

        st.session_state.client.connect(
            "157.230.214.127",
            1883
        )

        st.session_state.client.subscribe(
            "smartcase/sensors"
        )

        st.session_state.client.loop_start()

        st.session_state.connected = True

    except Exception as e:

        st.error(f"Error MQTT: {e}")

# ==================================================
# MODELO IA
# ==================================================

@st.cache_resource
def load_ai_model():
    return load_model("keras_model.h5")

model = load_ai_model()

class_names = [
    "Juan",
    "Peinilla",
    "Nada",
    "Celular"
]

# ==================================================
# SIDEBAR
# ==================================================

st.sidebar.title("🧭 Menú de Control")

pagina = st.sidebar.radio(
    "Selecciona una sección:",
    [
        "📊 Dashboard de Sensores",
        "🎙️ Control Multimodal (Voz/Texto)",
        "📷 Reconocimiento Visual IA"
    ]
)

# ==================================================
# PÁGINA 1
# DASHBOARD
# ==================================================

if pagina == "📊 Dashboard de Sensores":

    st.title("🏠 SmartCase: Monitoreo Físico")

    st.markdown(
        "Interacción en tiempo real con sensores simulados en Wokwi."
    )

    data = st.session_state.sensor_data

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Temperatura",
        f"{data['temperature']} °C"
    )

    col2.metric(
        "Humedad",
        f"{data['humidity']} %"
    )

    col3.metric(
        "Movimiento",
        "⚠️ MOVIMIENTO"
        if data['motion'] == 1
        else "✅ SEGURO"
    )

    st.markdown("---")

    st.subheader("Controles Rápidos")

    c1, c2 = st.columns(2)

    if c1.button(
        "🚨 Activar Alarma",
        use_container_width=True
    ):

        st.session_state.client.publish(
            "cmqtt_s",
            json.dumps({"Act1": "ON"})
        )

        st.success("Comando enviado")

    if c2.button(
        "🟢 Desactivar Alarma",
        use_container_width=True
    ):

        st.session_state.client.publish(
            "cmqtt_s",
            json.dumps({"Act1": "OFF"})
        )

        st.warning("Alarma desactivada")

    time.sleep(2)

    st.rerun()

# ==================================================
# PÁGINA 2
# VOZ + TEXTO
# ==================================================

elif pagina == "🎙️ Control Multimodal (Voz/Texto)":

    st.title("🎙️ Interacción Multimodal")

    st.info(
        "Utiliza comandos de voz o texto."
    )

    # ==============================================
    # VOZ
    # ==============================================

    st.markdown("### 🗣️ Entrada por Voz")

    audio = mic_recorder(
        start_prompt="Record 🎙️",
        stop_prompt="Stop ⏹️",
        key='voice_ctrl'
    )

    if audio:

        st.audio(audio['bytes'])

        st.success(
            "Audio capturado correctamente."
        )

    # ==============================================
    # TEXTO
    # ==============================================

    st.markdown("---")

    st.markdown("### ✍️ Entrada por Texto")

    comando = st.text_input(
        "Escribe una orden:"
    ).lower()

    if st.button("Ejecutar Comando"):

        if (
            "activar" in comando
            or
            "prender" in comando
        ):

            st.session_state.client.publish(
                "cmqtt_s",
                json.dumps({"Act1": "ON"})
            )

            st.success(
                "Comando enviado: Encender"
            )

        elif (
            "apagar" in comando
            or
            "desactivar" in comando
        ):

            st.session_state.client.publish(
                "cmqtt_s",
                json.dumps({"Act1": "OFF"})
            )

            st.warning(
                "Comando enviado: Apagar"
            )

        else:

            st.error(
                "Comando no reconocido."
            )

# ==================================================
# PÁGINA 3
# IA VISUAL
# ==================================================

elif pagina == "📷 Reconocimiento Visual IA":

    st.title("📷 Reconocimiento Visual IA")

    st.info(
        "Detección usando Teachable Machine"
    )

    img_file_buffer = st.camera_input(
        "Tomar Foto"
    )

    if img_file_buffer is not None:

        img = Image.open(img_file_buffer)

        st.image(
            img,
            caption="Imagen capturada",
            width=300
        )

        # ==========================================
        # PREPROCESAMIENTO
        # ==========================================

        img = img.resize((224, 224))

        img_array = np.array(img)

        normalized_image_array = (
            img_array.astype(np.float32) / 127.0
        ) - 1

        data = np.ndarray(
            shape=(1, 224, 224, 3),
            dtype=np.float32
        )

        data[0] = normalized_image_array

        # ==========================================
        # PREDICCIÓN
        # ==========================================

        prediction = model.predict(data)

        index = np.argmax(prediction)

        confidence = prediction[0][index]

        detected_class = class_names[index]

        st.success(
            f"Detectado: {detected_class}"
        )

        st.write(
            f"Probabilidad: {confidence:.2f}"
        )

        # ==========================================
        # MQTT AUTOMÁTICO
        # ==========================================

        if (
            detected_class == "Juan"
            and confidence > 0.7
        ):

            st.session_state.client.publish(
                "cmqtt_s",
                json.dumps({"Act1": "OFF"})
            )

            st.success(
                "Juan detectado → alarma desactivada"
            )

        elif (
            detected_class == "Celular"
            and confidence > 0.7
        ):

            st.session_state.client.publish(
                "cmqtt_s",
                json.dumps({"Act1": "ON"})
            )

            st.warning(
                "Celular detectado → alarma activada"
            )

        elif (
            detected_class == "Peinilla"
            and confidence > 0.7
        ):

            st.info(
                "Peinilla detectada"
            )

        elif detected_class == "Nada":

            st.write(
                "Sin objetos relevantes"
            )

# ==================================================
# FOOTER
# ==================================================

st.sidebar.markdown("---")

st.sidebar.markdown(
    """
    <div style='text-align: center;
                color: #4F8BF9;
                font-weight: bold;'>

        Creado por:<br>
        👨‍💻 Juan Felipe<br>
        👨‍💻 Santiago Marín

    </div>
    """,
    unsafe_allow_html=True
)
