from fastapi import HTTPException, Response, UploadFile
from sqlalchemy.orm import Session, joinedload
from app.core.database import engine
from datetime import datetime

from app.core.database import Base
from app.dependencies.response import response_ok
from app.models.trafo_model import Trafo
from app.models.hasil_kalkulasi_model import HasilKalkulasi
from app.schemas.hasil_kalkulasi_scema import TrafoHasilKalkulasi

import io
import csv
import math
import pandas as pd

# Create table 'group trafo' when not exist
Base.metadata.create_all(bind=engine, tables=[HasilKalkulasi.__table__])

async def upload_hasil_kalkulasi(id_trafo: int, kapasitas: int, file: UploadFile, db: Session):
    
    tgl_upload = datetime.now()

    # 1. Baca file
    contents = await file.read()
    try:
        contents_str = contents.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Encoding file bukan UTF-8.")
        
    file_stream = io.StringIO(contents_str)
    reader = csv.DictReader(file_stream)
    
    data_list = []
    try:
        for row in reader:
            data_list.append(row)
    except csv.Error as e:
        raise HTTPException(status_code=400, detail=f"Format file CSV salah: {e}")

    if not data_list:
        raise HTTPException(status_code=400, detail="File CSV kosong.")

    new_hasil_kalkulasi = []

    # --- FUNGSI HELPER YANG DIPERBAIKI ---
    # Didefinisikan sekali di luar loop untuk efisiensi
    def _to_float_or_none(val, is_voltage=False):
        """
        Helper untuk konversi string ke float dengan aman.
        - Mengatasi 'None' atau string kosong.
        - Mengatasi format '228:01:00' jika is_voltage=True.
        - Mengatasi koma desimal (misal '0,5').
        """
        if val is None or val == '':
            return None
        
        # Ubah string jadi string bersih
        val_str = str(val).replace(',', '.') # Ganti koma desimal
        
        if is_voltage:
            # Mengubah "228:01:00" menjadi "228.01"
            parts = val_str.split(':')
            if len(parts) >= 2:
                val_str = f"{parts[0]}.{parts[1]}" # Ambil jam dan menit
            else:
                val_str = parts[0] # Jika formatnya normal
        
        try:
            return float(val_str)
        except ValueError:
            # Jika 'val' masih tidak bisa diubah (misal 'abc')
            return None
    # --- AKHIR FUNGSI HELPER ---


    # 3. Iterasi data yang sudah dibaca
    for idx, row in enumerate(data_list):
        try:
            # Ambil waktu kalkulasi dari CSV (sesuai format Anda)
            datetime_obj = None
            if row.get('Datetime'):
                datetime_obj = datetime.strptime(row['Datetime'], "%Y-%m-%d %H:%M:%S")

            
            # --- TAHAP 1: Ambil semua nilai float dari CSV ---
            importwh_float = _to_float_or_none(row.get('Import Wh'))
            exportwh_float = _to_float_or_none(row.get('Export Wh'))
            importvarh_float = _to_float_or_none(row.get('Import VArh'))
            exportvarh_float = _to_float_or_none(row.get('Export VArh'))
            v_r_float = _to_float_or_none(row.get('Voltage R'), is_voltage=True)
            v_s_float = _to_float_or_none(row.get('Voltage S'), is_voltage=True)
            v_t_float = _to_float_or_none(row.get('Voltage T'), is_voltage=True)
            
            i_r_float = _to_float_or_none(row.get('Ampere R'))
            i_s_float = _to_float_or_none(row.get('Ampere S'))
            i_t_float = _to_float_or_none(row.get('Ampere T'))
            
            cosphi_float = _to_float_or_none(row.get('Cosphi'))

            
            # --- TAHAP 2: Hitung kVA (Apparent Power) ---
            # (Memperbaiki TypeError: 'NoneType' * 'float')
            
            kv_r_calc = None
            if v_r_float is not None and i_r_float is not None:
                kv_r_calc = v_r_float * i_r_float/1000

            kv_s_calc = None
            if v_s_float is not None and i_s_float is not None:
                kv_s_calc = v_s_float * i_s_float/1000

            kv_t_calc = None
            if v_t_float is not None and i_t_float is not None:
                kv_t_calc = v_t_float * i_t_float/1000

                
            # --- TAHAP 3: Hitung kW (Real Power) sesuai permintaan Anda ---
            # (Mengisi baris Anda yang kosong)
            
            kw_r_calc = None
            if kv_r_calc is not None and cosphi_float is not None:
                kw_r_calc = kv_r_calc * cosphi_float

            kw_s_calc = None
            if kv_s_calc is not None and cosphi_float is not None:
                kw_s_calc = kv_s_calc * cosphi_float
            
            kw_t_calc = None
            if kv_t_calc is not None and cosphi_float is not None:
                kw_t_calc = kv_t_calc * cosphi_float
                
            sin_phi = math.sqrt(1 - cosphi_float**2)

            kvar_r_calc = None
            if kv_r_calc is not None and cosphi_float is not None:
                kvar_r_calc = kv_r_calc * sin_phi

            kvar_s_calc = None
            if kv_s_calc is not None and cosphi_float is not None:
                kvar_s_calc = kv_s_calc * sin_phi

            kvar_t_calc = None
            if kv_t_calc is not None and cosphi_float is not None:
                kvar_t_calc = kv_t_calc * sin_phi
            # --- TAHAP 4: Buat objek model ---
            new_data = HasilKalkulasi(
                # Menggunakan 'id_trafo' sesuai variabel Anda
                id_trafo=id_trafo, 
                
                waktu_kalkulasi=datetime_obj,
                importwh=importwh_float,
                exportwh=exportwh_float,
                importvarh=importvarh_float,
                exportvarh=exportvarh_float,    
                
                v_r=v_r_float,
                v_s=v_s_float,
                v_t=v_t_float,
                
                i_r=i_r_float,
                i_s=i_s_float,
                i_t=i_t_float,
                
                # Hasil kalkulasi kVA
                kv_r = kv_r_calc,
                kv_s = kv_s_calc,
                kv_t = kv_t_calc,
                
                # Hasil kalkulasi kW (BARU)
                kw_r = kw_r_calc,
                kw_s = kw_s_calc,
                kw_t = kw_t_calc,

                # Hasil kalkulasi kvar
                kvar_r = kv_r_calc * sin_phi,
                kvar_s = kv_s_calc * sin_phi,
                kvar_t = kv_t_calc * sin_phi,

                # Total kalkulasi
                total_kva = kv_r_calc+kv_s_calc+kv_t_calc,
                total_kw = kw_r_calc+kw_s_calc+kw_t_calc,
                total_kvar = kvar_r_calc+kvar_s_calc+kvar_t_calc,
                
                # Hasil kalkulasi sisa kapasitas
                sisa_kap = kapasitas - (kv_r_calc+kv_s_calc+kv_t_calc),
                
                cosphi=cosphi_float,
                tgl_upload=tgl_upload,
            )
            new_hasil_kalkulasi.append(new_data)

        except KeyError as e:
            # Error jika header di CSV (misal 'Voltage R') tidak ditemukan
            raise HTTPException(status_code=400, detail=f"Header CSV tidak ditemukan: {e} pada baris {idx + 2}")
        except ValueError as e:
            # Error jika '155' (angka) ternyata 'abc' atau format tanggal salah
            raise HTTPException(status_code=400, detail=f"Data tidak valid: {e} pada baris {idx + 2}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error internal: {e} pada baris {idx + 2}")

    # 4. Simpan semua data ke database
    try:
        db.add_all(new_hasil_kalkulasi) # Ini penting!
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Gagal menyimpan ke database: {e}")

    # 5. Kembalikan respons sukses
    return response_ok(
        message=f"Sukses! {len(new_hasil_kalkulasi)} baris data telah di-upload."
    )

