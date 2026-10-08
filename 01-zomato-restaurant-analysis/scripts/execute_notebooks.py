"""Execute notebooks using the current Python environment without installing a kernel."""
from pathlib import Path
import sys
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpec

root = Path(__file__).resolve().parents[1]
for path in sorted((root/'notebooks').glob('*.ipynb')):
    notebook = nbformat.read(path,as_version=4)
    manager = KernelManager()
    manager._kernel_spec = KernelSpec(argv=[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}'],
                                      display_name='Python (current environment)',language='python')
    try:
        NotebookClient(notebook,km=manager,timeout=180,resources={'metadata':{'path':str(root)}}).execute()
    finally:
        if manager.has_kernel:
            manager.shutdown_kernel(now=True)
    nbformat.write(notebook,path)
    print(f'Executed {path.name}')
