import streamlit as st
from supabase import create_client, Client
import random

# Configuración de la página
st.set_page_config(page_title="Tiroteo de Alemán", page_icon="🔫", layout="centered")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    div.block-container {padding-top: 2rem; max-width: 700px;}
    p {margin-bottom: 0.5rem !important;}
    .badge-container {display: flex; gap: 8px; margin-bottom: 15px;}
    .badge {padding: 4px 12px; border-radius: 15px; font-size: 12px; font-weight: bold; color: white;}
    </style>
    """, unsafe_allow_html=True)

# Conexión a Supabase
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_supabase()

GENERO_COLORES = {
    "Masculino": "#3b82f6",
    "Femenino": "#ec4899",
    "Neutro": "#10b981",
    "Plural": "#8b5cf6"
}

# Barra lateral con filtros
st.sidebar.title("🎯 Configurar Tiroteo")

filtro_dificultad = st.sidebar.selectbox(
    "Nivel de Dificultad:",
    ["Todos", "Básico", "Intermedio", "Avanzado"]
)

filtro_caso = st.sidebar.selectbox(
    "Caso Gramatical:",
    ["Todos", "Nominativo", "Acusativo", "Dativo", "Genitivo"]
)

if "prev_diff" not in st.session_state:
    st.session_state.prev_diff = filtro_dificultad
if "prev_case" not in st.session_state:
    st.session_state.prev_case = filtro_caso

if st.session_state.prev_diff != filtro_dificultad or st.session_state.prev_case != filtro_caso:
    st.session_state.prev_diff = filtro_dificultad
    st.session_state.prev_case = filtro_caso
    st.session_state.ronda_num = 1
    st.session_state.current_card = None

# Inicializar estados de la sesión
if "current_card" not in st.session_state:
    st.session_state.current_card = None
if "show_solution" not in st.session_state:
    st.session_state.show_solution = False
if "ronda_num" not in st.session_state:
    st.session_state.ronda_num = 1

def fetch_next_card():
    query = supabase.table("german_flashcards").select("*")
    if filtro_dificultad != "Todos":
        query = query.eq("difficulty", filtro_dificultad)
    if filtro_caso != "Todos":
        query = query.eq("case", filtro_caso)
    response = query.execute()
    if response.data and len(response.data) > 0:
        st.session_state.current_card = random.choice(response.data)
        st.session_state.show_solution = False
    else:
        st.session_state.current_card = None

if st.session_state.current_card is None:
    fetch_next_card()

# Interfaz visual principal
if st.session_state.current_card:
    card = st.session_state.current_card
    color_genero = GENERO_COLORES.get(card["gender"], "#6b7280")
    
    st.markdown(f"### 🔫 RONDA {st.session_state.ronda_num} — Palabra: **{card['word']}**")
    
    st.markdown(f"""
        <div class="badge-container">
            <span class="badge" style="background-color: {color_genero};">{card['gender'].upper()}</span>
            <span class="badge" style="background-color: #4b5563;">{card['case'].upper()}</span>
            <span class="badge" style="background-color: #1f2937;">{card['difficulty'].upper()}</span>
        </div>
    """, unsafe_allow_html=True)
    
    if card.get("subcategory"):
        st.markdown(f"**Categoría:** *{card['subcategory']}*")
    st.markdown(f"◦ &nbsp;&nbsp; *Situación:* {card['situation']}")
    
    st.markdown(f'<div style="font-size: 24px; font-weight: bold; margin-left: 10px; margin-top: 10px; margin-bottom: 20px; border-left: 4px solid {color_genero}; padding-left: 15px;">"{card["spanish_phrase"]}"</div>', unsafe_allow_html=True)
    
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

    if st.session_state.show_solution:
        st.markdown("---")
        st.markdown(f"## 🔊 DE: `{card['german_solution']}`")
        
        # Leemos la explicación (pruebe minúscula o mayúscula por seguridad)
        explicacion_texto = card.get('explanation') or card.get('Explanation')
        if explicacion_texto:
            st.info(f"💡 **Explicación:** {explicacion_texto}")
            
        # Leemos el tip de gramática solo si no es null o vacío
        tip_texto = card.get('grammar_tip') or card.get('Grammar_tip')
        if tip_texto and str(tip_texto).strip().lower() != 'none':
            st.warning(f"🔑 **Grammar Tip:** {tip_texto}")
else:
    st.error("No hay tarjetas que coincidan con los filtros seleccionados en la barra lateral.")
    if st.button("🔄 Recargar / Resetear Filtros"):
        fetch_next_card()
        st.rerun()
