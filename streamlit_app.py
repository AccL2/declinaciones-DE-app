import streamlit as st
from supabase import create_client, Client
import random

# 1. Configuración de la página e inyección de estilos limpios
st.set_page_config(page_title="Tiroteo de Alemán", page_icon="🔫", layout="centered")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    div.block-container {padding-top: 2rem; max-width: 700px;}
    p {margin-bottom: 0.5rem !important;}
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

# 5. INTERFAZ VISUAL: CALCO DE TU FORMATO DE CHAT
if st.session_state.current_card:
    card = st.session_state.current_card
    
    # Línea 1: El encabezado con la palabra
    st.markdown(f"🔫 **TARJETA: {card['word']} ({card['gender']})**")
    
    # Línea 2 y 3: Situación y Frase en español (Línea a línea, pegado)
    st.markdown(f"◦ &nbsp;&nbsp; *Situación:* {card['situation']}")
    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp; **\"{card['spanish_phrase']}\"**")
    
    # Pequeño espacio para la botonera
    st.markdown("")
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("👁️ Revelar", use_container_width=True):
            st.session_state.show_solution = True
            st.rerun()
    with col2:
        if st.button("🚀 Siguiente", type="primary", use_container_width=True):
            fetch_next_card()
            st.rerun()

    # BLOQUE DE REVELACIÓN: Tu formato exacto línea a línea
    if st.session_state.show_solution:
        st.markdown("") # Separador sutil
        st.markdown(f"🔊 **DE:** `{card['german_solution']}`")
        st.markdown(f"({card['explanation']})")

else:
    st.error("El cargador está vacío. Revisa tu tabla en Supabase.")
    if st.button("🔄 Recargar"):
        fetch_next_card()
        st.rerun()
