
import io
import pandas as pd
import streamlit as st

st.set_page_config(page_title="CSV/Excel Viewer", page_icon="📄", layout="wide")
st.title("📄 CSV/Excel Viewer (Simple)")

st.write(
    "Upload file **CSV** atau **Excel (XLSX/XLS)**, lalu aplikasinya akan menampilkan datanya. "
    "Jika Excel memiliki banyak sheet, pilih sheet yang ingin ditampilkan."
)

uploaded_file = st.file_uploader("Pilih file CSV/XLSX", type=["csv", "xlsx", "xls"])

if uploaded_file is not None:
    file_name = uploaded_file.name.lower()
    use_header = st.checkbox("Baris pertama sebagai header", value=True)
    nrows_preview = st.slider("Jumlah baris preview", min_value=5, max_value=200, value=50, step=5)

    df = None

    try:
        if file_name.endswith(".csv"):
            # Opsi delimiter
            delimiter = st.selectbox("Delimiter CSV", options=[",", ";", "\t", "|"], index=0, help="Pilih pemisah kolom")
            # Coba beberapa encoding umum
            encodings_to_try = ["utf-8", "utf-8-sig", "cp1252", "latin1"]
            last_err = None
            for enc in encodings_to_try:
                try:
                    df = pd.read_csv(uploaded_file, sep=delimiter, encoding=enc, header=0 if use_header else None)
                    break
                except Exception as e:
                    last_err = e
                    uploaded_file.seek(0)  # reset pointer untuk percobaan berikutnya
            if df is None and last_err:
                st.error(f"Gagal membaca CSV. Error terakhir: {last_err}")
        else:
            # Excel: deteksi semua sheet terlebih dahulu
            uploaded_file.seek(0)
            xl = pd.ExcelFile(uploaded_file)
            sheet = st.selectbox("Pilih sheet", options=xl.sheet_names)
            df = xl.parse(sheet_name=sheet, header=0 if use_header else None)
    except Exception as e:
        st.error(f"Terjadi error saat membaca file: {e}")
        st.stop()

    if df is not None:
        st.success("File berhasil dibaca ✅")
        # Info ringkas
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Jumlah Baris", df.shape[0])
        with c2:
            st.metric("Jumlah Kolom", df.shape[1])
        with c3:
            st.write("**Tipe Data Kolom**")
            st.caption(", ".join([f"{c}:{str(t)}" for c, t in zip(df.columns, df.dtypes)]))
        with c4:
            st.write("**Ukuran Memori**")
            try:
                st.caption(f"{df.memory_usage(index=True).sum()/1024**2:.2f} MB")
            except Exception:
                st.caption("-")

        st.subheader("Preview Data")
        st.dataframe(df.head(nrows_preview), use_container_width=True)

        # Unduh kembali ke CSV
        csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "⬇️ Download sebagai CSV",
            data=csv_bytes,
            file_name="output.csv",
            mime="text/csv",
        )

        # Opsi filter sederhana
        with st.expander("🔎 Filter sederhana (opsional)"):
            cols = st.multiselect("Pilih kolom untuk filter equals", df.columns.tolist())
            filtered = df.copy()
            for col in cols:
                unique_vals = filtered[col].dropna().unique().tolist()
                val = st.selectbox(f"Nilai untuk kolom '{col}'", options=["<kosong>"] + unique_vals, key=f"filter_{col}")
                if val == "<kosong>":
                    filtered = filtered[filtered[col].isna()]
                else:
                    filtered = filtered[filtered[col] == val]
            st.dataframe(filtered.head(nrows_preview), use_container_width=True)
            csv_filt = filtered.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "⬇️ Download hasil filter (CSV)",
                data=csv_filt,
                file_name="filtered_output.csv",
                mime="text/csv",
            )

else:
    st.info("Belum ada file diunggah.")
