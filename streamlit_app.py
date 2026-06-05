import streamlit as st
from supabase import create_client, Client
from datetime import datetime

# 1. Configuración de la página ultra-limpia
st.set_page_config(page_title="Tiroteo de Alemán", page_icon="🔫", layout="centered")

# Ocultar menús molestos de Streamlit para máxima inmersión
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# 2. Conexión segura a Supabase usando tus Secrets
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_supabase()

# 3. Inicializar variables de sesión de Streamlit (Estado de la app)
if "current_card" not in st.session_state:
    st.session_state.current_card = None
if "show_solution" not in st.session_state:
    st.session_state.show_solution = False

# 4. Función lógica: Traer la tarjeta más antigua del bucle
def fetch_next_card():
    # Buscamos la fila que se haya visto hace más tiempo (last_viewed más antiguo o NULL)
    response = supabase.table("german_flashcards") \
        .select("*") \
        .order("last_viewed", nulls_first=True, ascending=True) \
        .limit(1) \
        .execute()
    
    if response.data:
        st.session_state.current_card = response.data[0]
        st.session_state.show_solution = False
    else:
        st.session_state.current_card = None

# Función para registrar que ya vimos la palabra justo ahora
def mark_card_as_viewed(card_id):
    now = datetime.utcnow().isoformat()
    supabase.table("german_flashcards") \
        .update({"last_viewed": now}) \
        .eq("id", card_id) \
        .execute()

# Cargar la primera tarjeta si la sesión está vacía
if st.session_state.current_card is None:
    fetch_next_card()

# 5. INTERFAZ VISUAL (El diseño del tiroteo)
st.title("🔫 Tiroteo de Alemán")
st.subheader("Entrenamiento de flujo rápido")
st.markdown("---")

if st.session_state.current_card:
    card = st.session_state.current_card
    
    # Mostrar datos del estímulo
    st.markdown(f"### **Palabra objetivo:** `{card['word']}` ({card['gender']})")
    st.info(f"💡 Estado mental / Modo:")
    
    # El reto en español en grande
    st.markdown("### **Tu situación en español:**")
    st.warning(f"👉 **\"{card['spanish_phrase']}\"**")
    
    st.markdown("---")
    
    # Botonera de interacción (Sin rellenar huecos, solo boca y ojos)
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("👁️ Mostrar Chuleta / Solución", use_container_width=True):
            st.session_state.show_solution = True
            st.rerun()
            
    with col2:
        if st.button("🚀 Siguiente Bala", type="primary", use_container_width=True):
            # 1. Guardamos el timestamp en la base de datos para que pase al final de la cola
            mark_card_as_viewed(card['id'])
            # 2. Saltamos a la siguiente tarjeta
            fetch_next_card()
            st.rerun()

    # Si el usuario pide la chuleta, se despliega abajo sin ruido
    if st.session_state.show_solution:
        st.success(f"🔊 **Solución en alemán:** `{card['german_solution']}`")
        st.caption(f"🧠 Fogonazo mental:")

else:
    st.error("La base de datos está vacía. ¡Necesitas meter munición (filas) en tu tabla de Supabase!")
    if st.button("🔄 Intentar recargar"):
        fetch_next_card()
        st.rerun()
