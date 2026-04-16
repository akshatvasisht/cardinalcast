"""
Model Evaluation Module for CardinalCast ML Pipeline.

Loads trained quantile regression models and evaluates them on a held-out
test set (last 20% of the time-ordered dataset). Produces:
  - Comprehensive metrics JSON (quantile coverage, pinball loss, MAE, RMSE, bias)
  - Feature importance rankings per target
  - Evaluation plots (prediction vs actual, residual distribution, coverage bands)
  - Interval width by month chart (high_temp only -- blog asset)

Usage:
    python evaluate_models.py
"""

import json
import warnings
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

import feature_engineering

# ---------------------------------------------------------------------------
# Site-matched monochrome palette (mirrors globals.css)
# ---------------------------------------------------------------------------
BK  = "#000000"   # --foreground / --border-color
GY  = "#696969"   # --muted-foreground (neutral-500)
MT  = "#f5f5f5"   # --muted (neutral-100)
MT2 = "#d4d4d4"   # slightly darker muted for secondary fills
WH  = "#ffffff"   # --background

SITE_STYLE = {
    "font.family":       "sans-serif",
    "font.size":         9,
    "axes.facecolor":    WH,
    "figure.facecolor":  WH,
    "axes.edgecolor":    BK,
    "axes.linewidth":    0.8,
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "axes.grid":         True,
    "grid.color":        MT,
    "grid.linewidth":    0.6,
    "grid.linestyle":    "-",
    "xtick.color":       BK,
    "ytick.color":       BK,
    "xtick.labelsize":   8,
    "ytick.labelsize":   8,
    "text.color":        BK,
    "axes.labelcolor":   BK,
    "axes.labelsize":    9,
    "axes.titlesize":    10,
    "axes.titleweight":  "bold",
    "lines.linewidth":   1.2,
    "legend.frameon":    True,
    "legend.framealpha": 1.0,
    "legend.edgecolor":  BK,
    "legend.fontsize":   7,
    "figure.dpi":        150,
}

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT  = Path(__file__).resolve().parent.parent
MODEL_DIR  = REPO_ROOT / "backend" / "odds_service" / "models"
DATA_PATH  = REPO_ROOT / "data" / "cleaned_weather_data.csv"
OUTPUT_DIR = REPO_ROOT / "ml_training" / "evaluation"

# Site public images dir -- interval width chart is used by the blog post
SITE_IMAGES_DIR = Path("/home/aksha/projects/site/public/images")

TARGETS = [
    {"name": "high_temp",      "target_col": "high_temp",     "unit": "°F"},
    {"name": "avg_wind_speed", "target_col": "avg_wind_speed", "unit": "mph"},
    {"name": "precipitation",  "target_col": "precip",         "unit": "in"},
]

TEST_FRACTION = 0.20
QUANTILES     = [("p10", 0.10), ("p50", 0.50), ("p90", 0.90)]

MONTH_LABELS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def pinball_loss(y_true, y_pred, quantile):
    """Pinball (quantile) loss -- proper scoring rule for quantile regression."""
    delta = y_true - y_pred
    return np.mean(np.where(delta >= 0, quantile * delta, (quantile - 1) * delta))


