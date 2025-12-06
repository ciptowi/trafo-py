from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import timedelta, datetime
from sklearn.preprocessing import MinMaxScaler

from app.dependencies.response import response_ok
from app.models.hasil_forecast_model import HasilForecast
from app.models.hasil_kalkulasi_model import HasilKalkulasi
from app.schemas.forecast_schema import ForecastResult

import numpy as np
import pandas as pd
import tensorflow as tf


# =========================================================
# GLOBAL MODEL CACHE
# =========================================================
GLOBAL_MODEL_CACHE: Dict[int, Dict[str, Any]] = {}


# =========================================================
# AGENTIC HYBRID CALLBACK (SIMPLE)
# =========================================================
class AgenticHybridCallback(tf.keras.callbacks.Callback):
    def __init__(self, monitor="val_loss", patience=5, threshold=0.005, amplify_factor=0.05):
        super().__init__()
        self.monitor = monitor
        self.patience = patience
        self.threshold = threshold
        self.amplify_factor = amplify_factor
        self.best = float("inf")
        self.wait = 0

    def on_epoch_end(self, epoch, logs=None):
        logs = logs or {}
        current = logs.get(self.monitor)

        if current is None:
            return

        # Ada perbaikan signifikan
        if self.best - current > self.threshold:
            self.best = current
            self.wait = 0
        else:
            self.wait += 1

        # Setelah stagnan beberapa epoch → tingkatkan LR
        if self.wait >= self.patience:
            old_lr = float(tf.keras.backend.get_value(self.model.optimizer.learning_rate))
            new_lr = old_lr * self.amplify_factor

            # UPDATE LR
            self.model.optimizer.learning_rate.assign(new_lr)

            print(f"\n[AgenticHybridCallback] LR amplified {old_lr:.6f} → {new_lr:.6f}")
            self.wait = 0


