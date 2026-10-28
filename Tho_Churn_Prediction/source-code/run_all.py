from pathlib import Path
from argparse import ArgumentParser
import subprocess
import sys


def run_script(script_path, args):
    subprocess.run([sys.executable, "-B", str(script_path)] + args, check=True)


def main():
    source_dir = Path(__file__).resolve().parent
    parser = ArgumentParser(description="Chạy đánh giá churn theo thời gian")
    parser.add_argument("--clean-orders", type=Path)
    parser.add_argument("--master", type=Path)
    parser.add_argument("--handover-dir", type=Path, help="Thu muc tho trong goi du lieu cua Thien")
    parser.add_argument("--observation-end", default="2018-08-31 00:00:00")
    parser.add_argument("--output-dir", type=Path, help="Thu muc rieng de chay lai/doi soat ket qua")
    args = parser.parse_args()
    command = ["--observation-end", args.observation_end]
    if args.clean_orders:
        command += ["--clean-orders", str(args.clean_orders)]
    if args.master:
        command += ["--master", str(args.master)]
    if args.handover_dir:
        command += ["--handover-dir", str(args.handover_dir)]
    if args.output_dir:
        command += ["--output-dir", str(args.output_dir)]
    run_script(source_dir / "evaluate_temporal.py", command)


if __name__ == "__main__":
    main()
