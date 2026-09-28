import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np # <-- TAMBAHAN BARU: Library Matematika Tingkat Tinggi

# ==========================================
# 1. KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(page_title="Islamic WealthTech", page_icon="🕋", layout="wide")

st.title("🕋 Sistem Alokasi & Forecasting Kuantitatif Syariah")
st.markdown("""
Sistem pintar berbasis Python untuk mendeteksi saham syariah *undervalued* (murah), 
mengalokasikan modal, dan memproyeksikan masa depan menggunakan **Simulasi Monte Carlo**.
""")

# ==========================================
# 2. SIDEBAR (PENGATURAN INTERAKTIF KLIEN)
# ==========================================
st.sidebar.header("⚙️ Pengaturan Portofolio")
modal_input = st.sidebar.number_input("Modal Investasi (Rp)", min_value=100000, value=5000000, step=100000)

st.sidebar.markdown("---")
st.sidebar.subheader("Parameter Fundamental")
batas_pe = st.sidebar.slider("Batas Maksimal P/E Ratio (Valuasi)", 5, 25, 15)
batas_der = st.sidebar.slider("Batas Maksimal DER (%)", 20, 100, 80)

# ==========================================
# 3. MESIN UTAMA (BERJALAN JIKA TOMBOL DITEKAN)
# ==========================================
if st.sidebar.button("🚀 Jalankan Algoritma & Forecast"):
    
    with st.spinner('Membedah Laporan Keuangan & Membangun Simulasi Masa Depan...'):
        
        # --- A. FASE PENYARINGAN FUNDAMENTAL ---
        daftar_saham = [
            'BRIS.JK', 'TLKM.JK', 'ICBP.JK', 'UNTR.JK', 'ASII.JK', 
            'KLBF.JK', 'PTBA.JK', 'ITMG.JK', 'SIDO.JK', 'MYOR.JK', 
            'AKRA.JK', 'PGAS.JK', 'ANTM.JK', 'CPIN.JK', 'MAPI.JK'
        ]
        
        keranjang_data = []
        for saham in daftar_saham:
            info = yf.Ticker(saham).info
            pe_ratio = info.get('trailingPE', 0) 
            der = info.get('debtToEquity', 999) 
            
            if (0 < pe_ratio <= batas_pe) and (der <= batas_der):
                keranjang_data.append({"Kode Saham": saham, "P/E Ratio": pe_ratio, "DER (%)": der})
                
        tabel_lolos = pd.DataFrame(keranjang_data)
        
        if tabel_lolos.empty:
            st.error("❌ Tidak ada saham yang lolos kriteria. Longgarkan batas di pengaturan.")
        else:
            # --- B. FASE PEMBOBOTAN & DISCRETIZATION (PEMBULATAN LOT) ---
            tabel_lolos['Skor_Valuasi'] = 1 / tabel_lolos['P/E Ratio']
            tabel_lolos['Rupiah Target'] = (tabel_lolos['Skor_Valuasi'] / tabel_lolos['Skor_Valuasi'].sum()) * modal_input
            
            harga_terakhir = [yf.Ticker(s).history(period="1d")['Close'].iloc[-1] if not yf.Ticker(s).history(period="1d").empty else 0 for s in tabel_lolos['Kode Saham']]
            tabel_lolos['Harga/Lot (Rp)'] = np.array(harga_terakhir) * 100
            
            tabel_lolos['Jumlah Lot'] = tabel_lolos['Rupiah Target'] // tabel_lolos['Harga/Lot (Rp)']
            tabel_lolos['Total Eksekusi (Rp)'] = tabel_lolos['Jumlah Lot'] * tabel_lolos['Harga/Lot (Rp)']
            
            tabel_final = tabel_lolos[tabel_lolos['Jumlah Lot'] > 0].copy()
            
            if tabel_final.empty:
                st.warning("⚠️ Uang Anda tidak cukup untuk membeli minimal 1 Lot.")
            else:
                tabel_tampil = tabel_final[['Kode Saham', 'P/E Ratio', 'Harga/Lot (Rp)', 'Jumlah Lot', 'Total Eksekusi (Rp)']].copy()
                tabel_tampil['P/E Ratio'] = tabel_tampil['P/E Ratio'].round(1)
                tabel_tampil = tabel_tampil.sort_values(by='Total Eksekusi (Rp)', ascending=False)
                
                total_terpakai = tabel_tampil['Total Eksekusi (Rp)'].sum()
                sisa_cash = modal_input - total_terpakai
                
                # ==========================================
                # 4. TAMPILAN DASHBOARD: ALOKASI
                # ==========================================
                st.success("✅ Algoritma Selesai! Portofolio berhasil dibentuk.")
                st.markdown("---")
                
                col1, col2, col3 = st.columns(3)
                col1.metric("💰 Dana Tereksekusi", f"Rp {int(total_terpakai):,.0f}")
                col2.metric("💵 Sisa Cash (Kembalian)", f"Rp {int(sisa_cash):,.0f}")
                col3.metric("📈 Saham Terpilih", f"{len(tabel_tampil)} Emiten")
                
                col_tab, col_chart = st.columns([3, 2])
                with col_tab:
                    st.subheader("📋 Instruksi Eksekusi Sekuritas")
                    st.dataframe(tabel_tampil, use_container_width=True, hide_index=True)
                with col_chart:
                    st.subheader("📊 Porsi Alokasi Dana")
                    st.bar_chart(tabel_tampil.set_index('Kode Saham')[['Total Eksekusi (Rp)']])

                # ==========================================
                # 5. MODUL FORECASTING: MONTE CARLO SIMULATION
                # ==========================================
                st.markdown("---")
                st.subheader("🔮 Forecasting: Proyeksi Nilai Portofolio (1 Tahun ke Depan)")
                st.write("Menganalisis probabilitas menggunakan 100 skenario *Monte Carlo Simulation* berdasarkan volatilitas IHSG/ISSI (Asumsi Return Historis ~12% per tahun dengan Volatilitas 15%).")
                
                # Setup Monte Carlo
                hari_perdagangan = 252 # 1 tahun bursa
                jumlah_skenario = 100 # Mesin akan menebak 100 kemungkinan masa depan
                
                # Parameter statistik (diubah ke skala harian)
                mu = 0.12 / hari_perdagangan # Rata-rata return harian
                sigma = 0.15 / np.sqrt(hari_perdagangan) # Volatilitas harian
                
                # Menciptakan matriks probabilitas masa depan menggunakan Numpy
                return_harian = np.random.normal(mu, sigma, (hari_perdagangan, jumlah_skenario))
                
                # Menghitung harga masa depan (Modal Awal Tereksekusi diproyeksikan ke depan)
                harga_masa_depan = total_terpakai * np.exp(np.cumsum(return_harian, axis=0))
                
                # Memasukkan hasil simulasi ke dalam format tabel agar bisa digambar
                df_simulasi = pd.DataFrame(harga_masa_depan)
                
                # Menampilkan Grafik "Spaghetti" khas Quant
                st.line_chart(df_simulasi)
                
                # Menghitung Kesimpulan Probabilitas
                nilai_akhir_rata2 = df_simulasi.iloc[-1].mean()
                nilai_akhir_terburuk = df_simulasi.iloc[-1].min()
                nilai_akhir_terbaik = df_simulasi.iloc[-1].max()
                
                st.info(f"""
                **Analisis Skenario 1 Tahun ke Depan (Dari Modal Rp {int(total_terpakai):,.0f}):**
                - 📉 **Skenario Terburuk (Pesimis):** Rp {int(nilai_akhir_terburuk):,.0f}
                - 🎯 **Skenario Probabilitas Tertinggi (Ekspektasi):** Rp {int(nilai_akhir_rata2):,.0f}
                - 🚀 **Skenario Terbaik (Optimis):** Rp {int(nilai_akhir_terbaik):,.0f}
                """)
else:
    st.info("👈 Silakan atur modal dan parameter di menu samping, lalu klik 'Jalankan Algoritma & Forecast'.")
