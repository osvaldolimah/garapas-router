import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np
from folium.features import DivIcon
import requests

# --- 1. INTELIGÊNCIA DE ROTA ---

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

# --- 2. DESIGN SYSTEM RESPONSIVO (UX Sênior) ---

st.set_page_config(page_title="Garapas Router", layout="wide", page_icon="🚚")

st.markdown("""
    <style>
    /* Base e Fundo */
    .stApp { background-color: #f8f9fa; }
    
    /* Card de Entrega Refinado */
    .delivery-card { 
        border-radius: 12px; 
        padding: 16px; 
        margin-bottom: 8px; 
        background-color: white; 
        border-left: 8px solid #FF4B4B;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    .next-target { border-left: 8px solid #007BFF !important; background-color: #f0f7ff !important; }
    
    /* Tipografia Ajustada para não cortar */
    .address-header { 
        font-size: 20px !important; 
        font-weight: 700 !important; 
        color: #212529; 
        line-height: 1.2;
        margin-bottom: 5px;
    }
    .bairro-label { font-size: 15px; color: #6c757d; margin-bottom: 12px; }
    
    /* Input de Ordem (Sem cortes) */
    div[data-baseweb="input"] {
        height: 45px !important;
    }
    .stTextInput input {
        background-color: #212529 !important; 
        color: #39FF14 !important;
        font-family: 'Roboto Mono', monospace; 
        font-size: 18px !important; 
        text-align: center;
        padding: 5px !important;
        border-radius: 8px !important;
    }

    /* Botões Operacionais */
    .stButton button {
        height: 45px !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        text-transform: uppercase;
    }

    /* Ajuste para telas muito pequenas */
    @media (max-width: 480px) {
        .address-header { font-size: 18px !important; }
        .delivery-card { padding: 12px; }
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🚚 Garapas Router")

# --- 3. MEMÓRIA ---

if 'df_final' not in st.session_state: st.session_state['df_final'] = None
if 'road_path' not in st.session_state: st.session_state['road_path'] = []
if 'entregues' not in st.session_state: st.session_state['entregues'] = set()
if 'custom_sequences' not in st.session_state: st.session_state['custom_sequences'] = {}
if 'versao_lista' not in st.session_state: st.session_state['versao_lista'] = 0

# --- 4. OTIMIZAÇÃO ---

with st.expander("📂 Carregar Planilha", expanded=(st.session_state['df_final'] is None)):
    uploaded_file = st.file_uploader("", type=['xlsx'])
    if uploaded_file:
        df_raw = pd.read_excel(uploaded_file)
        df_raw.columns = df_raw.columns.str.strip().str.upper()
        df_clean = df_raw.dropna(subset=['LATITUDE', 'LONGITUDE'])

        if st.button("🚀 INICIAR ROTA", use_container_width=True):
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
            
            with st.spinner("Desenhando mapa..."):
                st.session_state['road_path'] = get_road_route_batch(final_df[['LATITUDE', 'LONGITUDE']].values.tolist())
            
            st.session_state['entregues'] = set()
            st.session_state['versao_lista'] += 1
            st.rerun()

# --- 5. INTERFACE ---

if st.session_state['df_final'] is not None:
    df_res = st.session_state['df_final']
    entregues_list = st.session_state['entregues']
    restantes = [i for i in range(len(df_res)) if i not in entregues_list]

    # Métricas
    km_vovo = 0.0
    for k in range(len(restantes) - 1):
        p1 = df_res.iloc[restantes[k]]
        p2 = df_res.iloc[restantes[k+1]]
        km_vovo += fast_haversine(p1['LATITUDE'], p1['LONGITUDE'], p2['LATITUDE'], p2['LONGITUDE'])
    
    m1, m2, m3 = st.columns([1, 1, 1])
    m1.metric("📦 Faltam", len(restantes))
    m2.metric("🛤️ KM (Est.)", f"{km_vovo * 1.3:.1f}")
    if m3.button("🗑️ LIMPAR", use_container_width=True):
        if restantes:
            novo_df = df_res.iloc[restantes].reset_index(drop=True)
            novo_df['ORDEM_PARADA'] = range(1, len(novo_df) + 1)
            st.session_state['df_final'] = novo_df
            st.session_state['entregues'] = set()
            with st.spinner("Atualizando..."):
                st.session_state['road_path'] = get_road_route_batch(novo_df[['LATITUDE', 'LONGITUDE']].values.tolist())
            st.session_state['versao_lista'] += 1
            st.rerun()

    # Mapa
    m = folium.Map(location=[df_res['LATITUDE'].mean(), df_res['LONGITUDE'].mean()], zoom_start=13, tiles="cartodbpositron")
    if st.session_state['road_path']:
        folium.PolyLine(st.session_state['road_path'], color="#007BFF", weight=5, opacity=0.7).add_to(m)

    for i, row in df_res.iterrows():
        foi = i in entregues_list
        cor = "#28A745" if foi else ("#007BFF" if (restantes and i == restantes[0]) else "#FF4B4B")
        icon_html = f'''<div style="background-color: {cor}; border: 2px solid white; border-radius: 50%; width: 28px; height: 28px; 
                        display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; 
                        font-size: 12px;">{int(row['ORDEM_PARADA'])}</div>'''
        folium.Marker(location=[row['LATITUDE'], row['LONGITUDE']], icon=DivIcon(icon_size=(28,28), icon_anchor=(14,14), html=icon_html)).add_to(m)
    st_folium(m, width=1400, height=400, key=f"map_v{st.session_state['versao_lista']}")

    st.markdown("---")

    # Lista de Entregas Otimizada
    for i, row in df_res.iterrows():
        rua, bairro = str(row.get('DESTINATION ADDRESS', '---')), str(row.get('BAIRRO', ''))
        seq_v = st.session_state['custom_sequences'].get(i, str(row.get('SEQUENCE', '---')))
        id_p = int(row['ORDEM_PARADA'])
        
        entregue = i in entregues_list
        is_next = (restantes and i == restantes[0])
        card_class = "next-target" if is_next else ""

        with st.container():
            st.markdown(f'''
                <div class="delivery-card {card_class}">
                    <div class="address-header">{"✅ " if entregue else ""}{id_p}ª - {rua}</div>
                    <div class="bairro-label">{bairro}</div>
                </div>
            ''', unsafe_allow_html=True)
            
            # Layout de controles: Botões em cima, Input embaixo para ganhar largura
            c1, c2 = st.columns([1, 1])
            with c1:
                if not entregue:
                    if st.button("✅ FEITO", key=f"done_{i}_{st.session_state['versao_lista']}", use_container_width=True):
                        st.session_state['entregues'].add(i); st.rerun()
                else:
                    if st.button("🔄 VOLTAR", key=f"undo_{i}_{st.session_state['versao_lista']}", use_container_width=True):
                        st.session_state['entregues'].remove(i); st.rerun()
            with c2:
                st.link_button("🚗 WAZE", f"https://waze.com/ul?ll={row['LATITUDE']},{row['LONGITUDE']}&navigate=yes", use_container_width=True, disabled=entregue)
            
            # Input de Ordem ocupando toda a largura para não cortar
            st.session_state['custom_sequences'][i] = st.text_input("ORDEM (MANIFESTO):", value=seq_v, key=f"s_{i}_{st.session_state['versao_lista']}")
            
            st.markdown("---")

