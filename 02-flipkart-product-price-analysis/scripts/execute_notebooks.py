"""Execute this project's plain-Python notebook cells and save actual text outputs.

These notebooks intentionally use no notebook magics or rich-display expressions.
Run python -m src.pipeline first. No Jupyter installation is required by this runner.
"""
from pathlib import Path
import contextlib
import io
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
for path in sorted((ROOT / 'notebooks').glob('*.ipynb')):
    book = json.loads(path.read_text())
    namespace = {'__name__': '__main__'}
    count = 0
    for cell in book['cells']:
        if cell['cell_type'] != 'code':
            continue
        count += 1
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            exec(compile(cell['source'], str(path), 'exec'), namespace)
        cell['execution_count'] = count
        cell['outputs'] = [{'output_type':'stream','name':'stdout','text':output.getvalue()}] if output.getvalue() else []
    path.write_text(json.dumps(book, indent=2))
    print('Executed', path.name)
