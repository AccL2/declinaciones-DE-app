import streamlit as st
from supabase import create_client, Client
import random

# 1. Configuración de la página
st.set_page_config(page_title="Tiroteo de Alemán", page_icon="🔫", layout="centered")

# Ocultar menús de Streamlit para máxima inmersión limpia
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    div.block-container {padding-top: 2rem;}
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

# 4. Lógica de carga aleatoria
def fetch_next_card():
    response = supabase.table("german_flashcards").select("*").execute()
    if response.data and len(response.data) > 0:
        st.session_state.current_card = random.choice(response.data)
        st.session_state.show_solution = False
    else:
        st.session_state.current_card = None

if st.session_state.current_card is None:
    fetch_next_card()

# 5. INTERFAZ VISUAL ESTILO "RONDA DE TIRO" (Tu captura de pantalla)
st.title("⚡ Sistema de Tiroteo Alemán")
st.markdown("---")

if st.session_state.current_card:
    card = st.session_state.current_card
    
    # Cabecera estilo Ronda (Ej: 🔫 RONDA X — Tarjeta: Kaffee)
    st.markdown(f"### 🔫 TARJETA EN CURSO: `{card['word']}` ({card['gender']})")
    
    # Sección Situación con viñeta limpia
    st.markdown(f"""
    * &nbsp;&nbsp; ***Situación:*** {card['situation']}
      **"{card['spanish_phrase']}"**
    """)
    
    st.info(f"💡 Estado mental / Modo:")
    st.markdown("---")
    
    # Botonera de control
    col1, col2 = st.columns(2)
    with col1:
        if st.button("👁️ Revelar la Bala", use_container_width=True):
            st.session_state.show_solution = True
            st.rerun()
            
    with col2:
        if st.button("🚀 Siguiente Bala", type="primary", use_container_width=True):
            fetch_next_card()
            st.rerun()

    # BLOQUE DE SOLUCIÓN: Copia exacta del formato de tu imagen
    if st.session_state.show_solution:
        st.markdown(" ") # Espaciador
        # La bala en alemán (Formato código en gris destacado)
        st.markdown(f"### 🔊 **La bala en alemán:** `{card['german_solution']}`")
        # El fogonazo mental explicativo en cursiva abajo
        st.markdown(f"*{card['explanation']}*")

else:
    st.error("El cargador está vacío. Revisa tu tabla en Supabase.")
    if st.button("🔄 Recargar"):
        fetch_next_card()
        st.rerun()
