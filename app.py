import streamlit as st
import simpy
import random
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from dataclasses import dataclass

# ============================
# KONFIGURASI SIMULASI
# ============================
@dataclass
class Config:
    JUMLAH_MEJA: int = 60
    # Parameter kecepatan (dalam menit)
    LAUK_SPEED: float = 0.8  
    ANGKUT_SPEED: float = 0.5
    NASI_SPEED: float = 0.8
    START_TIME: str = "07:00"

# ============================
# MODEL SIMULASI (DES)
# ============================
class PiketSimulasi:
    def __init__(self, config: Config):
        self.config = config
        self.env = simpy.Environment()
        
        # Resources (Petugas)
        self.petugas_lauk = simpy.Resource(self.env, capacity=2)
        self.petugas_angkut = simpy.Resource(self.env, capacity=3)
        self.petugas_nasi = simpy.Resource(self.env, capacity=2)
        
        self.data_hasil = []
        jam_split = self.config.START_TIME.split(':')
        self.start_dt = datetime(2024, 1, 1, int(jam_split[0]), int(jam_split[1]))

    def proses_meja(self, meja_id):
        # 1. Tahap Isi Lauk
        with self.petugas_lauk.request() as req:
            yield req
            # Durasi acak berdasarkan parameter speed
            yield self.env.timeout(random.uniform(self.config.LAUK_SPEED - 0.2, self.config.LAUK_SPEED + 0.2))
        
        # 2. Tahap Angkut
        with self.petugas_angkut.request() as req:
            yield req
            yield self.env.timeout(random.uniform(self.config.ANGKUT_SPEED - 0.1, self.config.ANGKUT_SPEED + 0.1))
            
        # 3. Tahap Isi Nasi
        with self.petugas_nasi.request() as req:
            yield req
            yield self.env.timeout(random.uniform(self.config.NASI_SPEED - 0.2, self.config.NASI_SPEED + 0.2))
        
        # Selesai
        self.data_hasil.append({
            'Meja': meja_id,
            'Waktu Selesai': self.env.now,
            'Jam Selesai': (self.start_dt + timedelta(minutes=self.env.now)).strftime("%H:%M:%S")
        })

    def run(self):
        for i in range(1, self.config.JUMLAH_MEJA + 1):
            self.env.process(self.proses_meja(i))
        self.env.run()
        return pd.DataFrame(self.data_hasil)

# ============================
# INTERFACE STREAMLIT
# ============================
st.set_page_config(page_title="Simulasi Piket IT Del", layout="wide")

with st.sidebar:
    st.header("⚙️ Kontrol Simulasi")
    target_durasi = st.slider("Target Durasi Piket (Menit)", 15, 60, 25)
    st.divider()
    st.caption("Petugas: 7 Orang (2 Lauk, 3 Angkut, 2 Nasi)")
    run_btn = st.button("🚀 Jalankan Simulasi", type="primary", use_container_width=True)

st.title("📊 Monitoring Dashboard Piket IT Del")

if run_btn:
    # Eksekusi Model
    cfg = Config()
    sim = PiketSimulasi(cfg)
    df = sim.run()
    df = df.sort_values('Waktu Selesai')
    
    realisasi = df['Waktu Selesai'].max()
    selisih = target_durasi - realisasi
    
    # --- METRICS ---
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Target", f"{target_durasi} Min")
    m2.metric("Realisasi", f"{realisasi:.2f} Min", f"{selisih:.2f} Min")
    m3.metric("Status", "✅ TERPENUHI" if selisih >= 0 else "❌ MELAMPAUI")
    m4.metric("Total Meja", f"{len(df)}")

    # --- GRAPHS ---
    
    # Baris 1: Line Chart & Bar Chart
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Progres Kumulatif")
        fig_line = px.line(df, x='Waktu Selesai', y='Meja', 
                           title="Laju Penyelesaian Meja (Menit ke Menit)",
                           markers=True)
        fig_line.add_vline(x=target_durasi, line_dash="dash", line_color="red", annotation_text="Batas Target")
        st.plotly_chart(fig_line, use_container_width=True)
        
    with col2:
        st.subheader("📊 Distribusi Output Meja")
        # Mengelompokkan penyelesaian per 5 menit untuk bar chart
        df['Interval'] = (df['Waktu Selesai'] // 5 * 5).astype(int)
        dist_df = df.groupby('Interval').size().reset_index(name='Jumlah Meja')
        fig_bar = px.bar(dist_df, x='Interval', y='Jumlah Meja', 
                         title="Jumlah Meja Selesai per Interval 5 Menit",
                         color='Jumlah Meja', color_continuous_scale='Blues')
        st.plotly_chart(fig_bar, use_container_width=True)

    # Baris 2: Sensitivitas & Gauge
    col3, col4 = st.columns(2)
    
    with col3:
        st.subheader("🎯 Analisis Target vs Realisasi")
        # Membuat data perbandingan sederhana
        comp_data = pd.DataFrame({
            'Kategori': ['Target User', 'Realisasi Sistem'],
            'Menit': [target_durasi, realisasi]
        })
        fig_comp = px.bar(comp_data, x='Kategori', y='Menit', color='Kategori',
                          color_discrete_map={'Target User': 'gray', 'Realisasi Sistem': 'orange'})
        st.plotly_chart(fig_comp, use_container_width=True)

    with col4:
        st.subheader("⏲️ Efisiensi Waktu")
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = realisasi,
            gauge = {
                'axis': {'range': [0, 80]},
                'steps': [
                    {'range': [0, target_durasi], 'color': "lightgreen"},
                    {'range': [target_durasi, 80], 'color': "pink"}]}))
        st.plotly_chart(fig_gauge, use_container_width=True)

    # Tabel Detail
    with st.expander("📋 Rincian Data Meja"):
        st.dataframe(df[['Meja', 'Waktu Selesai', 'Jam Selesai']], use_container_width=True)

else:
    st.info("Klik tombol di sidebar untuk menjalankan simulasi.")