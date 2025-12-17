from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import timedelta, datetime
from sklearn.preprocessing import MinMaxScaler

from app.dependencies.response import response_ok
from app.models.hasil_forecast_model import HasilForecast
from app.models.hasil_kalkulasi_model import HasilKalkulasi

import numpy as np
import pandas as pd
import tensorflow as tf

# =========================================================
# GLOBAL MODEL CACHE
# =========================================================
GLOBAL_MODEL_CACHE: Dict[int, Dict[str, Any]] = {}


# =========================================================
# AGENTIC HYBRID CALLBACK (SIMPLE)
# - monitor val_loss
# - if improvement < threshold for `patience` epochs -> amplify LR
# =========================================================
class AgenticHybridCallback(tf.keras.callbacks.Callback):
    def __init__(self, monitor="val_loss", threshold=1e-4, patience=4, amplify_factor=1.15):
        super().__init__()
        self.monitor = monitor
        self.threshold = threshold
        self.patience = patience
        self.amplify_factor = amplify_factor
        self.best = float("inf")
        self.wait = 0

    def on_epoch_end(self, epoch, logs=None):
        logs = logs or {}
        current = logs.get(self.monitor)
        if current is None:
            return

        # if significant improvement reset wait
        if (self.best - current) > self.threshold:
            self.best = current
            self.wait = 0
        else:
            self.wait += 1

        if self.wait >= self.patience:
            # amplify learning rate safely
            opt = self.model.optimizer
            try:
                old_lr = float(tf.keras.backend.get_value(opt.learning_rate))
                new_lr = old_lr * self.amplify_factor
                opt.learning_rate.assign(new_lr)
                print(f"[AgenticHybridCallback] LR amplified: {old_lr:.6f} -> {new_lr:.6f}")
            except Exception as e:
                print("[AgenticHybridCallback] Failed to amplify LR:", e)
            finally:
                self.wait = 0


