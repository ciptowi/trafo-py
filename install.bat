@echo off
echo --- 1. Menghapus environment lama (jika ada) ---
IF EXIST .venv (
    rmdir /S /Q .venv
)

echo --- 2. Membuat Virtual Environment baru ---
python3.11 -m venv .venv

echo --- 3. Mengaktifkan Environment ---
call .\.venv\Scripts\activate.bat

echo --- 4. Upgrade Pip ---
python -m pip install --upgrade pip

echo --- 5. Menginstal Kebutuhan dari requirement.txt ---
python -m pip install -r requirement.txt

echo --- 6. Menampilkan Paket Terinstal ---
python -m pip list

echo.
echo --- PROSES INSTALASI SELESAI ---
pause