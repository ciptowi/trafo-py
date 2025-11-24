
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import timedelta
from sklearn.preprocessing import MinMaxScaler
from app.dependencies.response import response_ok
from app.models.hasil_kalkulasi_model import HasilKalkulasi
from app.schemas.forecast_schema import ForecastResult

import numpy as np
import pandas as pd
import tensorflow as tf

class ForecastFormula:
    """Mengelola seluruh siklus hidup ML: Preprocessing, Training, Forecasting."""

    def __init__(self, db: Session, trafo_id: int):
        self.db = db
        self.MIN_DATA_ROWS = 30
        self.DEFAULT_SEQ_LENGTH = 21
        self.trafo_id = trafo_id

    def _load_data(self) -> pd.DataFrame:
        """Memuat data dari SQLite dan memproses outlier."""
        
        # 1. Ambil data
        data_records = self.db.query(HasilKalkulasi).filter(HasilKalkulasi.id_trafo == self.trafo_id).order_by(HasilKalkulasi.waktu_kalkulasi.desc()).all()
        
        if data_records is None:
            raise HTTPException(status_code=404, detail=f"Hasil kalkulasi for trafo id {self.trafo_id} not found")
        
        daily_df = pd.DataFrame([
            {"Date": r.waktu_kalkulasi, "ImportVA": r.total_kva} 
            for r in data_records
        ])

        if daily_df.empty or len(daily_df) < self.MIN_DATA_ROWS:
            raise ValueError(f"Data tidak mencukupi. Ditemukan {len(daily_df)} hari. Minimal {self.MIN_DATA_ROWS} hari diperlukan.")

        # 2. Outlier Clamping (IQR)
        q1 = daily_df['ImportVA'].quantile(0.25)
        q3 = daily_df['ImportVA'].quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        daily_df['ImportVA'] = daily_df['ImportVA'].clip(lower, upper)
        
        return daily_df

    def _create_sequences(self, data, seq_length):
        """Membuat sequence input/output untuk model."""
        X, y = [], []
        for i in range(seq_length, len(data)):
            X.append(data[i-seq_length:i])
            y.append(data[i])
        return np.array(X), np.array(y)

    def _build_lstm_transformer(self, seq_length, n_features=1) -> tf.keras.Model:
        """Membangun arsitektur model LSTM + Transformer Attention."""
        
        seq_input = tf.keras.Input(shape=(seq_length, n_features))

        # --- LSTM encoder ---
        x = tf.keras.layers.LSTM(64, return_sequences=True, name="LSTM_64")(seq_input)
        x = tf.keras.layers.Dropout(0.1, name="Dropout_LSTM1")(x)
        x = tf.keras.layers.LSTM(32, return_sequences=True, name="LSTM_32")(x)
        
        # --- Multi-Head Attention Block ---
        attn_out = tf.keras.layers.MultiHeadAttention(num_heads=4, key_dim=32)(x, x)
        x = x + attn_out
        x = tf.keras.layers.LayerNormalization(epsilon=1e-6)(x)

        # --- Feed Forward Network (FFN) ---
        ffn = tf.keras.layers.Dense(32, activation='relu', name="FFN_32")(x)
        ffn = tf.keras.layers.Dropout(0.1, name="Dropout_FFN")(ffn)

        # Residual
        x = tf.keras.layers.LayerNormalization(epsilon=1e-6, name="Norm_FFN")(x + ffn)

        # --- Global Pooling dan Concatenate ---
        avg_pool = tf.keras.layers.GlobalAveragePooling1D(name="AvgPool")(x)
        max_pool = tf.keras.layers.GlobalMaxPooling1D(name="MaxPool")(x)
        x = tf.keras.layers.Concatenate(name="Concatenate")([avg_pool, max_pool])

        # --- Dense Head (Predictor) ---
        x = tf.keras.layers.Dense(64, activation='relu', name="Dense_64")(x)
        x = tf.keras.layers.Dropout(0.2, name="Dropout_Final")(x)
        output = tf.keras.layers.Dense(1, name="Output_Layer")(x)

        model = tf.keras.Model(inputs=seq_input, outputs=output, name="LSTM_Transformer_Model")
        model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.001), loss='mse')
        return model

    def train_model(self) -> Dict[str, Any]:
        """Melakukan preprocessing, scaling, dan training model."""
        global GLOBAL_MODEL, GLOBAL_SCALER, GLOBAL_SEQ_LENGTH
        
        daily_df = self._load_data()
        values = daily_df[["ImportVA"]].values.astype(float)
        
        train_ratio = 0.8
        split_idx = int(len(values) * train_ratio)
        train_values = values[:split_idx]

        # Tentukan seq_length
        seq_length = min(self.DEFAULT_SEQ_LENGTH, len(train_values) - 1)
        if seq_length < 2:
            raise ValueError("Data training terlalu sedikit untuk dibuat sequence.")
            
        GLOBAL_SEQ_LENGTH = seq_length
        
        # Scaling
        scaler = MinMaxScaler()
        train_scaled = scaler.fit_transform(train_values)
        test_scaled  = scaler.transform(values[split_idx:])
        scaled_full = np.concatenate([train_scaled, test_scaled], axis=0)
        
        GLOBAL_SCALER = scaler

        # Sequence creation
        X_all, y_all = self._create_sequences(scaled_full, seq_length)
        
        test_start = len(train_scaled) - seq_length
        X_train, y_train = X_all[:test_start], y_all[:test_start]
        
        # Reshape ke format [samples, timesteps, features]
        X_train = X_train.reshape((X_train.shape[0], seq_length, 1))

        # Build Model
        model = self._build_lstm_transformer(seq_length, n_features=1)
        
        # Callbacks
        early_stop = tf.keras.callbacks.EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True, verbose=0)
        reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(monitor='val_loss', patience=7, factor=0.3, min_lr=1e-6, verbose=0)

        # Training
        history = model.fit(
            X_train, y_train,
            epochs=150,
            batch_size=32,
            validation_split=0.2,
            callbacks=[early_stop, reduce_lr],
            verbose=0 # Nonaktifkan output training di API
        )
        
        GLOBAL_MODEL = model
        
        # Ambil metrik terakhir
        val_loss = history.history['val_loss'][-1] if history.history['val_loss'] else None
        
        # return {
        #     "status": "Trained",
        #     "message": "Model berhasil dilatih dan disimpan di global state.",
        #     "data_length": len(daily_df),
        #     "sequence_length": seq_length,
        #     "last_validation_loss_mse": f"{val_loss:.6f}" if val_loss else "N/A"
        # }
        return self.run_forecast(df=daily_df, forecast_steps=30)

    def run_forecast(self, df: pd.DataFrame, forecast_steps: int) -> ForecastResult:
        """Melakukan forecast multi-step ke depan."""
        global GLOBAL_MODEL, GLOBAL_SCALER, GLOBAL_SEQ_LENGTH

        if GLOBAL_MODEL is None or GLOBAL_SCALER is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Model belum dilatih.")
        
        # Muat data full untuk mendapatkan sequence terakhir dan tanggal terakhir
        daily_df = df
        values = daily_df[["ImportVA"]].values.astype(float)
        
        # Ambil sequence terakhir dari data FULL (sudah diskalakan oleh GLOBAL_SCALER)
        last_seq = GLOBAL_SCALER.transform(values[-GLOBAL_SEQ_LENGTH:]).reshape(1, GLOBAL_SEQ_LENGTH, 1)

        forecast_scaled = []

        for _ in range(forecast_steps):
            # Prediksi satu langkah ke depan
            next_scaled = GLOBAL_MODEL.predict(last_seq, verbose=0)[0, 0]
            forecast_scaled.append([next_scaled])

            # Geser window (multi-step prediction)
            new_seq = np.append(last_seq[:, 1:, :], [[[next_scaled]]], axis=1)
            last_seq = new_seq

        forecast_scaled_arr = np.array(forecast_scaled)
        
        # Balik ke satuan asli
        forecast_orig_arr = GLOBAL_SCALER.inverse_transform(forecast_scaled_arr).reshape(-1)

        # Buat tanggal ke depan
        last_date = daily_df['Date'].iloc[-1]
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
