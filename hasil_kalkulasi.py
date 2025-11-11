import csv
from  datetime import datetime
import io
from fastapi import Query, Depends, HTTPException, APIRouter, UploadFile
from fastapi.params import File
from sqlalchemy.orm import Session
from database import engine, SessionLocal
from auth import get_current_user
from response import response_ok, response_paginate

import math
import models, schemas

router = APIRouter(tags=["hasil kalkulasi"])

# Dependency DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create table 'group trafo' when not exist
models.Base.metadata.create_all(bind=engine, tables=[models.HasilKalkulasi.__table__])


@router.post("/kalkulasi/upload-csv")
async def upload_hasil_kalkulasi(
    id_trafo: int = Query(..., description="ID Trafo yang akan di-upload datanya"),
    kapasitas: int = Query(..., description="Kapasitas Trafo"), 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    
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
                kv_r_calc = v_r_float * i_r_float

            kv_s_calc = None
            if v_s_float is not None and i_s_float is not None:
                kv_s_calc = v_s_float * i_s_float

            kv_t_calc = None
            if v_t_float is not None and i_t_float is not None:
                kv_t_calc = v_t_float * i_t_float

                
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
            new_data = models.HasilKalkulasi(
                # Menggunakan 'id_trafo' sesuai variabel Anda
                id_trafo=id_trafo, 
                
                waktu_kalkulasi=datetime_obj,
                
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
