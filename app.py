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
# CONFIGURACIÓN MQTT UNIFICADA (Paho 1.6.1)
# ==========================================
BROKER = "broker.mqttdashboard.com"
PORT = 1883
TOPIC_RECEIVE = "Sensor/THP3"  # Su tópico asignado actualizado
TOPIC_SEND = "cmqtt_s"

# Inicializar variables de estado en sesión para evitar pérdidas al cambiar de menú
if 'sensor_data' not in st.session_state:
    st.session_state.sensor_data = {"temperature": 0.0, "humidity": 0.0, "motion": 0}

def obtener_datos_wokwi_sincrono():
    """Captura datos de forma síncrona imprimiendo la carga útil recibida en la consola"""
    message_received = {"received": False, "payload": None}
    
    def on_message(client, userdata, message):
        try:
            cadena_texto = message.payload.decode('utf-8')
            # 🟢 PRINT DE CONSOLA: Muestra en bruto el texto tal cual llega del broker
            print(f"\n[MQTT INCOMING] Mensaje recibido en bruto en el tópico {message.topic}:")
            print(f"👉 {cadena_texto}")
            
            payload = json.loads(message.payload.decode())
            message_received["payload"] = payload
            message_received["received"] = True
        except Exception as e:
            message_received["payload"] = message.payload.decode()
            message_received["received"] = True
            
    try:
        # Generar un ID aleatorio único para esta consulta momentánea
        client_id = f"smarthouse_fetch_{int(time.time())}"
        
        # Sintaxis nativa y limpia para paho-mqtt==1.6.1
        client = mqtt.Client(client_id=client_id, clean_session=True)
        client.on_message = on_message
        
        client.connect(BROKER, PORT, 60)
        client.subscribe(TOPIC_RECEIVE)
        
        # Iniciar ciclo de escucha asíncrono temporal
        client.loop_start()
        
        # Ventana de espera controlada de hasta 1.5 segundos
        timeout = time.time() + 1.5
        while not message_received["received"] and time.time() < timeout:
            time.sleep(0.02)
            
        # Desconexión inmediata para liberar el canal e impedir saturación en Streamlit
        client.loop_stop()
        client.disconnect()
        
        if message_received["received"] and message_received["payload"]:
            raw_data = control_box["payload"]
            
            # Mapeo y conversión estricta a tipos numéricos nativos
            st.session_state.sensor_data = {
                "temperature": float(raw_data.get("temperature", 0.0)),
                "humidity": float(raw_data.get("humidity", 0.0)),
                "motion": int(raw_data.get("motion", 0))
            }
            
            # 🟢 PRINT DE CONSOLA: Muestra los datos ya procesados y listos para la interfaz
            print("[STREAMLIT SESIÓN] Variables mapeadas con éxito en st.session_state:")
            print(f"   ├─ Temp: {st.session_state.sensor_data['temperature']} °C")
            print(f"   ├─ Hum:  {st.session_state.sensor_data['humidity']} %")
            print(f"   └─ Mov:  {st.session_state.sensor_data['motion']}\n")
            return True
            
        print("⚠️ Advertencia: Se agotó el tiempo de espera (Timeout) sin recibir datos válidos de Wokwi.")
        return False
        
    except Exception as e:
        print(f"🚨 Error crítico de red en la función síncrona MQTT: {e}")
        return False

# Cliente persistente en sesión exclusivo para el ENVÍO de comandos hacia Wokwi (Paho 1.x)
if "client" not in st.session_state:
    try:
        client_id_send = f"smarthouse_send_{int(time.time())}"
        st.session_state.client = mqtt.Client(client_id=client_id_send, clean_session=True)
        st.session_state.client.connect(BROKER, PORT, 60)
        st.session_state.client.loop_start()
        print("🚀 Canal persistente de comandos MQTT inicializado con éxito (Paho 1.6.1).")
    except Exception as e:
        st.error(f"Error en pasarela de comandos de salida: {e}")

def asegurar_envio_mqtt(topic, payload_dict):
    """Verifica el estado de conexión del cliente antes de inyectar datos en la red"""
    try:
        # Si por fluctuaciones de red el cliente persistente se cae, se fuerza una reconexión inmediata
        if not st.session_state.client.is_connected():
            print("🔗 Detectada desconexión en el canal de salida. Reconectando...")
            st.session_state.client.reconnect()
            
        payload_json = json.dumps(payload_dict)
        st.session_state.client.publish(topic, payload_json)
        # 🟢 PRINT DE CONSOLA: Registra los datos salientes generados por botones, voz o IA
        print(f"[MQTT OUTGOING] Comando enviado a -> {topic}: {payload_json}")
    except Exception as e:
        print(f"❌ Fallo al transmitir comando MQTT de salida: {e}")

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
    st.title("🏠 SmartHouse Dashboard")
    st.write("Gestiona la recepción de datos y actuadores de la casa inteligente.")
    
    if st.button("🔄 Recibir datos del Wokwi", use_container_width=True):
        with st.spinner("Conectando al canal seguro y extrayendo telemetría..."):
            exito = obtener_datos_wokwi_sincrono()
            if exito:
                st.success("✅ Datos sincronizados correctamente")
            else:
                st.warning("⚠️ No se detectaron datos nuevos de la ESP32 en este ciclo (Verifica que Wokwi esté corriendo)")

    st.markdown("---")

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

    if b1.button("🚨 Activar Alarma", use_container_width=True):
        asegurar_envio_mqtt(TOPIC_SEND, {"Act1": "ON"})
        st.success("Alarma activada")

    if b2.button("🟢 Desactivar Alarma", use_container_width=True):
        asegurar_envio_mqtt(TOPIC_SEND, {"Act1": "OFF"})
        st.warning("Alarma desactivada")

# ==========================================
# VOZ + TEXTO
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

    if result:
        if "GET_TEXT" in result:
            voz = result.get("GET_TEXT").lower()
            st.success(f"Detectado: {voz}")

            if "activar" in voz or "encender" in voz or "prender" in voz:
                asegurar_envio_mqtt(TOPIC_SEND, {"VozAct": "ON"})
                st.success("Comando enviado: Encender LED Voz")

            elif "apagar" in voz or "desactivar" in voz:
                asegurar_envio_mqtt(TOPIC_SEND, {"VozAct": "OFF"})
                st.warning("Comando enviado: Apagar LED Voz")

    st.markdown("---")
    comando = st.text_input("Escribe un comando:").lower()

    if st.button("Enviar Texto"):
        if "activar" in comando or "encender" in comando:
            asegurar_envio_mqtt(TOPIC_SEND, {"VozAct": "ON"})
            st.success("Comando de texto enviado: LED Voz ON")

        elif "apagar" in comando or "desactivar" in comando:
            asegurar_envio_mqtt(TOPIC_SEND, {"VozAct": "OFF"})
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
            asegurar_envio_mqtt(TOPIC_SEND, {"door": "OPEN"})
            st.success("✅ Acceso permitido")

        elif clase == "Denegar acceso" and confidence > 0.80:
            asegurar_envio_mqtt(TOPIC_SEND, {"door": "DENY"})
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
