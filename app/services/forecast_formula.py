from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import timedelta, datetime
from sklearn.preprocessing import MinMaxScaler

# --- Impor disesuaikan sesuai permintaan Anda ---
from app.dependencies.response import response_ok
from app.models.hasil_kalkulasi_model import HasilKalkulasi 
from app.schemas.forecast_schema import ForecastResult
# --- Akhir Impor disesuaikan ---

import numpy as np
import pandas as pd
import tensorflow as tf
import math

# --- CACHE GLOBAL KRITIS ---
# Menyimpan model yang sudah dilatih per trafo ID.
# Ini adalah optimasi utama untuk mengurangi train time pada API.
# Key: trafo_id (int)
# Value: {'model': tf.keras.Model, 'scaler': MinMaxScaler, 'seq_length': int, 'last_date': datetime}
GLOBAL_MODEL_CACHE: Dict[int, Dict[str, Any]] = {}
# ---

# --- DUMMY MODEL (Dihapus karena Anda mengimpor HasilKalkulasi yang asli) ---

class ForecastFormula:
    """Mengelola seluruh siklus hidup ML: Preprocessing, Training, Forecasting."""

    def __init__(self, db: Session, trafo_id: int):
        self.db = db
        self.MIN_DATA_ROWS = 30
        self.DEFAULT_SEQ_LENGTH = 21
        self.trafo_id = trafo_id

    def _load_data(self) -> pd.DataFrame:
        """Memuat data dari database dan memproses outlier."""
        
        # Query Database yang sebenarnya (Pastikan 'waktu_kalkulasi' memiliki index!)
        data_records = self.db.query(HasilKalkulasi).filter(HasilKalkulasi.id_trafo == self.trafo_id).order_by(HasilKalkulasi.waktu_kalkulasi.desc()).all()
            
        if not data_records:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Hasil kalkulasi for trafo id {self.trafo_id} not found")

        daily_df = pd.DataFrame([
            {"Date": r.waktu_kalkulasi, "ImportVA": r.total_kva} 
            for r in data_records
        ])
        
        # Validasi data minimal
        if daily_df.empty or len(daily_df) < self.MIN_DATA_ROWS:
            raise ValueError(f"Data tidak mencukupi. Ditemukan {len(daily_df)} hari. Minimal {self.MIN_DATA_ROWS} hari diperlukan.")

        # Outlier Clamping (IQR)
        q1 = daily_df['ImportVA'].quantile(0.25)
        q3 = daily_df['ImportVA'].quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        daily_df['ImportVA'] = daily_df['ImportVA'].clip(lower, upper)
        
        return daily_df.sort_values(by='Date').reset_index(drop=True)


    def _build_lstm_transformer(self, seq_length, n_features=1) -> tf.keras.Model:
        """Membangun arsitektur model LSTM + Transformer Attention yang dioptimalkan."""
        
        seq_input = tf.keras.Input(shape=(seq_length, n_features))
        D_MODEL = 32 # Dimensi output LSTM, harus konsisten di seluruh blok.

        # --- Sederhanakan LSTM encoder ---
        x = tf.keras.layers.LSTM(D_MODEL, return_sequences=True, name="LSTM_32")(seq_input)
        x = tf.keras.layers.Dropout(0.1, name="Dropout_LSTM1")(x)

        # --- Multi-Head Attention Block ---
        attn_out = tf.keras.layers.MultiHeadAttention(num_heads=2, key_dim=16)(x, x)
        x = x + attn_out # Residual 1: 32 + 32 (OK)
        x = tf.keras.layers.LayerNormalization(epsilon=1e-6)(x)

        # --- Feed Forward Network (FFN) ---
        # FFN harus mengembalikan dimensi yang sama (D_MODEL=32) untuk Residual Connection kedua.
        
        # 1. Expansion Layer (Misal ke 64)
        ffn = tf.keras.layers.Dense(64, activation='relu', name="FFN_Expansion")(x)
        ffn = tf.keras.layers.Dropout(0.1, name="Dropout_FFN_1")(ffn)
        
        # 2. Contraction Layer (MUST match D_MODEL=32)
        ffn = tf.keras.layers.Dense(D_MODEL, name="FFN_Contraction")(ffn) # ### [PERBAIKAN] Dimensi FFN diubah dari 16 ke D_MODEL (32)

        # Residual 2
        x = tf.keras.layers.LayerNormalization(epsilon=1e-6, name="Norm_FFN")(x + ffn) # Penjumlahan Residual (32 + 32) kini berhasil.

        # --- Global Pooling dan Concatenate ---
        avg_pool = tf.keras.layers.GlobalAveragePooling1D(name="AvgPool")(x)
        max_pool = tf.keras.layers.GlobalMaxPooling1D(name="MaxPool")(x)
        x = tf.keras.layers.Concatenate(name="Concatenate")([avg_pool, max_pool])

        # --- Dense Head (Predictor) ---
        x = tf.keras.layers.Dense(32, activation='relu', name="Dense_32")(x)
        x = tf.keras.layers.Dropout(0.1, name="Dropout_Final")(x)
        output = tf.keras.layers.Dense(1, name="Output_Layer")(x)

        model = tf.keras.Model(inputs=seq_input, outputs=output, name="LSTM_Transformer_Model")
        
        # Pengecekan versi TensorFlow untuk kompatibilitas optimizer
        optimizer = tf.keras.optimizers.Adam(learning_rate=0.001) if tf.__version__.startswith('2.') else 'adam'
            
        model.compile(optimizer=optimizer, loss='mse')
        return model

    def train_model(self, force_retrain: bool = False) -> Dict[str, Any]:
        """Melakukan preprocessing, scaling, dan training model secara kondisional."""
        global GLOBAL_MODEL_CACHE
        
        # --- TAHAP 0: Pemuatan Data & Pemeriksaan Cache ---
        daily_df = self._load_data()
        values = daily_df[["ImportVA"]].values.astype(float)
        last_data_date = daily_df['Date'].iloc[-1]
        
        cache_entry = GLOBAL_MODEL_CACHE.get(self.trafo_id)

        # Optimasi Caching Kritis: Lewati pelatihan jika data tidak berubah.
        if cache_entry and cache_entry['last_date'] == last_data_date and not force_retrain:
            
            print(f"Trafo ID {self.trafo_id}: Model sudah terlatih. Melewatkan pelatihan.")
            return self.run_forecast(df=daily_df, forecast_steps=90) 
            
        print(f"Trafo ID {self.trafo_id}: Melatih ulang model...")
        
        # --- TAHAP 1: Preprocessing dan Scaling ---
        
        train_ratio = 0.8
        split_idx = int(len(values) * train_ratio)
        train_values = values[:split_idx]

        seq_length = min(self.DEFAULT_SEQ_LENGTH, len(train_values) - 1)
        if seq_length < 2:
            raise ValueError("Data training terlalu sedikit untuk dibuat sequence.")
            
        scaler = MinMaxScaler()
        train_scaled = scaler.fit_transform(train_values)
        test_scaled  = scaler.transform(values[split_idx:])
        scaled_full = np.concatenate([train_scaled, test_scaled], axis=0)
        
        # --- TAHAP 2: Sequence Creation yang Efisien (Optimasi NumPy) ---

        # Sequence creation yang di-vektorisasi (Jauh lebih cepat daripada loop Python)
        indices = np.arange(len(scaled_full) - seq_length)
        # Membuat X_all (Input)
        X_all = np.array([scaled_full[i:i + seq_length] for i in indices])
        # Membuat y_all (Target)
        y_all = scaled_full[seq_length:] 
        
        # Membagi kembali X dan y untuk training
        # Perbaiki penentuan sequence end index
        train_sequence_end_index = split_idx - seq_length
        X_train, y_train = X_all[:train_sequence_end_index], y_all[:train_sequence_end_index]
        
        # Reshape ke format [samples, timesteps, features]
        X_train = X_train.reshape((X_train.shape[0], seq_length, 1))
        
        # --- TAHAP 3: Model Building dan Training (Optimasi Hyperparameter) ---
        
        model = self._build_lstm_transformer(seq_length, n_features=1)
        
        # Callbacks (Patience dan Epochs dikurangi untuk mempercepat EarlyStopping)
        early_stop = tf.keras.callbacks.EarlyStopping(monitor='val_loss', patience=7, restore_best_weights=True, verbose=0) # Dari 15
        reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(monitor='val_loss', patience=5, factor=0.3, min_lr=1e-6, verbose=0) # Dari 7

        # Training (Epochs dikurangi dari 150 menjadi 80)
        history = model.fit(
            X_train, y_train,
            epochs=80, 
            batch_size=32,
            validation_split=0.2,
            callbacks=[early_stop, reduce_lr],
            verbose=0 
        )
        
        # --- TAHAP 4: Caching dan Return ---
        
        # Simpan Model, Scaler, Seq_length, dan Tanggal data terakhir ke Cache Global
        GLOBAL_MODEL_CACHE[self.trafo_id] = {
            'model': model,
            'scaler': scaler,
            'seq_length': seq_length,
            'last_date': last_data_date
        }
        
        # Ambil metrik terakhir (Opsional, untuk debugging/logging)
        # val_loss = history.history['val_loss'][-1] if history.history.get('val_loss') else None
        
        return self.run_forecast(df=daily_df, forecast_steps=90)

    def run_forecast(self, df: pd.DataFrame, forecast_steps: int) -> Dict[str, Any]:
        """Melakukan forecast multi-step ke depan menggunakan model yang di-cache."""
        global GLOBAL_MODEL_CACHE

        cache_entry = GLOBAL_MODEL_CACHE.get(self.trafo_id)

        if cache_entry is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Model belum dilatih untuk ID ini.")
        
        # Ambil dari cache
        model = cache_entry['model']
        scaler = cache_entry['scaler']
        seq_length = cache_entry['seq_length']
        
        # Muat data full
        values = df[["ImportVA"]].values.astype(float)
        
        # Ambil sequence terakhir dari data FULL (sudah diskalakan oleh scaler)
        last_seq = scaler.transform(values[-seq_length:]).reshape(1, seq_length, 1)

        forecast_scaled = []

        for _ in range(forecast_steps):
            # Prediksi satu langkah ke depan
            next_scaled = model.predict(last_seq, verbose=0)[0, 0]
            forecast_scaled.append([next_scaled])

            # Geser window (multi-step prediction)
            new_seq = np.append(last_seq[:, 1:, :], [[[next_scaled]]], axis=1)
            last_seq = new_seq

        forecast_scaled_arr = np.array(forecast_scaled)
        
        # Balik ke satuan asli
        forecast_orig_arr = scaler.inverse_transform(forecast_scaled_arr).reshape(-1)

        # Buat tanggal ke depan
        last_date = df['Date'].iloc[-1]
        forecast_dates = [last_date + timedelta(days=i) for i in range(1, forecast_steps + 1)]

        # Format hasil
        results = []
        for d, v in zip(forecast_dates, forecast_orig_arr):
            results.append(
                {
                    "date": d.strftime("%Y-%m-%d"),
                    "value": float(v)
                }
            )
            
        data_json = {
            "date": results[-1]["date"],
            "value": results[-1]["value"]
        }
            
        return response_ok(data=data_json, message="Success")