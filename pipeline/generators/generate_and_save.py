"""
Standalone script: generates a synthetic transaction dataset and saves
it to data/synthetic_transactions.csv.

Usage:
    python pipeline/generators/generate_and_save.py
    python pipeline/generators/generate_and_save.py --accounts 5000 --fraud-rate 0.005 --seed 42

This is Phase 1's literal deliverable per ImplementationPlan.md:
"a script that produces a realistic stream of synthetic transactions on
demand." Kept separate from transaction_stream.py itself so that file
stays a clean, importable module (used directly by tests and, later,
by Phase 3's training code) without CLI argument-parsing concerns mixed in.
"""

import argparse
import csv
from datetime import datetime
from dataclasses import asdict

from pipeline.generators.transaction_stream import generate_dataset, dataset_summary


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic fraud transaction dataset")
    parser.add_argument("--accounts", type=int, default=2000)
    parser.add_argument("--fraud-rate", type=float, default=0.005)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=str, default="data/synthetic_transactions.csv")
    args = parser.parse_args()

    print(f"Generating dataset: {args.accounts} accounts, target fraud_rate={args.fraud_rate}, seed={args.seed}")
    transactions = generate_dataset(
        n_accounts=args.accounts,
        fraud_rate=args.fraud_rate,
        end_time=datetime(2026, 6, 1),
        seed=args.seed,
    )

    summary = dataset_summary(transactions)
    print("Generation complete:")
    for k, v in summary.items():
        print(f"  {k}: {v}")

    fieldnames = [
        "account_id", "timestamp", "amount", "merchant_category",
        "location_lat", "location_lng", "device_id", "is_fraud", "fraud_type",
    ]
    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for t in transactions:
            row = asdict(t)
            writer.writerow(row)

    print(f"\nSaved {len(transactions)} transactions to {args.output}")


if __name__ == "__main__":
    main()
