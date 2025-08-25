import io
import re
import pandas as pd
import streamlit as st

st.set_page_config(page_title="CSV/Excel Viewer + NIK Cleaner", page_icon="🧹", layout="wide")
st.title("🧹 CSV/Excel Viewer + NIK Cleaner (NIK 16 digit diawali '3')")

st.write(
    "Upload file **CSV** atau **Excel (XLSX/XLS)**, pratinjau data, lalu bersihkan baris "
    "berdasarkan **NIK KTP Indonesia** pada kolom *MemberNo* dan/atau *IdentityNo*. "
    "Kriteria valid: **16 digit angka** dan **diawali angka '3'**."
)

uploaded_file = st.file_uploader("Pilih file CSV/XLSX", type=["csv", "xlsx", "xls"])

def only_digits(s):
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    # cast angka/float -> string, hilangkan .0, whitespace, dan karakter non-digit
    s = str(s)
    s = re.sub(r"[^0-9]", "", s)
    return s

def normalize_nik(val):
    digits = only_digits(val)
    # NIK valid: 16 digit dan mulai dengan '3'
    if len(digits) == 16 and digits.startswith("3"):
        return digits
    return None

if uploaded_file is not None:
    file_name = uploaded_file.name.lower()
    use_header = st.checkbox("Baris pertama sebagai header", value=True)
    nrows_preview = st.slider("Jumlah baris preview", min_value=5, max_value=200, value=50, step=5)

    df = None

    try:
        if file_name.endswith(".csv"):
            delimiter = st.selectbox("Delimiter CSV", options=[",", ";", "\t", "|"], index=0, help="Pilih pemisah kolom")
            encodings_to_try = ["utf-8", "utf-8-sig", "cp1252", "latin1"]
            last_err = None
            for enc in encodings_to_try:
                try:
                    df = pd.read_csv(uploaded_file, sep=delimiter, encoding=enc, header=0 if use_header else None)
                    break
                except Exception as e:
                    last_err = e
                    uploaded_file.seek(0)
            if df is None and last_err:
                st.error(f"Gagal membaca CSV. Error terakhir: {last_err}")
        else:
            uploaded_file.seek(0)
            xl = pd.ExcelFile(uploaded_file)
            sheet = st.selectbox("Pilih sheet", options=xl.sheet_names)
            df = xl.parse(sheet_name=sheet, header=0 if use_header else None)
    except Exception as e:
        st.error(f"Terjadi error saat membaca file: {e}")
        st.stop()

    if df is not None:
        st.success("File berhasil dibaca ✅")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Jumlah Baris", df.shape[0])
        with c2:
            st.metric("Jumlah Kolom", df.shape[1])
        with c3:
            st.write("**Tipe Data (ringkas)**")
            st.caption(", ".join([f"{c}:{str(t)}" for c, t in zip(df.columns, df.dtypes)])[:250] + ("..." if len(df.columns)>10 else ""))

        st.subheader("Preview Data (awal)")
        st.dataframe(df.head(nrows_preview), use_container_width=True)

        # ---------- Bagian Pembersihan NIK ----------
        st.subheader("🧽 Pembersihan berdasarkan NIK (16 digit, diawali '3')")
        st.caption("Sistem akan menyaring baris yang memiliki NIK valid pada salah satu kolom yang dipilih. "
                   "Nilai non-digit akan dihilangkan sebelum validasi (misal spasi/tanda baca).")

        # Pilih kolom sumber (fallback bila nama berbeda)
        cols = ["<Tidak Ada>"] + df.columns.astype(str).tolist()
        default_member = df.columns[df.columns.astype(str).str.lower().eq("memberno")]
        default_identity = df.columns[df.columns.astype(str).str.lower().eq("identityno")]

        member_col = st.selectbox(
            "Kolom MemberNo",
            options=cols,
            index=(cols.index(default_member[0]) if len(default_member) > 0 else 0)
        )
        identity_col = st.selectbox(
            "Kolom IdentityNo",
            options=cols,
            index=(cols.index(default_identity[0]) if len(default_identity) > 0 else 0)
        )

        # Proses pembersihan
        do_clean = st.checkbox("Aktifkan pembersihan NIK", value=True)

        if do_clean and (member_col != "<Tidak Ada>" or identity_col != "<Tidak Ada>"):
            work = df.copy()

            if member_col != "<Tidak Ada>":
                work["MemberNo_clean"] = work[member_col].apply(normalize_nik)
            else:
                work["MemberNo_clean"] = None

            if identity_col != "<Tidak Ada>":
                work["IdentityNo_clean"] = work[identity_col].apply(normalize_nik)
            else:
                work["IdentityNo_clean"] = None

            # baris valid jika salah satu kolom clean tidak None
            mask_valid = work["MemberNo_clean"].notna() | work["IdentityNo_clean"].notna()
            df_clean = work.loc[mask_valid].copy()

            # kolom NIK final (prioritas MemberNo_clean baru IdentityNo_clean)
            df_clean["NIK"] = df_clean["MemberNo_clean"].combine_first(df_clean["IdentityNo_clean"])

            # metrik hasil
            kept = int(mask_valid.sum())
            dropped = int(len(work) - kept)
            c1c, c2c, c3c = st.columns(3)
            with c1c:
                st.metric("Baris Valid (kept)", kept)
            with c2c:
                st.metric("Baris Dibuang", dropped)
            with c3c:
                st.metric("Total Awal", len(work))

            st.write("**Preview Data (SETELAH dibersihkan)**")
            # tampilkan NIK di depan + kolom lainnya (tanpa *_clean)
            front_cols = ["NIK"]
            other_cols = [c for c in df_clean.columns if c not in front_cols and not c.endswith("_clean")]
            show_cols = front_cols + other_cols
            st.dataframe(df_clean[show_cols].head(nrows_preview), use_container_width=True)

            # Unduh hasil
            csv_bytes = df_clean.to_csv(index=False).encode("utf-8-sig")
            st.download_button("⬇️ Download hasil bersih (CSV)", data=csv_bytes, file_name="cleaned_nik.csv", mime="text/csv")

            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                df_clean.to_excel(writer, index=False, sheet_name="cleaned")
            st.download_button(
                "⬇️ Download hasil bersih (XLSX)",
                data=buf.getvalue(),
                file_name="cleaned_nik.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        else:
            st.info("Aktifkan pembersihan dan pilih minimal satu kolom (MemberNo/IdentityNo) untuk memfilter berdasarkan NIK.")
        # ---------- /Pembersihan NIK ----------

        with st.expander("🔎 Filter sederhana (opsional)"):
            cols_f = st.multiselect("Pilih kolom untuk filter equals", df.columns.astype(str).tolist())
            filtered = df.copy()
            for col in cols_f:
                unique_vals = filtered[col].dropna().unique().tolist()
                # batasi opsi agar cepat
                options = ["<kosong>"] + (unique_vals[:100] if len(unique_vals) > 100 else unique_vals)
                val = st.selectbox(f"Nilai untuk kolom '{col}'", options=options, key=f"filter_{col}")
                if val == "<kosong>":
                    filtered = filtered[filtered[col].isna()]
                else:
                    filtered = filtered[filtered[col] == val]
            st.dataframe(filtered.head(nrows_preview), use_container_width=True)
            csv_filt = filtered.to_csv(index=False).encode("utf-8-sig")
            st.download_button("⬇️ Download hasil filter (CSV)", data=csv_filt, file_name="filtered_output.csv", mime="text/csv")

else:
    st.info("Belum ada file diunggah.")
