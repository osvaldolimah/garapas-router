import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np
from folium.features import DivIcon
import requests

# --- 1. FUNÇÕES TÉCNICAS ---

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

# --- 2. DESIGN SYSTEM MINIMALISTA ---

st.set_page_config(page_title="Garapas Router", layout="wide", page_icon="🚚")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    
    /* Remove espaços e cabeçalhos inúteis */
    .block-container { padding-top: 0rem !important; padding-bottom: 0rem !important; }
    header, footer, #MainMenu { visibility: hidden; }

    /* Métricas e Botões Compactos */
    [data-testid="stMetricValue"] { font-size: 18px !important; font-weight: 700 !important; }
    [data-testid="stMetricLabel"] { font-size: 11px !important; }
    
    .stButton button {
        height: 35px !important;
        font-size: 12px !important;
        border-radius: 6px !important;
        padding: 0px 8px !important;
    }

    /* Cards Slim */
    .delivery-card { 
        border-radius: 8px; padding: 10px 12px; margin-bottom: 6px; 
        background-color: white; border-left: 6px solid #FF4B4B;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .next-target { border-left: 6px solid #007BFF !important; background-color: #f8fbff !important; }
    .address-header { font-size: 14px !important; font-weight: 600 !important; color: #333; }
    
    /* Input Ordem Discreto */
    div[data-baseweb="input"] { height: 32px !important; }
    .stTextInput input {
        background-color: #f1f3f5 !important; color: #2ecc71 !important;
        font-size: 13px !important; text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ESTADO DA SESSÃO ---

if 'df_final' not in st.session_state: st.session_state['df_final'] = None
if 'road_path' not in st.session_state: st.session_state['road_path'] = []
if 'entregues' not in st.session_state: st.session_state['entregues'] = set()
if 'custom_sequences' not in st.session_state: st.session_state['custom_sequences'] = {}
if 'versao_lista' not in st.session_state: st.session_state['versao_lista'] = 0

# --- 4. CARREGAMENTO ---

if st.session_state['df_final'] is None:
    st.subheader("🚚 Garapas Router")
    uploaded_file = st.file_uploader("", type=['xlsx'])
    if uploaded_file:
        df_raw = pd.read_excel(uploaded_file)
        df_raw.columns = df_raw.columns.str.strip().str.upper()
        df_clean = df_raw.dropna(subset=['LATITUDE', 'LONGITUDE'])
        if st.button("🚀 Otimizar Rota", use_container_width=True):
            df_temp = df_clean.copy().reset_index()
            rota = []
            p_atual = df_temp.iloc[0]; rota.append(p_atual); df_temp = df_temp.drop(df_temp.index[0])
            while not df_temp.empty:
                dists = fast_haversine(p_atual['LATITUDE'], p_atual['LONGITUDE'], df_temp['LATITUDE'].values, df_temp['LONGITUDE'].values)
                idx = np.argmin(dists); p_atual = df_temp.iloc[idx]; rota.append(p_atual); df_temp = df_temp.drop(df_temp.index[idx])
            final_df = pd.DataFrame(rota).reset_index(drop=True)
            final_df['ORDEM_PARADA'] = range(1, len(final_df) + 1)
            st.session_state['df_final'] = final_df
            with st.spinner("Traçando..."):
                st.session_state['road_path'] = get_road_route_batch(final_df[['LATITUDE', 'LONGITUDE']].values.tolist())
            st.rerun()

# --- 5. INTERFACE OPERACIONAL ---

if st.session_state['df_final'] is not None:
    df_res = st.session_state['df_final']
    entregues_list = st.session_state['entregues']
    restantes = [i for i in range(len(df_res)) if i not in entregues_list]

    # --- MAPA NO TOPO ABSOLUTO ---
    m = folium.Map(tiles="cartodbpositron")
    if st.session_state['road_path']:
        folium.PolyLine(st.session_state['road_path'], color="#007BFF", weight=4, opacity=0.7).add_to(m)

    all_coords = []
    for i, row in df_res.iterrows():
        foi = i in entregues_list
        cor = "#2ecc71" if foi else ("#007BFF" if (restantes and i == restantes[0]) else "#e74c3c")
        loc = [row['LATITUDE'], row['LONGITUDE']]; all_coords.append(loc)
        icon_html = f'''<div style="background-color: {cor}; border: 1px solid white; border-radius: 50%; width: 20px; height: 20px; 
                        display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; 
                        font-size: 8px;">{int(row['ORDEM_PARADA'])}</div>'''
        folium.Marker(location=loc, icon=DivIcon(icon_size=(20,20), icon_anchor=(10,10), html=icon_html)).add_to(m)
    
    if all_coords: m.fit_bounds(all_coords, padding=(30, 30))
    st_folium(m, width=None, height=300, key=f"map_v{st.session_state['versao_lista']}", use_container_width=True)

    # --- MÉTRICAS ABAIXO DO MAPA ---
    c1, c2, c3 = st.columns([1, 1, 1.2])
    km_vovo = 0.0
    for k in range(len(restantes) - 1):
        p1, p2 = df_res.iloc[restantes[k]], df_res.iloc[restantes[k+1]]
        km_vovo += fast_haversine(p1['LATITUDE'], p1['LONGITUDE'], p2['LATITUDE'], p2['LONGITUDE'])
    
    c1.metric("📦 Restam", f"{len(restantes)}")
    c2.metric("🛤️ KM", f"{km_vovo * 1.3:.1f}")
    if c3.button("🗑️ Limpar", use_container_width=True):
        if restantes:
            novo_df = df_res.iloc[restantes].reset_index(drop=True)
            novo_df['ORDEM_PARADA'] = range(1, len(novo_df) + 1)
            st.session_state['df_final'] = novo_df; st.session_state['entregues'] = set()
            with st.spinner("Atualizando..."):
                st.session_state['road_path'] = get_road_route_batch(novo_df[['LATITUDE', 'LONGITUDE']].values.tolist())
            st.rerun()

    # --- LISTA COM SCROLL INTERNO ---
    with st.container(height=450):
        for i, row in df_res.iterrows():
            rua, bairro = str(row.get('DESTINATION ADDRESS', '---')), str(row.get('BAIRRO', ''))
            seq_v = st.session_state['custom_sequences'].get(i, str(row.get('SEQUENCE', '---')))
            id_p = int(row['ORDEM_PARADA'])
            entregue = i in entregues_list
            is_next = (restantes and i == restantes[0])
            card_class = "next-target" if is_next else ""

            st.markdown(f'''
                <div class="delivery-card {card_class}">
                    <div class="address-header">{id_p}ª - {rua}</div>
                    <div style="font-size: 11px; color: #888;">{bairro}</div>
                </div>
            ''', unsafe_allow_html=True)
            
            ca, cb, cc = st.columns([1, 1, 1.2])
            with ca:
                label = "✅" if not entregue else "🔄"
                if st.button(label, key=f"d_{i}", use_container_width=True):
                    if entregue: st.session_state['entregues'].remove(i)
                    else: st.session_state['entregues'].add(i)
                    st.rerun()
            with cb:
                st.link_button("🚗", f"https://waze.com/ul?ll={row['LATITUDE']},{row['LONGITUDE']}&navigate=yes", use_container_width=True)
            with cc:
                st.session_state['custom_sequences'][i] = st.text_input("", value=seq_v, key=f"s_{i}", label_visibility="collapsed")