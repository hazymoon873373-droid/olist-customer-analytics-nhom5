from pathlib import Path
import subprocess
import sys


def run(script_path):
    subprocess.run([sys.executable, str(script_path)], check=True)


def main():
    source_dir = Path(__file__).resolve().parent
    run(source_dir / "prepare_anomaly_data.py")
    run(source_dir / "train_isolation_forest.py")


if __name__ == "__main__":
    main()
