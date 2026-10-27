from pathlib import Path
import subprocess
import sys


def run_script(script_path):
    subprocess.run([sys.executable, "-B", str(script_path)], check=True)


def main():
    source_dir = Path(__file__).resolve().parent
    run_script(source_dir / "prepare_churn_data.py")
    run_script(source_dir / "train_churn_model.py")


if __name__ == "__main__":
    main()
