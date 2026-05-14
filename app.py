import streamlit as st
import paho.mqtt.client as paho
import json
import time
import numpy as np

from keras.models import load_model
from PIL import Image

# ==========================================
# VOZ
# ==========================================

from bokeh.models import Button, CustomJS
from streamlit_bokeh_events import streamlit_bokeh_events

# ==========================================
# CONFIGURACIÓN
# ==========================================

st.set_page_config(
    page_title="SmartCase AI Multimodal",
    layout="wide"
)

# ==========================================
# MQTT
# ==========================================

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

# ==========================================
# CALLBACK MQTT
# ==========================================

def on_message(client, userdata, message):

    try:

        st.session_state.sensor_data = json.loads(
            message.payload.decode("utf-8")
        )

    except:
        pass

# ==========================================
# CONECTAR MQTT
# ==========================================

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

# ==========================================
# MODELO IA
# ==========================================

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

# ==========================================
# SIDEBAR
# ==========================================

st.sidebar.title("🧭 Menú de Control")

pagina = st.sidebar.radio(
    "Selecciona una sección:",
    [
        "📊 Dashboard de Sensores",
        "🎙️ Control Multimodal",
        "📷 Reconocimiento Visual IA"
    ]
)

# ==========================================
# PÁGINA 1
# DASHBOARD
# ==========================================

if pagina == "📊 Dashboard de Sensores":

    st.title("🏠 SmartCase")

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

    c1, c2 = st.columns(2)

    if c1.button("🚨 Activar Alarma"):

        st.session_state.client.publish(
            "cmqtt_s",
            json.dumps({"Act1": "ON"})
        )

        st.success("Alarma activada")

    if c2.button("🟢 Desactivar Alarma"):

        st.session_state.client.publish(
            "cmqtt_s",
            json.dumps({"Act1": "OFF"})
        )

        st.warning("Alarma desactivada")

    time.sleep(2)

    st.rerun()

# ==========================================
# PÁGINA 2
# CONTROL MULTIMODAL
# ==========================================

elif pagina == "🎙️ Control Multimodal":

    st.title("🎙️ Control por Voz y Texto")

    st.markdown("## 🗣️ Control por Voz")

    st.write("Presiona el botón y habla")

    # ==========================================
    # BOTÓN VOZ
    # ==========================================

    stt_button = Button(
        label="🎤 Hablar",
        width=200
    )

    stt_button.js_on_event(
        "button_click",

        CustomJS(code="""
        var recognition = new webkitSpeechRecognition();

        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'es-ES';

        recognition.onresult = function (e) {

            var value = "";

            for (var i = e.resultIndex;
                 i < e.results.length;
                 ++i) {

                if (e.results[i].isFinal) {

                    value += e.results[i][0].transcript;
                }
            }

            if (value != "") {

                document.dispatchEvent(
                    new CustomEvent(
                        "GET_TEXT",
                        {detail: value}
                    )
                );
            }
        }

        recognition.start();
        """)
    )

    result = streamlit_bokeh_events(
        stt_button,
        events="GET_TEXT",
        key="listen",
        refresh_on_update=False,
        override_height=75,
        debounce_time=0
    )

    # ==========================================
    # RESULTADO VOZ
    # ==========================================

    if result:

        if "GET_TEXT" in result:

            voz = result.get("GET_TEXT").lower()

            st.success(f"Comando detectado: {voz}")

            # ======================================
            # COMANDOS VOZ
            # ======================================

            if (
                "activar" in voz
                or
                "encender" in voz
                or
                "prender" in voz
            ):

                st.session_state.client.publish(
                    "cmqtt_s",
                    json.dumps({"Act1": "ON"})
                )

                st.success(
                    "Comando enviado → ON"
                )

            elif (
                "apagar" in voz
                or
                "desactivar" in voz
            ):

                st.session_state.client.publish(
                    "cmqtt_s",
                    json.dumps({"Act1": "OFF"})
                )

                st.warning(
                    "Comando enviado → OFF"
                )

            else:

                st.error(
                    "Comando no reconocido"
                )

    # ==========================================
    # TEXTO
    # ==========================================

    st.markdown("---")

    st.markdown("## ✍️ Control por Texto")

    comando = st.text_input(
        "Escribe una orden:"
    ).lower()

    if st.button("Enviar Texto"):

        if (
            "activar" in comando
            or
            "encender" in comando
        ):

            st.session_state.client.publish(
                "cmqtt_s",
                json.dumps({"Act1": "ON"})
            )

            st.success("Alarma activada")

        elif (
            "apagar" in comando
            or
            "desactivar" in comando
        ):

            st.session_state.client.publish(
                "cmqtt_s",
                json.dumps({"Act1": "OFF"})
            )

            st.warning("Alarma desactivada")

        else:

            st.error("Comando no reconocido")

# ==========================================
# PÁGINA 3
# IA VISUAL
# ==========================================

elif pagina == "📷 Reconocimiento Visual IA":

    st.title("📷 IA Visual")

    img_file_buffer = st.camera_input(
        "Tomar Foto"
    )

    if img_file_buffer is not None:

        img = Image.open(img_file_buffer)

        st.image(img, width=300)

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

        # ======================================
        # AUTOMATIZACIÓN MQTT
        # ======================================

        if (
            detected_class == "Juan"
            and confidence > 0.7
        ):

            st.session_state.client.publish(
                "cmqtt_s",
                json.dumps({"Act1": "OFF"})
            )

            st.success(
                "Juan detectado → alarma OFF"
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
                "Celular detectado → alarma ON"
            )

# ==========================================
# FOOTER
# ==========================================

st.sidebar.markdown("---")

st.sidebar.markdown(
    """
    <div style='text-align:center;
                color:#4F8BF9;
                font-weight:bold;'>

        Creado por:<br>
        👨‍💻 Juan Felipe<br>
        👨‍💻 Santiago Marín

    </div>
    """,

    unsafe_allow_html=True
)
