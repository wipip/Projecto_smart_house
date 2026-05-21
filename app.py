import streamlit as st
import paho.mqtt.client as paho
import json
import time
import numpy as np

from keras.models import load_model
from PIL import Image

# ==========================================
# REFRESH AUTOMÁTICO
# ==========================================
from streamlit_autorefresh import st_autorefresh

# ==========================================
# BOKEH
# ==========================================
from bokeh.models.widgets import Button
from bokeh.models import CustomJS
from streamlit_bokeh_events import streamlit_bokeh_events

# ==========================================
# CONFIG
# ==========================================
st.set_page_config(
    page_title="SmartCase AI",
    layout="wide"
)

# ==========================================
# MQTT CONFIG
# ==========================================
BROKER = "157.230.214.127"
PORT = 1883

# ==========================================
# MQTT + ESTADO GLOBAL
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
        payload = message.payload.decode("utf-8")
        st.session_state.sensor_data = json.loads(payload)
    except Exception as e:
        print(f"Error en recepción MQTT: {e}")

# ==========================================
# CONEXIÓN MQTT
# ==========================================
if not st.session_state.connected:
    try:
        st.session_state.client.on_message = on_message
        st.session_state.client.connect(BROKER, PORT)
        st.session_state.client.subscribe("smartcase/sensors")
        st.session_state.client.loop_start()
        st.session_state.connected = True
    except Exception as e:
        st.error(f"Error MQTT: {e}")

# ==========================================
# CARGAR MODELO IA
# ==========================================
@st.cache_resource
def cargar_modelo():
    return load_model("keras_model.h5")

model = cargar_modelo()

# ==========================================
# CLASES DEL MODELO
# ==========================================
class_names = [
    "Abrir puerta",
    "Denegar acceso"
]

# ==========================================
# SIDEBAR
# ==========================================
st.sidebar.title("🧭 Menú")

pagina = st.sidebar.radio(
    "Selecciona:",
    [
        "📊 Dashboard",
        "🎙️ Voz y Texto",
        "📷 Reconocimiento Facial IA"
    ]
)

# ==========================================
# DASHBOARD
# ==========================================
if pagina == "📊 Dashboard":
    st.title("🏠 SmartCase Dashboard")
    
    # Refresca la UI cada 2 segundos de forma segura
    st_autorefresh(interval=2000, key="datarefresh")

    data = st.session_state.sensor_data

    c1, c2, c3 = st.columns(3)
    c1.metric("Temperatura", f"{data['temperature']} °C")
    c2.metric("Humedad", f"{data['humidity']} %")
    c3.metric(
        "Movimiento",
        "⚠️ Detectado" if data["motion"] == 1 else "✅ Seguro"
    )
    
    st.markdown("---")

    b1, b2 = st.columns(2)

    if b1.button("🚨 Activar Alarma"):
        st.session_state.client.publish(
            "cmqtt_s",
            json.dumps({"Act1": "ON"})
        )
        st.success("Alarma activada")

    if b2.button("🟢 Desactivar Alarma"):
        st.session_state.client.publish(
            "cmqtt_s",
            json.dumps({"Act1": "OFF"})
        )
        st.warning("Alarma desactivada")

# ==========================================
# VOZ + TEXTO (Modificado Exclusivo Pin 5)
# ==========================================
elif pagina == "🎙️ Voz y Texto":
    st.title("🎙️ Control por Voz (LED Pin 5)")
    st.write("Presiona el botón y habla")

    # Botón Voz
    stt_button = Button(label="🎤 Hablar", width=200)
    stt_button.js_on_event(
        "button_click",
        CustomJS(code="""
        var recognition = new webkitSpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'es-ES';

        recognition.onresult = function(e) {
            var value = "";
            for (var i = e.resultIndex; i < e.results.length; ++i) {
                if (e.results[i].isFinal) {
                    value += e.results[i][0].transcript;
                }
            }
            if (value != "") {
                document.dispatchEvent(
                    new CustomEvent("GET_TEXT", {detail: value})
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

    # Resultado Voz -> Envía la clave "VozAct"
    if result:
        if "GET_TEXT" in result:
            voz = result.get("GET_TEXT").lower()
            st.success(f"Detectado: {voz}")

            if "activar" in voz or "encender" in voz or "prender" in voz:
                st.session_state.client.publish(
                    "cmqtt_s",
                    json.dumps({"VozAct": "ON"})
                )
                st.success("Comando enviado: Encender LED Voz")

            elif "apagar" in voz or "desactivar" in voz:
                st.session_state.client.publish(
                    "cmqtt_s",
                    json.dumps({"VozAct": "OFF"})
                )
                st.warning("Comando enviado: Apagar LED Voz")

    # Entrada de Texto -> Envía la clave "VozAct"
    st.markdown("---")
    comando = st.text_input("Escribe un comando:").lower()

    if st.button("Enviar Texto"):
        if "activar" in comando or "encender" in comando:
            st.session_state.client.publish(
                "cmqtt_s",
                json.dumps({"VozAct": "ON"})
            )
            st.success("Comando de texto enviado: LED Voz ON")

        elif "apagar" in comando or "desactivar" in comando:
            st.session_state.client.publish(
                "cmqtt_s",
                json.dumps({"VozAct": "OFF"})
            )
            st.warning("Comando de texto enviado: LED Voz OFF")

# ==========================================
# IA FACIAL
# ==========================================
elif pagina == "📷 Reconocimiento Facial IA":
    st.title("📷 Reconocimiento Facial IA")

    foto = st.camera_input("Tomar Foto")

    if foto is not None:
        img = Image.open(foto)
        st.image(img, width=300)

        # Preprocesamiento
        img = img.resize((224, 224))
        img_array = np.array(img)
        normalized_image_array = (img_array.astype(np.float32) / 127.0) - 1

        data = np.ndarray(shape=(1, 224, 224, 3), dtype=np.float32)
        data[0] = normalized_image_array

        # Predicción IA
        prediction = model.predict(data)
        index = np.argmax(prediction)
        confidence = prediction[0][index]
        clase = class_names[index]

        st.success(f"Detectado: {clase}")
        st.write(f"Probabilidad: {confidence:.2f}")

        # Control Puerta
        if clase == "Abrir puerta" and confidence > 0.80:
            st.session_state.client.publish(
                "cmqtt_s",
                json.dumps({"door": "OPEN"})
            )
            st.success("✅ Acceso permitido")

        elif clase == "Denegar acceso" and confidence > 0.80:
            st.session_state.client.publish(
                "cmqtt_s",
                json.dumps({"door": "DENY"})
            )
            st.error("🚨 Acceso denegado")

# ==========================================
# FOOTER
# ==========================================
st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    <div style='text-align:center; font-weight:bold; color:#4F8BF9;'>
        👨‍💻 Juan Felipe<br>
        👨‍💻 Santiago Marín
    </div>
    """,
    unsafe_allow_html=True
)
