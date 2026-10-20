"""Select a PDF output in the shared isolated Python-build supervisor."""
import sys
sys.path.insert(0, '/policy')
from cad_build_worker import run
from pdf_contract import MAX_PDF_BYTES
if __name__ == '__main__':
    run(output_name='document.pdf', output_limit=MAX_PDF_BYTES, result_key='pdf')
