import streamlit as st
import paho.mqtt.client as mqtt
import json
import time
import numpy as np

from keras.models import load_model
from PIL import Image

# ==========================================
# BOKEH
# ==========================================
from bokeh.models.widgets import Button
from bokeh.models import CustomJS
from streamlit_bokeh_events import streamlit_bokeh_events

# ==========================================
# CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(
    page_title="SmartCase AI",
    layout="wide"
)

# ==========================================
# CONFIGURACIÓN MQTT (Idéntica a su app receptora)
# ==========================================
if 'sensor_data' not in st.session_state:
    st.session_state.sensor_data = None

TOPIC_SEND = "cmqtt_s"

def get_mqtt_message(broker, port, topic, client_id):
    """Función exacta de su código funcional para obtener un mensaje MQTT"""
    message_received = {"received": False, "payload": None}
    
    def on_message(client, userdata, message):
        try:
            payload = json.loads(message.payload.decode())
            message_received["payload"] = payload
            message_received["received"] = True
        except:
            # Si no es JSON, guardar como texto
            message_received["payload"] = message.payload.decode()
            message_received["received"] = True
            
    try:
        client = mqtt.Client(client_id=client_id)
        client.on_message = on_message
        client.connect(broker, port, 60)
        client.subscribe(topic)
        client.loop_start()
        
        # Esperar máximo 5 segundos
        timeout = time.time() + 5
        while not message_received["received"] and time.time() < timeout:
            time.sleep(0.1)
            
        client.loop_stop()
        client.disconnect()
        
        # Log en consola para verificación de los datos reales recibidos
        print(f"\n[MQTT RECEPTOR] Datos crudos que entraron: {message_received['payload']}")
        
        return message_received["payload"]
        
    except Exception as e:
        return {"error": str(e)}

# Cliente persistente en sesión exclusivo para el ENVÍO de comandos hacia Wokwi
if "client" not in st.session_state:
    try:
        client_id_send = "streamlit_client_send"
        st.session_state.client = mqtt.Client(client_id=client_id_send)
        st.session_state.client.connect("broker.mqttdashboard.com", 1883, 60)
        st.session_state.client.loop_start()
    except Exception as e:
        st.error(f"Error en pasarela de salida: {e}")

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
# SIDEBAR (Configuración Dinámica Unificada)
# ==========================================
with st.sidebar:
    st.title("🧭 Menú")
    pagina = st.sidebar.radio(
        "Selecciona:",
        [
            "📊 Dashboard",
            "🎙️ Voz y Texto",
            "📷 Reconocimiento Facial IA"
        ]
    )
    
    st.markdown("---")
    st.subheader('⚙️ Configuración de Conexión')
    
    broker = st.text_input('Broker MQTT', value='broker.mqttdashboard.com', 
                           help='Dirección del broker MQTT')
    
    port = st.number_input('Puerto', value=1883, min_value=1, max_value=65535,
                           help='Puerto del broker (generalmente 1883)')
    
    topic = st.text_input('Tópico', value='Sensor/THP3',
                          help='Tópico MQTT a suscribirse')
    
    client_id = st.text_input('ID del Cliente', value='streamlit_client',
                              help='Identificador único para este cliente')

