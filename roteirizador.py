import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np
from folium.features import DivIcon
import requests

# --- 1. FUNÇÕES TÉCNICAS (ESTÁVEIS) ---
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

# --- 2. DESIGN SYSTEM: CONTROLE TOTAL E CORES ---
st.set_page_config(page_title="Garapas Router", layout="wide", page_icon="🚚")

st.markdown("""
    <style>
    /* Trava de segurança total */
    html, body, [data-testid="stAppViewContainer"] {
        overflow-x: hidden !important;
        width: 100vw !important;
    }
    .block-container { padding: 0rem 0.4rem !important; }
    header, footer, #MainMenu { visibility: hidden; }

    /* Barra de métricas compacta (HTML) */
    .custom-metrics-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: white;
        padding: 6px 10px;
        border-radius: 8px;
        margin: 4px 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        width: 100%;
    }
    .metric-item { text-align: center; flex: 1; }
    .metric-label { font-size: 9px; color: #888; font-weight: bold; text-transform: uppercase; }
    .metric-value { font-size: 15px; color: #111; font-weight: 800; display: block; }

    /* Cards Minimalistas */
    .delivery-card { 
        border-radius: 8px; padding: 8px 10px; margin-bottom: 3px; 
        background-color: white; border-left: 5px solid #FF4B4B;
    }
    .next-target { border-left: 5px solid #007BFF !important; background-color: #f8fbff !important; }
    .address-header { font-size: 13px !important; font-weight: 700; color: #111; }
    
    /* --- AJUSTE SOLICITADO: NÚMERO DA ORDEM EM PRETO --- */
    .stTextInput input {
        height: 30px !important; 
        background-color: #f1f3f5 !important;
        color: black !important; /* MUDANÇA AQUI: VERDE -> PRETO */
        font-size: 13px !important;
        text-align: center; 
        font-weight: 800 !important;
        border-radius: 6px !important;
    }
    
    /* Botões de Ação */
    .stButton button {
        height: 36px !important; font-size: 11px !important;
        width: 100% !important; border-radius: 8px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ESTADO E MEMÓRIA ---
if 'df_final' not in st.session_state: st.session_state['df_final'] = None
if 'road_path' not in st.session_state: st.session_state['road_path'] = []
if 'entregues' not in st.session_state: st.session_state['entregues'] = set()
if 'custom_sequences' not in st.session_state: st.session_state['custom_sequences'] = {}

# --- 4. TELA INICIAL ---
if st.session_state['df_final'] is None:
    st.subheader("🚚 Garapas Router")
    uploaded_file = st.file_uploader("", type=['xlsx'])
    if uploaded_file and st.button("🚀 Otimizar Rota", use_container_width=True):
        df_raw = pd.read_excel(uploaded_file)
        df_raw.columns = df_raw.columns.str.strip().str.upper()
        df_clean = df_raw.dropna(subset=['LATITUDE', 'LONGITUDE'])
        df_temp = df_clean.copy().reset_index()
        rota = []
        p_atual = df_temp.iloc[0]; rota.append(p_atual); df_temp = df_temp.drop(df_temp.index[0])
        while not df_temp.empty:
            dists = fast_haversine(p_atual['LATITUDE'], p_atual['LONGITUDE'], df_temp['LATITUDE'].values, df_temp['LONGITUDE'].values)
            idx = np.argmin(dists); p_atual = df_temp.iloc[idx]; rota.append(p_atual); df_temp = df_temp.drop(df_temp.index[idx])
        final_df = pd.DataFrame(rota).reset_index(drop=True)
        final_df['ORDEM_PARADA'] = range(1, len(final_df) + 1)
        st.session_state['df_final'] = final_df
        st.session_state['road_path'] = get_road_route_batch(final_df[['LATITUDE', 'LONGITUDE']].values.tolist())
        st.rerun()

# --- 5. INTERFACE OPERACIONAL ---
if st.session_state['df_final'] is not None:
    df_res = st.session_state['df_final']
    restantes = [i for i in range(len(df_res)) if i not in st.session_state['entregues']]

    # A. MAPA NO TOPO
    m = folium.Map(tiles="cartodbpositron")
    if st.session_state['road_path']:
        folium.PolyLine(st.session_state['road_path'], color="#007BFF", weight=4, opacity=0.7).add_to(m)

    all_coords = []
    for i, row in df_res.iterrows():
        foi = i in st.session_state['entregues']
        cor = "#2ecc71" if foi else ("#007BFF" if (restantes and i == restantes[0]) else "#e74c3c")
        loc = [row['LATITUDE'], row['LONGITUDE']]; all_coords.append(loc)
        icon_html = f'<div style="background-color:{cor};border:1px solid white;border-radius:50%;width:18px;height:18px;display:flex;align-items:center;justify-content:center;color:white;font-weight:bold;font-size:7px;">{int(row["ORDEM_PARADA"])}</div>'
        folium.Marker(location=loc, icon=DivIcon(icon_size=(18,18), icon_anchor=(9,9), html=icon_html)).add_to(m)
    
    if all_coords: m.fit_bounds(all_coords, padding=(20, 20))
    st_folium(m, width=None, height=200, use_container_width=True)

    # B. MÉTRICAS EM HTML (HORIZONTAL)
    km_v = sum(fast_haversine(df_res.iloc[restantes[k]]['LATITUDE'], df_res.iloc[restantes[k]]['LONGITUDE'], df_res.iloc[restantes[k+1]]['LATITUDE'], df_res.iloc[restantes[k+1]]['LONGITUDE']) for k in range(len(restantes)-1))
    
    st.markdown(f"""
        <div class="custom-metrics-container">
            <div class="metric-item">
                <span class="metric-label">📦 Faltam</span>
                <span class="metric-value">{len(restantes)} paradas</span>
            </div>
            <div class="metric-item">
                <span class="metric-label">🛤️ KM Restante</span>
                <span class="metric-value">{km_v * 1.3:.1f} km</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("🗑️ LIMPAR FEITAS", use_container_width=True):
        if restantes:
            st.session_state['df_final'] = df_res.iloc[restantes].reset_index(drop=True)
            st.session_state['df_final']['ORDEM_PARADA'] = range(1, len(st.session_state['df_final']) + 1)
            st.session_state['entregues'] = set()
            st.session_state['road_path'] = get_road_route_batch(st.session_state['df_final'][['LATITUDE', 'LONGITUDE']].values.tolist())
            st.rerun()

    # C. LISTA COM ROLAGEM
    with st.container(height=480):
        for i, row in df_res.iterrows():
            rua, bairro = str(row.get('DESTINATION ADDRESS', '---')), str(row.get('BAIRRO', ''))
            entregue = i in st.session_state['entregues']
            is_next = (restantes and i == restantes[0])
            card_class = "next-target" if is_next else ""

            st.markdown(f'<div class="delivery-card {card_class}"><div class="address-header">{int(row["ORDEM_PARADA"])}ª - {rua} <span style="font-size:9px;color:#999;">({bairro})</span></div></div>', unsafe_allow_html=True)
            
            ca, cb, cc = st.columns([0.8, 0.8, 1.4])
            with ca:
                if st.button("✅" if not entregue else "🔄", key=f"d_{i}", use_container_width=True):
                    if entregue: st.session_state['entregues'].remove(i)
                    else: st.session_state['entregues'].add(i)
                    st.rerun()
            with cb:
                st.link_button("🚗", f"https://waze.com/ul?ll={row['LATITUDE']},{row['LONGITUDE']}&navigate=yes", use_container_width=True)
            with cc:
                st.session_state['custom_sequences'][i] = st.text_input("", value=st.session_state['custom_sequences'].get(i, str(row.get('SEQUENCE', '---'))), key=f"s_{i}", label_visibility="collapsed")