def load_models(target_name):
    """Load RFECV selector and P10/P50/P90 models for a target."""
    rfecv  = joblib.load(MODEL_DIR / f"{target_name}_rfecv.pkl")
    models = {
        q: joblib.load(MODEL_DIR / f"{target_name}_{q}_model.pkl")
        for q in ("p10", "p50", "p90")
    }
    return rfecv, models


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate_target(df, target_cfg):
    """Evaluate all quantile models for a single target on the test split."""
    target_name = target_cfg["name"]
    target_col  = target_cfg["target_col"]

    rfecv, models = load_models(target_name)
    feature_names = rfecv.feature_names_in_

    X_all = df.reindex(columns=feature_names, fill_value=0)
    y_all = df[target_col].values

    mask  = ~np.isnan(y_all)
    X_all = X_all[mask]
    y_all = y_all[mask]

    split_idx  = int(len(y_all) * (1 - TEST_FRACTION))
    X_test     = X_all.iloc[split_idx:]
    y_test     = y_all[split_idx:]
    dates_test = df.loc[mask, "date"].iloc[split_idx:].reset_index(drop=True)

    X_test_rfe = rfecv.transform(X_test)
    preds      = {q: models[q].predict(X_test_rfe) for q in ("p10", "p50", "p90")}

    # Regression metrics (P50)
    metrics = {"target": target_name, "test_samples": int(len(y_test))}
    metrics["p50_mae"]  = round(float(mean_absolute_error(y_test, preds["p50"])), 4)
    metrics["p50_rmse"] = round(float(np.sqrt(mean_squared_error(y_test, preds["p50"]))), 4)
    metrics["p50_bias"] = round(float(np.mean(preds["p50"] - y_test)), 4)

    # Pinball loss per quantile
    for q_label, alpha in QUANTILES:
        metrics[f"{q_label}_pinball"] = round(
            float(pinball_loss(y_test, preds[q_label], alpha)), 4
        )

    # Empirical calibration: fraction of actuals below each quantile prediction
    calibration = {}
    for q_label, _ in QUANTILES:
        calibration[q_label] = round(float(np.mean(y_test < preds[q_label])), 4)
    metrics["calibration"] = calibration

    # P10-P90 interval coverage and width
    in_range = (y_test >= preds["p10"]) & (y_test <= preds["p90"])
    metrics["p10_p90_coverage"]      = round(float(np.mean(in_range)), 4)
    widths = preds["p90"] - preds["p10"]
    metrics["interval_width_mean"]   = round(float(np.mean(widths)), 4)
    metrics["interval_width_median"] = round(float(np.median(widths)), 4)

    # Feature importances (P50 model)
    importance_scores = models["p50"].feature_importances_
    selected_features = np.array(feature_names)[rfecv.support_]
    feat_imp = sorted(
        zip(selected_features, importance_scores),
        key=lambda x: x[1], reverse=True,
    )
    metrics["top_features"] = [
        {"feature": str(f), "importance": round(float(v), 4)}
        for f, v in feat_imp[:15]
    ]
    metrics["n_features_selected"] = int(rfecv.n_features_)
    metrics["n_features_total"]    = len(feature_names)

    return metrics, preds, y_test, dates_test, feat_imp


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def plot_predictions(target_cfg, preds, y_test, output_dir):
    """2x2 evaluation grid: scatter, residuals, coverage band, QQ."""
    target_name = target_cfg["name"]
    unit        = target_cfg["unit"]

    with plt.rc_context(SITE_STYLE):
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        fig.suptitle(
            f"{target_name}  |  model evaluation  (n={len(y_test):,})",
            fontsize=10, fontweight="bold", y=1.01,
        )

        lo = float(min(y_test.min(), preds["p50"].min()))
        hi = float(max(y_test.max(), preds["p50"].max()))

        # Actual vs P50 scatter
        ax = axes[0, 0]
        ax.scatter(y_test, preds["p50"], s=3, alpha=0.12, color=BK, linewidths=0)
        ax.plot([lo, hi], [lo, hi], color=GY, linewidth=0.8, linestyle="--", label="perfect")
        ax.set_xlabel(f"actual ({unit})")
        ax.set_ylabel(f"predicted P50 ({unit})")
        ax.set_title("actual vs predicted")
        ax.legend()

        # Residual histogram
        ax = axes[0, 1]
        residuals = preds["p50"] - y_test
        ax.hist(residuals, bins=60, color=BK, edgecolor="none", alpha=0.75)
        ax.axvline(0, color=GY, linewidth=1.0, linestyle="--",
                   label=f"bias = {np.mean(residuals):.2f}")
        ax.set_xlabel(f"residual ({unit})")
        ax.set_ylabel("count")
        ax.set_title("residual distribution")
        ax.legend()

        # Coverage band (last 200 days)
        ax = axes[1, 0]
        n_show = min(200, len(y_test))
        idx    = np.arange(len(y_test) - n_show, len(y_test))
        ax.fill_between(idx, preds["p10"][idx], preds["p90"][idx],
                        alpha=0.15, color=BK, label="P10–P90")
        ax.plot(idx, preds["p90"][idx], color=MT2, linewidth=0.6)
        ax.plot(idx, preds["p10"][idx], color=MT2, linewidth=0.6)
        ax.plot(idx, y_test[idx],       color=BK,  linewidth=0.7, label="actual")
        ax.plot(idx, preds["p50"][idx], color=GY,  linewidth=0.7, linestyle="--", label="P50")
        ax.set_xlabel("test index (last 200 days)")
        ax.set_ylabel(f"{unit}")
        ax.set_title("prediction interval")
        ax.legend()

        # QQ plot
        ax = axes[1, 1]
        ax.plot(np.sort(y_test), np.sort(preds["p50"]),
                ".", markersize=2, color=BK, alpha=0.5)
        ax.plot([lo, hi], [lo, hi], color=GY, linewidth=0.8, linestyle="--")
        ax.set_xlabel(f"sorted actual ({unit})")
        ax.set_ylabel(f"sorted predicted ({unit})")
        ax.set_title("Q–Q plot (P50)")

        fig.tight_layout()
        path = output_dir / f"{target_name}_evaluation.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
    print(f"  Saved: {path.relative_to(REPO_ROOT)}")