# =========================================================
# CLASS FORECAST FORMULA
# =========================================================
class ForecastFormula:

    # =========================================================
    # 1. HYBRID ACTIVATION (Swish + Mish + GELU) — trainable
    # =========================================================
    class HybridActivation(tf.keras.layers.Layer):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

        def build(self, input_shape):
            self.w = self.add_weight(
                name='hybrid_weights',
                shape=(3,),
                initializer=tf.keras.initializers.Ones(),
                trainable=True
            )
            super().build(input_shape)

        def call(self, x):
            w_norm = tf.nn.softmax(self.w)   # normalisasi bobot
            ws, wm, wg = w_norm[0], w_norm[1], w_norm[2]

            swish_x = x * tf.nn.sigmoid(x)
            mish_x = x * tf.math.tanh(tf.math.softplus(x))
            gelu_x = 0.5 * x * (1.0 + tf.math.erf(x / tf.sqrt(2.0)))

            return ws * swish_x + wm * mish_x + wg * gelu_x

        def get_config(self):
            return super().get_config()


    # =========================================================
    # 2. CONSTRUCTOR
    # =========================================================
    def __init__(self, db: Session, trafo_id: int):
        self.db = db
        self.trafo_id = trafo_id
        self.MIN_DATA_ROWS = 30
        self.DEFAULT_SEQ_LENGTH = 21

    # =========================================================
    # 3. LOAD DATA
    # =========================================================
    def _load_data(self) -> pd.DataFrame:
        data_records = (
            self.db.query(HasilKalkulasi)
            .filter(HasilKalkulasi.id_trafo == self.trafo_id)
            .order_by(HasilKalkulasi.waktu_kalkulasi.desc())
            .all()
        )

        if not data_records:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tidak ada hasil kalkulasi untuk trafo id {self.trafo_id}"
            )

        daily_df = pd.DataFrame([
            {"Date": r.waktu_kalkulasi, "ImportVA": r.total_kva}
            for r in data_records
        ])

        if len(daily_df) < self.MIN_DATA_ROWS:
            raise ValueError(f"Minimal {self.MIN_DATA_ROWS} hari data diperlukan.")

        # Outlier removal
        q1 = daily_df["ImportVA"].quantile(0.25)
        q3 = daily_df["ImportVA"].quantile(0.75)
        iqr = q3 - q1
        daily_df["ImportVA"] = daily_df["ImportVA"].clip(q1 - 1.5*iqr, q3 + 1.5*iqr)

        return daily_df.sort_values(by="Date").reset_index(drop=True)

    # =========================================================
    # 4. BUILD MODEL
    # =========================================================
    def _build_lstm_transformer(self, seq_length, n_features=1):
        seq_input = tf.keras.Input(shape=(seq_length, n_features))
        hybrid = self.HybridActivation()
        D_MODEL = 64

        # === LSTM Encoder ===
        x = tf.keras.layers.LSTM(D_MODEL, return_sequences=True)(seq_input)
        x = tf.keras.layers.Dropout(0.2)(x)

        # BUG-FIX: harus hybrid(x), bukan hybrid()(x)
        x = hybrid(x)

        # === Transformer Attention ===
        attn = tf.keras.layers.MultiHeadAttention(num_heads=1, key_dim=64)(x, x)
        attn = tf.keras.layers.Dense(64)(attn)
        x = tf.keras.layers.LayerNormalization(epsilon=1e-6)(x + attn)

        # === FFN Hybrid ===
        ffn = tf.keras.layers.Dense(128)(x)
        ffn = hybrid(ffn)
        ffn = tf.keras.layers.Dropout(0.2)(ffn)
        ffn = tf.keras.layers.Dense(64)(ffn)
        ffn = hybrid(ffn)

        x = tf.keras.layers.LayerNormalization(epsilon=1e-6)(x + ffn)

        # === Global Pool ===
        x_pool = tf.keras.layers.GlobalAveragePooling1D()(x)
        output = tf.keras.layers.Dense(1)(x_pool)

        model = tf.keras.Model(inputs=seq_input, outputs=output)

        model.compile(
            optimizer=tf.keras.optimizers.Adam(1e-3),
            loss="mae"
        )
        return model

    # =========================================================
    # 5. TRAIN MODEL
    # =========================================================
    def train_model(self, force_retrain=False):
        global GLOBAL_MODEL_CACHE

        daily_df = self._load_data()
        values = daily_df[["ImportVA"]].values.astype(float)
        last_data_date = daily_df["Date"].iloc[-1]

        cache = GLOBAL_MODEL_CACHE.get(self.trafo_id)

        # Skip training jika tidak ada data baru
        if cache and cache["last_date"] == last_data_date and not force_retrain:
            return self.run_forecast(df=daily_df, forecast_steps=90)

        # Scaling
        train_ratio = 0.8
        split_idx = int(len(values) * train_ratio)

        train_values = values[:split_idx]
        seq_length = min(self.DEFAULT_SEQ_LENGTH, len(train_values) - 1)
        if seq_length < 2:
            raise ValueError("Data terlalu sedikit.")

        scaler = MinMaxScaler()
        train_scaled = scaler.fit_transform(train_values)
        test_scaled = scaler.transform(values[split_idx:])
        scaled_full = np.concatenate([train_scaled, test_scaled], axis=0)

        # Sequence generation
        indices = np.arange(len(scaled_full) - seq_length)
        X_all = np.array([scaled_full[i:i + seq_length] for i in indices])
        y_all = scaled_full[seq_length:]

        train_end = split_idx - seq_length
        X_train, y_train = X_all[:train_end], y_all[:train_end]
        X_train = X_train.reshape((X_train.shape[0], seq_length, 1))

        # Build model
        model = self._build_lstm_transformer(seq_length)

        early_stop = tf.keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=7, restore_best_weights=True
        )
        reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(
        monitor="val_loss", patience=5, factor=0.3, min_lr=1e-6
        )

        # ✅ Tambahkan AgenticHybridCallback
        agentic_cb = AgenticHybridCallback(
            monitor="val_loss",
            patience=4,
            threshold=0.005,
            amplify_factor=0.05
        )

        model.fit(
            X_train,
            y_train,
            epochs=100,
            batch_size=8,
            validation_split=0.1,
            callbacks=[early_stop, reduce_lr, agentic_cb],
            verbose=0
        )

        print("=== AFTER TRAINING ===")
        for layer in model.layers:
            if isinstance(layer, self.HybridActivation):
                print(layer.name, layer.get_weights())

        GLOBAL_MODEL_CACHE[self.trafo_id] = {
            "model": model,
            "scaler": scaler,
            "seq_length": seq_length,
            "last_date": last_data_date,
        }

        return self.run_forecast(df=daily_df, forecast_steps=90)

    # =========================================================
    # 6. FORECAST + SAVE DB
    # =========================================================
    def run_forecast(self, df: pd.DataFrame, forecast_steps: int):
        cache = GLOBAL_MODEL_CACHE.get(self.trafo_id)

        if not cache:
            raise HTTPException(400, "Model belum dilatih.")

        model = cache["model"]
        scaler = cache["scaler"]
        seq_length = cache["seq_length"]

        values = df[["ImportVA"]].values.astype(float)
        last_seq = scaler.transform(values[-seq_length:]).reshape(1, seq_length, 1)

        forecast_scaled = []

        for _ in range(forecast_steps):
            next_scaled = model.predict(last_seq, verbose=0)[0, 0]
            forecast_scaled.append([next_scaled])
            last_seq = np.append(last_seq[:, 1:, :], [[[next_scaled]]], axis=1)

        forecast_orig = scaler.inverse_transform(np.array(forecast_scaled)).reshape(-1)

        last_date = df["Date"].iloc[-1]
        forecast_dates = [last_date + timedelta(days=i) for i in range(1, forecast_steps + 1)]

        results = [
            {"date": d.strftime("%Y-%m-%d"), "value": float(v)}
            for d, v in zip(forecast_dates, forecast_orig)
        ]

        # DELETE EXISTING FORECAST RECORDS
        try:
            self.db.query(HasilForecast).filter(
                HasilForecast.id_trafo == self.trafo_id
            ).delete()
            self.db.commit()
        except Exception as e:
            print("Error delete:", e)
            raise HTTPException(500, "Error deleting old forecast data")

        # INSERT NEW FORECAST
        rows = []
        for i in range(min(90, len(results))):
            rows.append(
                HasilForecast(
                    id_trafo=self.trafo_id,
                    tanggal_forecast=datetime.strptime(results[i]["date"], "%Y-%m-%d"),
                    hasil_forecast=float(results[i]["value"]),
                )
            )

        try:
            self.db.bulk_save_objects(rows)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise HTTPException(500, f"Error insert hasil forecast: {e}")

        return response_ok(
            data={"date": results[-1]["date"], "value": results[-1]["value"]},
            message="Success"
        )
