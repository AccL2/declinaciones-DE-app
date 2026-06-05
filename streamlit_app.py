import streamlit as st
from supabase import create_client, Client
import random

# 1. Configuración de la página
st.set_page_config(page_title="Tiroteo de Alemán", page_icon="🔫", layout="centered")

# Ocultar menús de Streamlit
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# 2. Conexión a Supabase
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_supabase()

# 3. Inicializar el estado de la sesión
if "current_card" not in st.session_state:
    st.session_state.current_card = None
if "show_solution" not in st.session_state:
    st.session_state.show_solution = False

# 4. NUEVA LÓGICA: Traer tarjetas y elegir una al azar de forma segura
def fetch_next_card():
    # Nos traemos las filas de la tabla de forma plana y directa, sin ordenar
    response = supabase.table("german_flashcards").select("*").execute()
    
    if response.data and len(response.data) > 0:
        # Si hay tarjetas, elegimos una al azar del cargador
        st.session_state.current_card = random.choice(response.data)
        st.session_state.show_solution = False
    else:
        st.session_state.current_card = None

# Cargar la primera tarjeta al arrancar
if st.session_state.current_card is None:
    fetch_next_card()

# 5. INTERFAZ VISUAL
st.title("🔫 Tiroteo de Alemán")
st.subheader("Entrenamiento de flujo rápido")
st.markdown("---")

if st.session_state.current_card:
    card = st.session_state.current_card
    
    # Mostrar datos
    st.markdown(f"### **Palabra objetivo:** `{card['word']}` ({card['gender']})")
    st.info(f"💡 Estado mental / Modo:")
    
    # El reto en español
    st.markdown("### **Tu situación en español:**")
    st.warning(f"👉 **\"{card['spanish_phrase']}\"**")
    
    st.markdown("---")
    
    # Botonera
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("👁️ Mostrar Chuleta / Solución", use_container_width=True):
            st.session_state.show_solution = True
            st.rerun()
            
    with col2:
        if st.button("🚀 Siguiente Bala", type="primary", use_container_width=True):
            fetch_next_card()
            st.rerun()

    # Desplegar solución
    if st.session_state.show_solution:
        st.success(f"🔊 **Solución en alemán:** `{card['german_solution']}`")
        st.markdown(f"🧠 Fogonazo mental:")

else:
    st.error("La base de datos está vacía o no se encuentra la tabla. ¡Asegúrate de haber metido filas en Supabase!")
    if st.button("🔄 Intentar recargar"):
        fetch_next_card()
        st.rerun()
