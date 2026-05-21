import streamlit as st
import paho.mqtt.client as mqtt
import json
from streamlit_autorefresh import st_autorefresh

# ==============================================================================
# 1. TRASFONDO: CONFIGURACIÓN, AUTO-REFRESCO Y MEMORIA (Invisible para el usuario)
# ==============================================================================

# Forzar a Streamlit a actualizar la pantalla internamente cada 2 segundos 
# para ir a buscar los datos que van llegando al session_state.
st_autorefresh(interval=2000, key="mqtt_data_refresh")

# Inicializar las variables globales dentro de la memoria interna si no existen
if "temp" not in st.session_state:
    st.session_state.temp = 0.0
if "hum" not in st.session_state:
    st.session_state.hum = 0.0
if "motion" not in st.session_state:
    st.session_state.motion = 0

# Función "Callback" que se activa sola cuando Wokwi publica datos en el broker
def on_message(client, userdata, message):
    try:
        # Decodificar el mensaje JSON enviado por la ESP32
        payload_str = message.payload.decode("utf-8")
        datos = json.loads(payload_str)
        
        # Guardar los datos en el estado global para que no se borren en cada recarga
        st.session_state.temp = float(datos.get("temperature", 0.0))
        st.session_state.hum = float(datos.get("humidity", 0.0))
        st.session_state.motion = int(datos.get("motion", 0))
    except Exception as e:
        print(f"Error procesando datos: {e}")

# Iniciar el cliente MQTT en segundo plano (loop_start hace que no se congele la web)
if "mqtt_client" not in st.session_state:
    broker_ip = "157.230.214.127"
    puerto = 1883
    
    nuevo_cliente = mqtt.Client()
    nuevo_cliente.on_message = on_message
    
    try:
        nuevo_cliente.connect(broker_ip, puerto, 60)
        nuevo_cliente.subscribe("smartcase/sensors")
        nuevo_cliente.loop_start() # Hilo asíncrono para escuchar en paralelo
        st.session_state.mqtt_client = nuevo_cliente
    except Exception as e:
        st.error(f"Error al conectar con el servidor de datos: {e}")


# ==============================================================================
# 2. SU INTERFAZ ORIGINAL (Mantengan aquí su propio diseño visual intacto)
# ==============================================================================

# --- EJEMPLO DE CÓMO SE LLAMAN LAS VARIABLES EN SU DISEÑO ---
# Reemplacen las métricas o textos de abajo por el código exacto de su interfaz, 
# asegurándose de usar 'st.session_state.temp', 'st.session_state.hum' y 
# 'st.session_state.motion' donde antes tenían sus variables estáticas.

st.title("Proyecto Smart House")
st.markdown("Monitoreo de variables meteorológicas y seguridad residencial.")
st.divider()

# Crear columnas para mostrar las tarjetas de los sensores
col1, col2, col3 = st.columns(3)

with col1:
    # Muestra el valor en vivo del DHT22 con un solo decimal
    st.metric(
        label="🌡️ Temperatura", 
        value=f"{st.session_state.temp:.1f} °C"
    )

with col2:
    # Muestra el valor en vivo de la humedad
    st.metric(
        label="💧 Humedad", 
        value=f"{st.session_state.hum:.1f} %"
    )

with col3:
    # Muestra un indicador dinámico dependiendo del estado del PIR
    st.write("**🚨 Sensor de Movimiento (PIR)**")
    if st.session_state.motion == 1:
        st.error("¡Actividad Detectada!")
    else:
        st.success("Zona Segura")
