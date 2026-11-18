"""Stage 3: temporal split, baselines and models, metrics.

Split: train = 2011, valid = H1 2012, test = H2 2012 (dates in src/config.py).
Models are fit on train only. Nothing is tuned against valid or test.

Run: python -m src.train
"""
import json

import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.config import METRICS, TARGET, TRAIN_END, VALID_END
from src.features import build_features, feature_columns
from src.ingest import load_raw


class Persistence:
    """Predict yesterday's count: the cnt_lag_1 feature, unchanged.

    scikit-learn has no estimator for this, so it is written out. fit() is a
    no-op because the rule has no parameters to learn.
    """

    def fit(self, X, y=None):
        return self

    def predict(self, X):
        return X["cnt_lag_1"].to_numpy()


MODELS = {
    "baseline_mean": DummyRegressor(strategy="mean"),
    "baseline_persistence": Persistence(),
    "ridge": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
    "hgb": HistGradientBoostingRegressor(random_state=0),
}


def temporal_split(df: pd.DataFrame):
    """Return (train, valid, test) split on dteday, in that time order."""
    d = df["dteday"]
    train = df[d <= pd.Timestamp(TRAIN_END)]
    valid = df[(d > pd.Timestamp(TRAIN_END)) & (d <= pd.Timestamp(VALID_END))]
    test = df[d > pd.Timestamp(VALID_END)]
    return train, valid, test


def evaluate(model, cols, train, valid, test) -> dict:
    """Fit on train; score valid and test. R^2 and MAE, rides per day."""
    model.fit(train[cols], train[TARGET])
    out = {}
    for name, part in (("valid", valid), ("test", test)):
        pred = model.predict(part[cols])
        out[name] = {
            "r2": round(float(r2_score(part[TARGET], pred)), 4),
            "mae": round(float(mean_absolute_error(part[TARGET], pred)), 1),
        }
    return out


if __name__ == "__main__":
    feats = build_features(load_raw())
    cols = feature_columns(feats)
    train, valid, test = temporal_split(feats)

    metrics = {
        name: evaluate(model, cols, train, valid, test)
        for name, model in MODELS.items()
    }

    METRICS.parent.mkdir(parents=True, exist_ok=True)
    METRICS.write_text(json.dumps(metrics, indent=2) + "\n")
    print(f"OK train: {len(train)} train / {len(valid)} valid / {len(test)} test rows -> {METRICS.name}")
    for name, m in metrics.items():
        print(f"  {name:22s} valid R2 {m['valid']['r2']:+.4f} MAE {m['valid']['mae']:8.1f} | "
              f"test R2 {m['test']['r2']:+.4f} MAE {m['test']['mae']:8.1f}")
