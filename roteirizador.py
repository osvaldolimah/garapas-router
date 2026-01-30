import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np
from folium.features import DivIcon
import requests
import streamlit.components.v1 as components

# --- 1. FUNÇÕES DE INTELIGÊNCIA ---

def fast_haversine(lat1, lon1, lat2, lon2):
    p = np.pi/180
    a = 0.5 - np.cos((lat2-lat1)*p)/2 + np.cos(lat1*p) * np.cos(lat2*p) * (1-np.cos((lon2-lon1)*p))/2
    return 12742 * np.arcsin(np.sqrt(a))

def get_road_route_batch(points):
    if len(points) < 2: return points
    coords_str = ";".join([f"{p[1]},{p[0]}" for p in points])
    url = f"http://router.project-osrm.org/route/v1/driving/{coords_str}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            coords = r.json()['routes'][0]['geometry']['coordinates']
            return [[c[1], c[0]] for c in coords]
    except: pass
    return points

# --- 2. DESIGN SYSTEM TOUCH-OPTIMIZED ---

st.set_page_config(page_title="Garapas Router", layout="wide", page_icon="🚚")

st.markdown("""
    <style>
    .stApp { background-color: #f4f7f9; }
    
    /* Card Otimizado para Touch */
    .delivery-card { 
        border-radius: 20px; padding: 25px; margin-bottom: 15px; 
        background-color: white; border-left: 12px solid #FF4B4B;
        box-shadow: 0 6px 15px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
        touch-action: pan-y; /* Permite scroll vertical, mas captura o horizontal */
    }
    
    .next-target { border-left: 12px solid #007BFF !important; background-color: #f0f7ff !important; }
    
    /* Endereço Gigante para Tablet/Celular */
    .address-header { font-size: 26px !important; font-weight: 800 !important; color: #1a1a1a; line-height: 1.1; }
    
    /* Toggle Switch Estilo Android */
    .stCheckbox {
        transform: scale(1.8); /* Aumenta o tamanho do check para facilitar o toque */
        margin-top: 10px;
    }
    
    /* Esconder elementos desnecessários no mobile */
    @media (max-width: 600px) {
        .address-header { font-size: 20px !important; }
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🚚 Garapas Router | Touch Edition")

# --- 3. INICIALIZAÇÃO ---

if 'df_final' not in st.session_state: st.session_state['df_final'] = None
if 'road_path' not in st.session_state: st.session_state['road_path'] = []
if 'entregues' not in st.session_state: st.session_state['entregues'] = set()
if 'custom_sequences' not in st.session_state: st.session_state['custom_sequences'] = {}
if 'versao_lista' not in st.session_state: st.session_state['versao_lista'] = 0

# --- 4. OTIMIZAÇÃO ---

with st.expander("📂 Importar Planilha", expanded=(st.session_state['df_final'] is None)):
    uploaded_file = st.file_uploader("", type=['xlsx'])
    if uploaded_file:
        df_raw = pd.read_excel(uploaded_file)
        df_raw.columns = df_raw.columns.str.strip().str.upper()
        df_clean = df_raw.dropna(subset=['LATITUDE', 'LONGITUDE'])

        if st.button("🚀 GERAR ROTA INTELIGENTE", use_container_width=True):
            with st.spinner("Calculando..."):
                df_temp = df_clean.copy().reset_index()
                rota = []
                p_atual = df_temp.iloc[0]
                rota.append(p_atual)
                df_temp = df_temp.drop(df_temp.index[0])
                while not df_temp.empty:
                    dists = fast_haversine(p_atual['LATITUDE'], p_atual['LONGITUDE'], df_temp['LATITUDE'].values, df_temp['LONGITUDE'].values)
                    idx = np.argmin(dists)
                    p_atual = df_temp.iloc[idx]
                    rota.append(p_atual)
                    df_temp = df_temp.drop(df_temp.index[idx])
                
                final_df = pd.DataFrame(rota).reset_index(drop=True)
                final_df['ORDEM_PARADA'] = range(1, len(final_df) + 1)
                st.session_state['df_final'] = final_df
                
            with st.spinner("Desenhando ruas..."):
                st.session_state['road_path'] = get_road_route_batch(final_df[['LATITUDE', 'LONGITUDE']].values.tolist())
            
            st.session_state['entregues'] = set()
            st.session_state['versao_lista'] += 1
            st.rerun()

# --- 5. INTERFACE OPERACIONAL ---

if st.session_state['df_final'] is not None:
    df_res = st.session_state['df_final']
    entregues_list = st.session_state['entregues']
    restantes_indices = [i for i in range(len(df_res)) if i not in entregues_list]

    # Painel de Métricas
    km = 0.0
    for k in range(len(restantes_indices) - 1):
        p1, p2 = df_res.iloc[restantes_indices[k]], df_res.iloc[restantes_indices[k+1]]
        km += fast_haversine(p1['LATITUDE'], p1['LONGITUDE'], p2['LATITUDE'], p2['LONGITUDE'])
    
    c1, c2, c3 = st.columns([1, 1, 1.2])
    c1.metric("📦 Faltam", len(restantes_indices))
    c2.metric("🛤️ KM Rodoviário", f"{km * 1.3:.1f} km")
    if c3.button("🗑️ LIMPAR FEITAS", use_container_width=True):
        if restantes_indices:
            novo_df = df_res.iloc[restantes_indices].reset_index(drop=True)
            novo_df['ORDEM_PARADA'] = range(1, len(novo_df) + 1)
            st.session_state['df_final'] = novo_df
            st.session_state['entregues'] = set()
            st.session_state['road_path'] = get_road_route_batch(novo_df[['LATITUDE', 'LONGITUDE']].values.tolist())
            st.session_state['versao_lista'] += 1
            st.rerun()

    # MAPA
    m = folium.Map(location=[df_res['LATITUDE'].mean(), df_res['LONGITUDE'].mean()], zoom_start=13, tiles="cartodbpositron")
    if st.session_state['road_path']:
        folium.PolyLine(st.session_state['road_path'], color="#007BFF", weight=6, opacity=0.7).add_to(m)

    for i, row in df_res.iterrows():
        foi = i in entregues_list
        cor = "#28A745" if foi else ("#007BFF" if (restantes_indices and i == restantes_indices[0]) else "#FF4B4B")
        id_p = int(row['ORDEM_PARADA'])
        icon_html = f'''<div style="background-color: {cor}; border: 3px solid white; border-radius: 50%; width: 34px; height: 34px; 
                        display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; 
                        font-size: 16px; box-shadow: 0 2px 6px rgba(0,0,0,0.4);">{id_p}</div>'''
        folium.Marker(location=[row['LATITUDE'], row['LONGITUDE']], icon=DivIcon(icon_size=(34,34), icon_anchor=(17,17), html=icon_html)).add_to(m)
    
    st_folium(m, width=1400, height=450, key=f"map_v{st.session_state['versao_lista']}")

    # LISTA COM "FEELING" DE SWIPE
    st.markdown("---")
    busca = st.text_input("🔍 FILTRAR RUA OU SEQUENCE").upper()

    for i, row in df_res.iterrows():
        rua, bairro = str(row.get('DESTINATION ADDRESS', '---')), str(row.get('BAIRRO', ''))
        seq_v = st.session_state['custom_sequences'].get(i, str(row.get('SEQUENCE', '---')))
        id_p = int(row['ORDEM_PARADA'])
        if busca and (busca not in rua.upper() and busca not in bairro.upper() and busca not in seq_v.upper()): continue
        
        entregue = i in entregues_list
        is_next = (restantes_indices and i == restantes_indices[0])
        
        # Estilização Dinâmica
        card_class = "next-target" if is_next else ""
        if entregue: card_class = ""

        with st.container():
            st.markdown(f'''
                <div class="delivery-card {card_class}">
                    <div class="address-header">{"✅ " if entregue else ""}{id_p}ª - {rua}</div>
                    <div style="color: #666; font-weight: 500;">Bairro: {bairro}</div>
                </div>
            ''', unsafe_allow_html=True)
            
            # Controles de Ação Aumentados
            col_check, col_seq, col_nav = st.columns([1, 2, 2])
            with col_check:
                # O Checkbox aqui atua como o gatilho do "Swipe"
                if st.checkbox("CONCLUÍDO", key=f"c_{i}_{st.session_state['versao_lista']}", value=entregue):
                    if i not in st.session_state['entregues']:
                        st.session_state['entregues'].add(i); st.rerun()
                elif entregue:
                    st.session_state['entregues'].remove(i); st.rerun()
            
            with col_seq:
                st.session_state['custom_sequences'][i] = st.text_input("ID PACOTE:", value=seq_v, key=f"s_{i}_{st.session_state['versao_lista']}")
            
            with col_nav:
                w_link = f"https://waze.com/ul?ll={row['LATITUDE']},{row['LONGITUDE']}&navigate=yes"
                st.link_button("🚗 ABRIR NO WAZE", w_link, use_container_width=True, disabled=entregue)
            st.markdown("---")
