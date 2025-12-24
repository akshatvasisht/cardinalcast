"""
Summarizes training metrics from JSON file into human-readable markdown tables.

This script reads the training_metrics.json file and generates:
1. A summary table with MAE and RMSE for each target/quantile combination
2. Detailed hyperparameter information for each model

Usage:
    python summarize_metrics.py
"""

import json
from pathlib import Path
from datetime import datetime


def load_metrics(metrics_file):
    """Load metrics from JSON file."""
    if not metrics_file.exists():
        print(f"Metrics file not found: {metrics_file}")
        return []

    with open(metrics_file, 'r') as f:
        return json.load(f)


def generate_summary_table(metrics):
    """Generate markdown summary table of model performance."""
    if not metrics:
        return "No metrics available.\n"

    # Sort by target and quantile
    metrics_sorted = sorted(metrics, key=lambda x: (x['target'], x['quantile']))

    # Build markdown table
    lines = []
    lines.append("## Model Performance Summary\n")
    lines.append("| Target | Quantile | MAE | RMSE | CV MAE | Features | Samples |")
    lines.append("|--------|----------|-----|------|--------|----------|---------|")

    for m in metrics_sorted:
        target = m['target'].replace('_', ' ').title()
        quantile = m['quantile'].upper()
        mae = f"{m['mae']:.4f}"
        rmse = f"{m['rmse']:.4f}"
        cv_mae = f"{m['best_cv_mae']:.4f}"
        n_features = m['n_features']
        n_samples = m['n_samples']

        lines.append(
            f"| {target} | {quantile} | {mae} | {rmse} | {cv_mae} | "
            f"{n_features} | {n_samples} |"
        )

    lines.append("")
    lines.append("**Metrics Legend:**")
    lines.append("- **MAE**: Mean Absolute Error (training set)")
    lines.append("- **RMSE**: Root Mean Squared Error (training set)")
    lines.append("- **CV MAE**: Cross-validated MAE (time series split)")
    lines.append("- **Features**: Number of features after RFECV selection")
    lines.append("- **Samples**: Training dataset size")
    lines.append("")

    return "\n".join(lines)


def generate_hyperparameter_details(metrics):
    """Generate detailed hyperparameter information."""
    if not metrics:
        return ""

    lines = []
    lines.append("## Hyperparameter Details\n")

    # Group by target
    targets = {}
    for m in metrics:
        target = m['target']
        if target not in targets:
            targets[target] = []
        targets[target].append(m)

    for target, target_metrics in sorted(targets.items()):
        lines.append(f"### {target.replace('_', ' ').title()}\n")

        for m in sorted(target_metrics, key=lambda x: x['quantile']):
            quantile = m['quantile'].upper()
            params = m['best_params']

            lines.append(f"**{quantile}:**")
            lines.append("```json")
            lines.append(json.dumps(params, indent=2))
            lines.append("```")
            lines.append("")

    return "\n".join(lines)


def generate_metadata(metrics):
    """Generate metadata about the training run."""
    if not metrics:
        return ""

    latest = max(metrics, key=lambda x: x['timestamp'])
    oldest = min(metrics, key=lambda x: x['timestamp'])

    lines = []
    lines.append("## Training Metadata\n")
    lines.append(f"- **Last Training Run**: {latest['timestamp']}")
    if oldest['timestamp'] != latest['timestamp']:
        lines.append(f"- **First Training Run**: {oldest['timestamp']}")
    lines.append(f"- **Total Models Trained**: {len(metrics)}")
    lines.append(f"- **Unique Targets**: {len(set(m['target'] for m in metrics))}")
    lines.append("")

    return "\n".join(lines)


def main():
    """Main entry point for metrics summarization."""
    # Locate metrics file
    script_dir = Path(__file__).resolve().parent
    metrics_file = script_dir / "metrics" / "training_metrics.json"

    print(f"Reading metrics from: {metrics_file}")

    # Load metrics
    metrics = load_metrics(metrics_file)

    if not metrics:
        print("No metrics to summarize.")
        return

    # Generate markdown report
    output_lines = []
    output_lines.append("# CardinalCast ML Training Metrics\n")
    output_lines.append(generate_metadata(metrics))
    output_lines.append(generate_summary_table(metrics))
    output_lines.append(generate_hyperparameter_details(metrics))

    # Write to file
    output_file = script_dir / "metrics" / "training_summary.md"
    with open(output_file, 'w') as f:
        f.write("\n".join(output_lines))

    print(f"\nSummary written to: {output_file}")
    print("\n" + "=" * 60)
    print("\n".join(output_lines[:50]))  # Print first 50 lines to console
    if len(output_lines) > 50:
        print(f"\n... (see {output_file} for full output)")


if __name__ == "__main__":
    main()
