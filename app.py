import streamlit as st
import paho.mqtt.client as paho
import json
import time
import numpy as np
from PIL import Image, ImageOps
from keras.models import load_model
from streamlit_mic_recorder import mic_recorder

# ==================================================
# CONFIGURACIÓN Y ESTADO
# ==================================================
st.set_page_config(page_title="SmartCase AI Multimodal", layout="wide")

if "client" not in st.session_state:
    st.session_state.client = paho.Client(client_id="SmartCaseAI_Final")
    st.session_state.sensor_data = {"temperature": 0, "humidity": 0, "motion": 0}
    st.session_state.connected = False

def on_message(client, userdata, message):
    try:
        st.session_state.sensor_data = json.loads(message.payload.decode("utf-8"))
    except:
        pass

if not st.session_state.connected:
    try:
        st.session_state.client.on_message = on_message
        st.session_state.client.connect("157.230.214.127", 1883)
        st.session_state.client.subscribe("smartcase/sensors")
        st.session_state.client.loop_start()
        st.session_state.connected = True
    except:
        st.sidebar.error("MQTT no conectado")

# ==================================================
# FUNCIONES DE IA (TEACHABLE MACHINE)
# ==================================================
@st.cache_resource
def cargar_recursos_ia():
    model = load_model("keras_model.h5", compile=False)
    with open("labels.txt", "r", encoding="utf-8") as f:
        labels = [line.strip()[2:] if len(line.strip()) > 2 else line.strip() for line in f.readlines()]
    return model, labels

def procesar_ia(img_file, model, labels):
    image = Image.open(img_file).convert("RGB")
    image = ImageOps.fit(image, (224, 224), Image.Resampling.LANCZOS)
    image_array = (np.asarray(image).astype(np.float32) / 127.5) - 1
    data = np.ndarray((1, 224, 224, 3), dtype=np.float32)
    data[0] = image_array
    prediction = model.predict(data, verbose=0)[0]
    index = np.argmax(prediction)
    return labels[index], prediction[index]

# ==================================================
# NAVEGACIÓN
# ==================================================
st.sidebar.title("🧭 SmartCase AI")
pagina = st.sidebar.radio("Secciones:", ["📊 Dashboard", "🎙️ Voz y Texto", "👁️ Visión Artificial"])

# --- PÁGINA 1: DASHBOARD ---
if pagina == "📊 Dashboard":
    st.title("🏠 Monitoreo Físico")
    d = st.session_state.sensor_data
    c1, c2, c3 = st.columns(3)
    c1.metric("Temperatura", f"{d['temperature']} °C")
    c2.metric("Humedad", f"{d['humidity']} %")
    c3.metric("Movimiento", "⚠️" if d['motion'] == 1 else "✅")
    
    if st.button("🚨 Alarma Manual"):
        st.session_state.client.publish("cmqtt_s", json.dumps({"Act1": "ON"}))
    time.sleep(2)
    st.rerun()

# --- PÁGINA 2: VOZ Y TEXTO ---
elif pagina == "🎙️ Voz y Texto":
    st.title("🎙️ Control por Voz/Texto")
    audio = mic_recorder(start_prompt="Hablar 🎙️", stop_prompt="Detener ⏹️", key='v1')
    if audio: st.success("Audio capturado")
    
    cmd = st.text_input("Escribe una orden:").lower()
    if st.button("Ejecutar"):
        act = "ON" if "activar" in cmd else "OFF"
        st.session_state.client.publish("cmqtt_s", json.dumps({"Act1": act}))

# --- PÁGINA 3: VISIÓN (TEACHABLE MACHINE) ---
elif pagina == "👁️ Visión Artificial":
    st.title("👁️ Control por Gestos")
    try:
        model, labels = cargar_recursos_ia()
        img = st.camera_input("Muestra un gesto a la cámara")
        if img:
            clase, conf = procesar_ia(img, model, labels)
            st.write(f"Detectado: **{clase}** ({conf:.2%})")
            
            # Lógica de interacción con el mundo físico
            if "arriba" in clase.lower():
                st.session_state.client.publish("cmqtt_s", json.dumps({"Act1": "ON"}))
                st.success("Gesto detectado: Activando Alarma en Wokwi")
            else:
                st.session_state.client.publish("cmqtt_s", json.dumps({"Act1": "OFF"}))
                st.warning("Gesto detectado: Desactivando Alarma")
    except Exception as e:
        st.error(f"Sube keras_model.h5 y labels.txt a GitHub: {e}")

# ==================================================
# CRÉDITOS
# ==================================================
st.sidebar.markdown("---")
st.sidebar.markdown("<div style='text-align: center; color: #4F8BF9;'><b>Creado por:</b><br>Juan Felipe & Santiago Marín</div>", unsafe_allow_html=True)
