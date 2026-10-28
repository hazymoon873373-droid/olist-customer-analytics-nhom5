from pathlib import Path
from argparse import ArgumentParser
import subprocess
import sys


def run(script_path, args=None):
    subprocess.run([sys.executable, str(script_path)] + (args or []), check=True)


def main():
    source_dir = Path(__file__).resolve().parent
    parser = ArgumentParser(description="Chạy phát hiện đơn hàng bất thường")
    parser.add_argument("--clean-orders", type=Path)
    parser.add_argument("--input", type=Path)
    args = parser.parse_args()
    command = []
    if args.clean_orders:
        command += ["--clean-orders", str(args.clean_orders)]
    if args.input:
        command += ["--input", str(args.input)]
    run(source_dir / "prepare_anomaly_data.py", command)
    run(source_dir / "train_isolation_forest.py")
    run(source_dir / "export_summary.py")


if __name__ == "__main__":
    main()
