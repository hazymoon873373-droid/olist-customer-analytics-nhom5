"""Single supported entrypoint: validated data rebuild, then plots."""
from pathlib import Path
import argparse
from build_handover import build,ROOT

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=ROOT/'inputs/clean')
    p.add_argument('--ml',type=Path,default=ROOT/'inputs/ml')
    p.add_argument('--output',type=Path,default=ROOT/'handover_v3')
    p.add_argument('--charts',type=Path,default=ROOT/'charts')
    p.add_argument('--data-only',action='store_true');a=p.parse_args()
    build(a.source,a.ml,a.output)
    if not a.data_only:
        from eda_analysis_pipeline import render_charts
        result=render_charts(a.output,a.charts);print(f'Exported {len(result)} charts')

if __name__=='__main__':main()
