@echo off
setlocal

:: --- setup virtual environment jika belum ada ---
IF NOT EXIST .venv (
    echo 🔧 Membuat virtual environment .venv ...
    python -m venv .venv
)

:: --- aktifkan virtual environment ---
echo ✅ Mengaktifkan virtual environment...
call .\.venv\Scripts\activate.bat

:: --- install dependensi ---
:: (Cek 'if uvicorn exists' lebih rumit di Batch, jadi lebih mudah
::  untuk menjalankan 'install' saja. Pip akan melewatinya jika sudah ada.)
echo 📦 Menginstal/Memverifikasi FastAPI dan Uvicorn...
python -m pip install --upgrade pip
python -m pip install fastapi uvicorn

:: --- jalankan server FastAPI ---
echo 🚀 Menjalankan FastAPI di http://127.0.0.1:8000/docs ...
echo (Tekan CTRL+C untuk berhenti)
uvicorn main:app --reload

endlocal