def plot_feature_importance(target_name, feat_imp, output_dir):
    """Horizontal bar chart -- top 15 features by gain."""
    top    = feat_imp[:15]
    names  = [f for f, _ in top]
    values = [v for _, v in top]

    with plt.rc_context(SITE_STYLE):
        fig, ax = plt.subplots(figsize=(7, 5))
        y_pos  = np.arange(len(names))
        colors = [BK if i < 3 else GY for i in range(len(names))]
        ax.barh(y_pos, values, color=colors, edgecolor="none", height=0.65)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(names, fontsize=7)
        ax.invert_yaxis()
        ax.set_xlabel("importance (gain)")
        ax.set_title(f"{target_name}  |  top 15 features  (P50 model)")
        ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f"))
        fig.tight_layout()
        path = output_dir / f"{target_name}_feature_importance.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
    print(f"  Saved: {path.relative_to(REPO_ROOT)}")


def plot_interval_width_by_month(df, output_dir):
    """
    Bar chart of P90-P10 interval width by calendar month for high temperature.

    Demonstrates that the model adapts its uncertainty to seasonal weather
    regimes: wider intervals during volatile spring transition months, narrower
    during consistent summer heat. Used as a blog asset.

    Saves to output_dir and, if reachable, to the site's public images directory.
    """
    rfecv = joblib.load(MODEL_DIR / "high_temp_rfecv.pkl")
    p10   = joblib.load(MODEL_DIR / "high_temp_p10_model.pkl")
    p90   = joblib.load(MODEL_DIR / "high_temp_p90_model.pkl")

    feature_names = rfecv.feature_names_in_
    y    = df["high_temp"].values
    mask = ~np.isnan(y)

    X_all     = df.reindex(columns=feature_names, fill_value=0)[mask]
    dates_all = df.loc[mask, "date"].reset_index(drop=True)

    split   = int(len(X_all) * (1 - TEST_FRACTION))
    X_test  = rfecv.transform(X_all.iloc[split:])
    dates_t = dates_all.iloc[split:].reset_index(drop=True)

    widths = p90.predict(X_test) - p10.predict(X_test)
    months = dates_t.dt.month.values

    month_nums  = np.arange(1, 13)
    medians     = np.array([np.median(widths[months == m]) for m in month_nums])
    q25         = np.array([np.percentile(widths[months == m], 25) for m in month_nums])
    q75         = np.array([np.percentile(widths[months == m], 75) for m in month_nums])
    overall_med = np.median(widths)
    peak_idx    = int(np.argmax(medians))
    trough_idx  = int(np.argmin(medians))

    with plt.rc_context(SITE_STYLE):
        fig, ax = plt.subplots(figsize=(7, 4))
        x = np.arange(12)

        bar_colors             = [MT2] * 12
        bar_colors[peak_idx]   = BK
        bar_colors[trough_idx] = BK

        ax.bar(x, medians, width=0.6, color=bar_colors,
               edgecolor=BK, linewidth=0.6, zorder=3)
        ax.errorbar(x, medians,
                    yerr=[medians - q25, q75 - medians],
                    fmt="none", color=GY, linewidth=0.8,
                    capsize=3, capthick=0.8, zorder=4)

        ax.axhline(overall_med, color=GY, linewidth=0.8, linestyle="--", zorder=2)
        ax.text(11.5, overall_med + 0.3,
                f"median\n{overall_med:.1f}°F",
                ha="right", va="bottom", fontsize=7, color=GY)

        for idx, label in [(peak_idx, "peak"), (trough_idx, "trough")]:
            err_hi = q75[idx] - medians[idx]
            ax.text(idx, medians[idx] + err_hi + 0.4,
                    f"{medians[idx]:.1f}°F",
                    ha="center", va="bottom",
                    fontsize=7.5, fontweight="bold", color=BK)

        ax.set_xticks(x)
        ax.set_xticklabels(MONTH_LABELS)
        ax.set_ylabel("P90 – P10 interval width (°F)")
        ax.set_title("prediction uncertainty by month  |  high temperature")
        ax.set_ylim(0, medians.max() + (q75[peak_idx] - medians[peak_idx]) + 3)
        ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%g°F"))

        fig.tight_layout()

        save_paths = [output_dir / "interval_width_by_month.png"]
        if SITE_IMAGES_DIR.exists():
            save_paths.append(SITE_IMAGES_DIR / "interval_width_by_month.png")

        for path in save_paths:
            fig.savefig(path, dpi=150, bbox_inches="tight")
            print(f"  Saved: {path}")

        plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    warnings.filterwarnings("ignore", category=UserWarning)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading data...")
    df = pd.read_csv(DATA_PATH, parse_dates=["date"])
    print(f"  {len(df):,} rows loaded")

    print("Engineering features...")
    df = feature_engineering.engineer_features(df)

    all_metrics = {}

    for target_cfg in TARGETS:
        name = target_cfg["name"]
        print(f"\nEvaluating: {name}")

        metrics, preds, y_test, dates_test, feat_imp = evaluate_target(df, target_cfg)
        all_metrics[name] = metrics

        print(f"  Test samples : {metrics['test_samples']:,}")
        print(f"  P50 MAE      : {metrics['p50_mae']} {target_cfg['unit']}")
        print(f"  P50 RMSE     : {metrics['p50_rmse']} {target_cfg['unit']}")
        print(f"  P50 Bias     : {metrics['p50_bias']} {target_cfg['unit']}")
        print(f"  Coverage     : {metrics['p10_p90_coverage']:.1%}  (target ~80%)")
        print(f"  Interval     : {metrics['interval_width_mean']:.2f} {target_cfg['unit']} avg width")
        cal = metrics["calibration"]
        print(f"  Calibration  : P10={cal['p10']:.0%}  P50={cal['p50']:.0%}  P90={cal['p90']:.0%}  (ideal: 10/50/90%)")
        print(f"  Features     : {metrics['n_features_selected']}/{metrics['n_features_total']} selected by RFECV")

        plot_predictions(target_cfg, preds, y_test, OUTPUT_DIR)
        plot_feature_importance(name, feat_imp, OUTPUT_DIR)

    print("\nGenerating interval width by month chart...")
    plot_interval_width_by_month(df, OUTPUT_DIR)

    metrics_path = OUTPUT_DIR / "evaluation_metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(all_metrics, f, indent=2)
    print(f"\nSaved metrics : {metrics_path.relative_to(REPO_ROOT)}")
    print("Done.")


if __name__ == "__main__":
    main()