async def upload_hasil_kalkulasi2(id_trafo: int, kapasitas: int, file: UploadFile, db: Session):

    tgl_upload = datetime.now()

    # 1. Baca file mentah
    contents = await file.read()
    try:
        contents_str = contents.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Encoding file bukan UTF-8.")
        
    file_stream = io.StringIO(contents_str)

    # ---- PANDAS: Baca CSV ke DataFrame ----
    try:
        df = pd.read_csv(file_stream)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"CSV tidak valid: {e}")

    # Pastikan kolom Datetime ada
    if 'Datetime' not in df.columns:
        raise HTTPException(status_code=400, detail="Kolom 'Datetime' tidak ditemukan.")

    # 2. Ubah kolom datetime jadi datetime object
    df['Datetime'] = pd.to_datetime(df['Datetime'])

    # 3. Ambil tanggal saja
    df['Date'] = df['Datetime'].dt.date

    # 4. Ambil baris maksimum per hari berdasarkan Import Wh
    daily_max = df.loc[df.groupby("Date")['Import Wh'].idxmax()].reset_index(drop=True)

    # 5. Ubah ke list of dict untuk loop Anda
    data_list = daily_max.to_dict(orient='records')

    if not data_list:
        raise HTTPException(status_code=400, detail="CSV kosong setelah filter harian.")

    # Fungsi helper konversi ke float
    def _to_float_or_none(val):
        if val is None or val == "":
            return None
        try:
            return float(str(val).replace(",", "."))
        except:
            return None

    new_hasil_kalkulasi = []

    # === LOOP BARU: hanya data harian yang sudah difilter ===
    for idx, row in enumerate(data_list):

        try:
            datetime_obj = row['Datetime']

            # ambil semua data CSV
            importwh_float = _to_float_or_none(row.get('Import Wh'))
            exportwh_float = _to_float_or_none(row.get('Export Wh'))
            importvarh_float = _to_float_or_none(row.get('Import VArh'))
            exportvarh_float = _to_float_or_none(row.get('Export VArh'))

            v_r_float = _to_float_or_none(row.get('Voltage R'))
            v_s_float = _to_float_or_none(row.get('Voltage S'))
            v_t_float = _to_float_or_none(row.get('Voltage T'))

            i_r_float = _to_float_or_none(row.get('Ampere R'))
            i_s_float = _to_float_or_none(row.get('Ampere S'))
            i_t_float = _to_float_or_none(row.get('Ampere T'))

            cosphi_float = _to_float_or_none(row.get('Cosphi'))

            # HITUNG kVA
            kv_r = v_r_float * i_r_float / 1000 if v_r_float and i_r_float else None
            kv_s = v_s_float * i_s_float / 1000 if v_s_float and i_s_float else None
            kv_t = v_t_float * i_t_float / 1000 if v_t_float and i_t_float else None

            # HITUNG kW
            kw_r = kv_r * cosphi_float if kv_r and cosphi_float else None
            kw_s = kv_s * cosphi_float if kv_s and cosphi_float else None
            kw_t = kv_t * cosphi_float if kv_t and cosphi_float else None

            # HITUNG kvar
            sin_phi = math.sqrt(1 - cosphi_float**2) if cosphi_float else None

            kvar_r = kv_r * sin_phi if kv_r and sin_phi else None
            kvar_s = kv_s * sin_phi if kv_s and sin_phi else None
            kvar_t = kv_t * sin_phi if kv_t and sin_phi else None

            total_kva = (kv_r or 0) + (kv_s or 0) + (kv_t or 0)
            total_kw = (kw_r or 0) + (kw_s or 0) + (kw_t or 0)
            total_kvar = (kvar_r or 0) + (kvar_s or 0) + (kvar_t or 0)

            sisa_kap = kapasitas - total_kva if total_kva else None

            new_row = HasilKalkulasi(
                id_trafo=id_trafo,
                waktu_kalkulasi=datetime_obj,

                importwh=importwh_float,
                exportwh=exportwh_float,
                importvarh=importvarh_float,
                exportvarh=exportvarh_float,

                v_r=v_r_float,
                v_s=v_s_float,
                v_t=v_t_float,

                i_r=i_r_float,
                i_s=i_s_float,
                i_t=i_t_float,

                kv_r=kv_r,
                kv_s=kv_s,
                kv_t=kv_t,

                kw_r=kw_r,
                kw_s=kw_s,
                kw_t=kw_t,

                kvar_r=kvar_r,
                kvar_s=kvar_s,
                kvar_t=kvar_t,

                total_kva=total_kva,
                total_kw=total_kw,
                total_kvar=total_kvar,

                sisa_kap=sisa_kap,
                cosphi=cosphi_float,
                tgl_upload=tgl_upload
            )

            new_hasil_kalkulasi.append(new_row)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error: {e}")

    # SIMPAN
    try:
        db.add_all(new_hasil_kalkulasi)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Gagal menyimpan ke database: {e}")

    return response_ok(
        message=f"Sukses! {len(new_hasil_kalkulasi)} data harian berhasil disimpan."
    )

