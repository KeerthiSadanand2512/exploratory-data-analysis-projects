"""Download the public Kaggle archive without executing or extracting arbitrary paths."""
from pathlib import Path
import io
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://www.kaggle.com/api/v1/datasets/download/PromptCloudHQ/flipkart-products'
FILENAME = 'flipkart_com-ecommerce_sample.csv'

def main():
    target = ROOT / 'data/raw' / FILENAME
    if target.exists():
        print(f'Already present: {target}')
        return
    request = urllib.request.Request(URL, headers={'User-Agent': 'flipkart-price-analysis/1.0'})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            archive = zipfile.ZipFile(io.BytesIO(response.read()))
        members = [n for n in archive.namelist() if Path(n).name == FILENAME]
        if len(members) != 1:
            raise ValueError('Expected CSV not found uniquely in the archive')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(archive.read(members[0]))
    except Exception as exc:
        raise SystemExit(f'Download failed: {exc}\nDownload manually from the Kaggle link in README and place {FILENAME} in data/raw/.') from exc
    print(f'Downloaded: {target}')

if __name__ == '__main__':
    main()
