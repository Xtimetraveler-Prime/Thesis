#!/usr/bin/env python3
from __future__ import annotations

import argparse

from mnist_app.config import PROFILES
from mnist_app.training import train_snn


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train one direct MNIST SNN deployment profile"
    )
    parser.add_argument("--profile", choices=tuple(PROFILES), required=True)
    parser.add_argument("--output", default="applications/mnist/build/training")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument(
        "--fine-tune-epochs",
        type=int,
        default=5,
        help="masked fine-tuning epochs used by native-sparse after pruning",
    )
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument(
        "--seed",
        type=lambda value: int(value, 0),
        default=0x4D4E4953,
    )
    parser.add_argument("--train-limit", type=int)
    parser.add_argument("--test-limit", type=int)
    args = parser.parse_args()

    result = train_snn(
        args.output,
        profile=args.profile,
        epochs=args.epochs,
        fine_tune_epochs=args.fine_tune_epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        seed=args.seed,
        train_limit=args.train_limit,
        test_limit=args.test_limit,
    )
    print(f"profile:    {result.profile}")
    print(f"checkpoint: {result.checkpoint}")
    print(f"metrics:    {result.metrics}")
    print(f"evaluation: {result.evaluation}")
    print(f"test acc:   {result.final_test_accuracy:.4f}")
    print(f"nonzero:    {result.nonzero_weights}")


if __name__ == "__main__":
    main()