def get_trafo_hasil_kalkulasi_by_id(trafo_id: int, db: Session):
    """
    Get a single row of hasil_kalkulasi filtered by trafo_id and order by waktu_kalkulasi.
    """
    try:
        hasil_kalkulasi = db.query(HasilKalkulasi).\
            options(joinedload(HasilKalkulasi.trafo)).\
            filter(HasilKalkulasi.id_trafo == trafo_id).\
            order_by(HasilKalkulasi.waktu_kalkulasi.desc()).\
            first()

        if hasil_kalkulasi is None:
            # Lebih baik gunakan 404 jika hasil kalkulasinya yang tidak ada,
            # bukan trafonya
            raise HTTPException(status_code=404, detail=f"Hasil kalkulasi for trafo id {trafo_id} not found")

        # --- SOLUSI ---
        # Buat skema respons secara manual, bukan pakai from_orm
        data_respons = TrafoHasilKalkulasi(
            trafo=hasil_kalkulasi.trafo,       # Ambil dari relationship
            hasil_kalkulasi=hasil_kalkulasi    # Gunakan objek utamanya
        )

        return response_ok(
            data=data_respons.model_dump(mode="json")
        )

    except Exception as e:
        print(f"Error internal: {e}") # Tambahkan print untuk debugging
        raise HTTPException(status_code=500, detail=f"Error internal: {e}")