# =========================================================
# ForecastFormula (integrated with dosen's winsorize + seq creation)
# =========================================================
class ForecastFormula:
    """
    Pipeline:
      - load data from HasilKalkulasi
      - winsorize (IQR clamping) like dosen
      - MinMax scale
      - create sequences with seq_length = min(7, len(data)-1)
      - build/train model (LSTM + Attention + HybridActivation)
      - forecast N steps (recursive)
      - delete old HasilForecast rows for trafo_id
      - insert up to 90 new forecast rows
    """

    # -------------------------
    # Hybrid activation: trainable mixture (Swish + Mish + GELU)
    # -------------------------
    class HybridActivation(tf.keras.layers.Layer):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

        def build(self, input_shape):
            self.w = self.add_weight(
                name="hybrid_weights",
                shape=(3,),
                initializer=tf.keras.initializers.Ones(),
                trainable=True,
            )
            super().build(input_shape)

        def call(self, x):
            w_norm = tf.nn.softmax(self.w)
            ws, wm, wg = w_norm[0], w_norm[1], w_norm[2]

            swish_x = x * tf.nn.sigmoid(x)
            mish_x = x * tf.math.tanh(tf.math.softplus(x))
            gelu_x = 0.5 * x * (1.0 + tf.math.erf(x / tf.sqrt(2.0)))

            return ws * swish_x + wm * mish_x + wg * gelu_x

        def get_config(self):
            return super().get_config()

    # -------------------------
    # constructor
    # -------------------------
    def __init__(self, db: Session, trafo_id: int):
        self.db = db
        self.trafo_id = trafo_id
        # note: seq_length will be derived from data like dosen (min 7)
        self.MIN_DATA_ROWS = 30

    # -------------------------
    # load & winsorize data (IQR clamping)
    # -------------------------
    def _load_data(self) -> pd.DataFrame:
        records = (
            self.db.query(HasilKalkulasi)
            .filter(HasilKalkulasi.id_trafo == self.trafo_id)
            .order_by(HasilKalkulasi.waktu_kalkulasi.desc())
            .all()
        )

        if not records:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tidak ada hasil kalkulasi untuk trafo id {self.trafo_id}"
            )

        df = pd.DataFrame([{"Date": r.waktu_kalkulasi, "ImportVA": r.importwh/r.cosphi} for r in records])
        if len(df) < self.MIN_DATA_ROWS:
            raise ValueError(f"Minimal {self.MIN_DATA_ROWS} hari data diperlukan.")

        # Dosen: outlier detection via IQR and winsorize (clamp)
        numeric_cols = df.select_dtypes(include=["float64", "int64"]).columns
        for col in numeric_cols:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - 1.5 * IQR
            upper = Q3 + 1.5 * IQR
            df[col] = df[col].clip(lower=lower, upper=upper)

        return df.sort_values(by="Date").reset_index(drop=True)

    # -------------------------
    # build model (LSTM + Attention + Hybrid)
    # -------------------------
    def _build_lstm_transformer(self, seq_length, n_features=1):
        seq_input = tf.keras.Input(shape=(seq_length, n_features))
        D_MODEL = 64
        hybrid = self.HybridActivation()

        # LSTM encoder
        x = tf.keras.layers.LSTM(D_MODEL, return_sequences=True)(seq_input)
        x = tf.keras.layers.Dropout(0.2)(x)

        # hybrid activation after LSTM
        x = hybrid(x)

        # Attention block
        attn = tf.keras.layers.MultiHeadAttention(num_heads=1, key_dim=64)(x, x)
        attn = tf.keras.layers.Dense(64)(attn)
        x = tf.keras.layers.LayerNormalization(epsilon=1e-6)(x + attn)

        # FFN with hybrid activation twice
        ffn = tf.keras.layers.Dense(128)(x)
        ffn = hybrid(ffn)
        ffn = tf.keras.layers.Dropout(0.2)(ffn)
        ffn = tf.keras.layers.Dense(64)(ffn)
        ffn = hybrid(ffn)

        x = tf.keras.layers.LayerNormalization(epsilon=1e-6)(x + ffn)

        # pooling + head
        x_pool = tf.keras.layers.GlobalAveragePooling1D()(x)
        out = tf.keras.layers.Dense(1)(x_pool)

        model = tf.keras.Model(inputs=seq_input, outputs=out)
        model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3), loss="mae")
        return model

    # -------------------------
    # train model (integrated dosen pipeline with AgenticHybridCallback)
    # -------------------------
    def train_model(self, force_retrain: bool = False):
        global GLOBAL_MODEL_CACHE

        df = self._load_data()
        values = df[["ImportVA"]].values.astype(float)
        last_date = df["Date"].iloc[-1]

        cache = GLOBAL_MODEL_CACHE.get(self.trafo_id)
        if cache and cache["last_date"] == last_date and not force_retrain:
            return self.run_forecast(df=df, forecast_steps=90)

        # ---------- DOSEN SEQUENCE LOGIC ----------
        scaler = MinMaxScaler()
        scaled_data = scaler.fit_transform(df[["ImportVA"]])

        seq_length = min(7, len(scaled_data) - 1)
        if seq_length < 2:
            raise ValueError("Data harian terlalu sedikit untuk sequence (seq_length < 2).")

        # create sequences like dosen
        def create_sequences(data, seq_length):
            X, y = [], []
            for i in range(seq_length, len(data)):
                X.append(data[i - seq_length:i])
                y.append(data[i])
            return np.array(X), np.array(y)

        X, y = create_sequences(scaled_data, seq_length)
        if X.size == 0:
            raise ValueError("Sequence tidak dapat dibuat. Periksa jumlah data dan seq_length.")

        X = X.reshape((X.shape[0], seq_length, 1))
        y = y.reshape((-1,))  # flatten targets

        # split
        split = int(0.8 * len(X))
        X_train, y_train = X[:split], y[:split]

        # build + train
        model = self._build_lstm_transformer(seq_length)

        early_stop = tf.keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=7, restore_best_weights=True
        )
        reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss", patience=5, factor=0.3, min_lr=1e-6
        )
        agentic_cb = AgenticHybridCallback(
            monitor="val_loss", threshold=1e-4, patience=4, amplify_factor=1.15
        )

        model.fit(
            X_train,
            y_train,
            epochs=80,
            batch_size=32,
            validation_split=0.2,
            callbacks=[early_stop, reduce_lr, agentic_cb],
            verbose=0
        )

        # save to cache
        GLOBAL_MODEL_CACHE[self.trafo_id] = {
            "model": model,
            "scaler": scaler,
            "seq_length": seq_length,
            "last_date": last_date,
        }

        return self.run_forecast(df=df, forecast_steps=90)

    # -------------------------
    # run_forecast + save to DB
    # -------------------------
    def run_forecast(self, df: pd.DataFrame, forecast_steps: int):
        cache = GLOBAL_MODEL_CACHE.get(self.trafo_id)
        if not cache:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Model belum dilatih.")

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

        results = [{"date": d.strftime("%Y-%m-%d"), "value": float(v)} for d, v in zip(forecast_dates, forecast_orig)]

        # Delete old rows for this trafo_id
        try:
            self.db.query(HasilForecast).filter(HasilForecast.id_trafo == self.trafo_id).delete()
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Error deleting old forecast data: {e}")

        # Insert up to 90 new rows
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
            raise HTTPException(status_code=500, detail=f"Error inserting hasil forecast: {e}")

        return response_ok(data={"date": results[-1]["date"], "value": float(results[-1]["value"])/1000}, message="Success")