# ==========================================
# DASHBOARD (Reescrito EXACTAMENTE como el receptor exitoso)
# ==========================================
if pagina == "📊 Dashboard":
    st.title("🏠 SmartHouse Dashboard")
    st.write("Gestiona la recepción de datos y actuadores de la casa inteligente.")
    
    # Botón idéntico a su aplicación funcional
    if st.button('🔄 recibir datos del wokwi/arduino', use_container_width=True):
        with st.spinner('Conectando al broker y esperando datos...'):
            sensor_data = get_mqtt_message(broker, int(port), topic, client_id)
            st.session_state.sensor_data = sensor_data

    # Renderizado idéntico y dinámico basado en la estructura que viene de Wokwi
    if st.session_state.sensor_data:
        st.divider()
        st.subheader('📊 Datos Recibidos')
        
        data = st.session_state.sensor_data
        
        # Verificar si hay error
        if isinstance(data, dict) and 'error' in data:
            st.error(f"❌ Error de conexión: {data['error']}")
        else:
            st.success('✅ Datos recibidos correctamente')
            
            # Si es un diccionario (JSON), se adapta dinámicamente a "Temp", "Hum", etc.
            if isinstance(data, dict):
                cols = st.columns(len(data))
                for i, (key, value) in enumerate(data.items()):
                    with cols[i]:
                        st.metric(label=key, value=value)
                
                # Desplegable para ver el JSON completo en bruto
                with st.expander('Ver JSON completo'):
                    st.json(data)
            else:
                # Si no es diccionario, mostrar como texto plano
                st.code(data)

    # Bloque de actuadores original de la alarma (se mantiene intacto abajo)
    st.markdown("---")
    st.subheader("🎮 Control de Actuadores")
    b1, b2 = st.columns(2)

    if b1.button("🚨 Activar Alarma", use_container_width=True):
        st.session_state.client.publish(TOPIC_SEND, json.dumps({"Act1": "ON"}))
        st.success("Alarma activada")

    if b2.button("🟢 Desactivar Alarma", use_container_width=True):
        st.session_state.client.publish(TOPIC_SEND, json.dumps({"Act1": "OFF"}))
        st.warning("Alarma desactivada")

# ==========================================
# VOZ + TEXTO (Totalmente quieto)
# ==========================================
elif pagina == "🎙️ Voz y Texto":
    st.title("🎙️ Control por Voz (LED Pin 5)")
    st.write("Presiona el botón y habla")

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

    if result and "GET_TEXT" in result:
        voz = result.get("GET_TEXT").lower()
        st.success(f"Detectado: {voz}")

        if "activar" in voz or "encender" in voz or "prender" in voz:
            st.session_state.client.publish(TOPIC_SEND, json.dumps({"VozAct": "ON"}))
            st.success("Comando enviado: Encender LED Voz")
        elif "apagar" in voz or "desactivar" in voz:
            st.session_state.client.publish(TOPIC_SEND, json.dumps({"VozAct": "OFF"}))
            st.warning("Comando enviado: Apagar LED Voz")

    st.markdown("---")
    comando = st.text_input("Escribe un comando:").lower()

    if st.button("Enviar Texto"):
        if "activar" in comando or "encender" in comando:
            st.session_state.client.publish(TOPIC_SEND, json.dumps({"VozAct": "ON"}))
            st.success("Comando de texto enviado: LED Voz ON")
        elif "apagar" in comando or "desactivar" in comando:
            st.session_state.client.publish(TOPIC_SEND, json.dumps({"VozAct": "OFF"}))
            st.warning("Comando de texto enviado: LED Voz OFF")

# ==========================================
# IA FACIAL (Totalmente quieto)
# ==========================================
elif pagina == "📷 Reconocimiento Facial IA":
    st.title("📷 Reconocimiento Facial IA")

    foto = st.camera_input("Tomar Foto")

    if foto is not None:
        img = Image.open(foto)
        st.image(img, width=300)

        img = img.resize((224, 224))
        img_array = np.array(img)
        normalized_image_array = (img_array.astype(np.float32) / 127.0) - 1

        data = np.ndarray(shape=(1, 224, 224, 3), dtype=np.float32)
        data[0] = normalized_image_array

        prediction = model.predict(data)
        index = np.argmax(prediction)
        confidence = prediction[0][index]
        clase = class_names[index]

        st.success(f"Detectado: {clase}")
        st.write(f"Probabilidad: {confidence:.2f}")

        if clase == "Abrir puerta" and confidence > 0.80:
            st.session_state.client.publish(TOPIC_SEND, json.dumps({"door": "OPEN"}))
            st.success("✅ Acceso permitido")
        elif clase == "Denegar acceso" and confidence > 0.80:
            st.session_state.client.publish(TOPIC_SEND, json.dumps({"door": "DENY"}))
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
