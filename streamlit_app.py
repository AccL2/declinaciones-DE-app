import streamlit as st
from supabase import create_client, Client
import random

# 1. Configuración de la página
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
if "ronda_num" not in st.session_state:
    st.session_state.ronda_num = 1

# 4. Lógica de carga aleatoria limpia
def fetch_next_card():
    response = supabase.table("german_flashcards").select("*").execute()
    if response.data and len(response.data) > 0:
        st.session_state.current_card = random.choice(response.data)
        # RESET OBLIGATORIO: Apagamos la solución para la nueva tarjeta
        st.session_state.show_solution = False
    else:
        st.session_state.current_card = None

if st.session_state.current_card is None:
    fetch_next_card()

# 5. INTERFAZ VISUAL MAQUETADA LÍNEA A LÍNEA
if st.session_state.current_card:
    card = st.session_state.current_card
    
    # Línea 1: Limpio, sin textos raros de géneros. Solo la palabra tal cual venga en la BD
    st.markdown(f"🔫 **RONDA {st.session_state.ronda_num} — Tarjeta: {card['word']}**")
    
    # Línea 2: Situación
    st.markdown(f"◦ &nbsp;&nbsp; *Situación:* {card['situation']}")
    
    # Línea 3: Frase en castellano MÁS GRANDE (Usando h3 en markdown)
    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp; ### **\"{card['spanish_phrase']}\"**")
    
    # Botonera
    st.markdown("")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("👁️ Revelar", use_container_width=True):
            st.session_state.show_solution = True
            st.rerun()
    with col2:
        if st.button("🚀 Siguiente", type="primary", use_container_width=True):
            st.session_state.ronda_num += 1
            fetch_next_card()
            st.rerun()

    # BLOQUE DE REVELACIÓN (Solo si se ha pulsado Revelar)
    if st.session_state.show_solution:
        st.markdown("") 
        # Solución alemana MÁS GRANDE e impactante
        st.markdown(f"## 🔊 **DE:** `{card['german_solution']}`")
        # Explicación justo abajo
        st.markdown(f"({card['explanation']})")

else:
    st.error("El cargador está vacío. Revisa tu tabla en Supabase.")
    if st.button("🔄 Recargar"):
        fetch_next_card()
        st.rerun()
