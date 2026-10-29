"""Export one verified data/processed layout for Ngan; never overwrite a handover."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,tempfile
from load_data import FILES

ROOT=Path(__file__).resolve().parent

def export_ngan(output, source=ROOT, extra_clean=None):
    output,source=Path(output).resolve(),Path(source).resolve()
    if output.exists():raise FileExistsError('Choose a new output directory; existing handover preserved')
    if output.is_relative_to(source):raise ValueError('Output must be outside the source project')
    handover=source/'handover_v3'
    manifest=json.loads((handover/'manifest.json').read_text(encoding='utf8'))
    copies={f'data/{name}':handover/name for name in [*manifest['output_sha256'],'manifest.json']}
    copies.update({f'data/processed/{name}':source/'inputs/clean'/name for name in FILES.values()})
    copies['powerbi/POWERBI_Olist_Chot.pbix']=source/'POWERBI_Olist_Chot.pbix'
    if extra_clean is not None:
        for name in ['geo_by_zip.csv','olist_sellers_clean.csv','audit_report.csv']:
            copies['data/processed/'+name]=Path(extra_clean)/name
    for name,path in copies.items():
        if not path.is_file():raise FileNotFoundError(str(path))
    for name,expected in manifest['output_sha256'].items():
        if hashlib.sha256((handover/name).read_bytes()).hexdigest()!=expected:
            raise ValueError('Handover hash mismatch: '+name)
    for name in FILES.values():
        if hashlib.sha256((source/'inputs/clean'/name).read_bytes()).hexdigest()!=manifest['input_sha256'][name]:
            raise ValueError('Clean input changed: '+name)
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.ngan_export_',dir=output.parent) as temp:
        stage=Path(temp)/'package';stage.mkdir()
        for name,path in copies.items():
            dest=stage/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
        result={'version':'ngan_handover_20261029','datasets_contract':'data/integration_contract.json',
                'files_sha256':{name:hashlib.sha256((stage/name).read_bytes()).hexdigest() for name in copies},
                'model_status':'experimental_not_validated_for_deployment',
                'powerbi_setup':'Set DataRoot to the absolute path of this package/data before Refresh.',
                'ml_test':'Historical evaluation only; use ml_bi from integration contract for customer scores.'}
        (stage/'HANDOVER_MANIFEST.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
        (stage/'README.md').write_text('# Bàn giao Ngân\n\nChép data vào cạnh app.py; giữ data/processed. Đọc data/integration_contract.json.\nSnapshot ML có tiền tố ml_; không dùng bảng test làm điểm khách BI, không điền xác suất thiếu thành 0.\nMở Power BI và đổi DataRoot thành đường dẫn tuyệt đối thư mục data này trước Refresh.\nML còn thử nghiệm; xem metrics.json và validation_protocol.json. Web cần tích hợp và kiểm thử riêng.\n',encoding='utf8')
        os.rename(stage,output)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--extra-clean',type=Path)
    a=p.parse_args();result=export_ngan(a.output,extra_clean=a.extra_clean)
    print(f"Exported {len(result['files_sha256'])} verified files to {a.output}")