def export_csv_by_id_trafo(trafo_id: int, db: Session):
    """
    Export csv data from hasil_kalkulasi filtered by trafo_id.
    """
    try:
        trafo = db.query(Trafo).filter(Trafo.id == trafo_id).first()
        if not trafo:
            raise HTTPException(status_code=404, detail=f"Trafo not found")
        
        hasil_kalkulasi = db.query(HasilKalkulasi).\
            filter(HasilKalkulasi.id_trafo == trafo_id).\
            order_by(HasilKalkulasi.waktu_kalkulasi.desc()).\
            limit(10).all()

        if not hasil_kalkulasi:
            raise HTTPException(status_code=404, detail=f"Hasil kalkulasi not found")

        # Buat respons csv
        csv_data = io.StringIO()
        writer = csv.writer(csv_data)
        writer.writerow([
            "Trafo",
            "Voltage R",
            "Voltage S",
            "Voltage T",
            "Current R",
            "Current S",
            "Current T",
            "Cosphi",
            "KVA R",
            "KVA S",
            "KVA T",
            "KW R",
            "KW S",
            "KW T",
            "KVAr R",
            "KVAr S",
            "KVAr T",
            "Total KVA",
            "Total KW",
            "Total KVAr",
            "Sisa Kapacitas",
            "Datetime",
        ])
        for row in hasil_kalkulasi:
            writer.writerow([
                trafo.name,
                row.v_r,
                row.v_s,
                row.v_t,
                row.i_r,
                row.i_s,
                row.i_t,
                row.cosphi,
                row.kv_r,
                row.kv_s,
                row.kv_t,
                row.kw_r,
                row.kw_s,
                row.kw_t,
                row.kvar_r,
                row.kvar_s,
                row.kvar_t,
                row.total_kva,
                row.total_kw,
                row.total_kvar,
                row.sisa_kap,
                row.waktu_kalkulasi,
            ])
        csv_data.seek(0) # Kembali ke awal

        filename = f"hasil_kalkulasi_{trafo.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        headers = {
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "text/csv"
        }
        return Response(content=csv_data.getvalue(), headers=headers, media_type="text/csv")
    
    except Exception as e:
        print(f"Error internal: {e}") # Tambahkan print untuk debugging
        raise HTTPException(status_code=500, detail=f"Error internal: {e}")
