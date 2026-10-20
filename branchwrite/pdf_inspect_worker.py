"""Independent PDF parse/render. No candidate source or build helpers mounted."""
import base64,hashlib,io,json,math,os,sys
from pathlib import Path
sys.path.insert(0,'/policy')
from cad_build_worker import candidate_process_policy
from pdf_contract import MAX_PDF_BYTES,MAX_PAGES,MAX_PAGE_POINTS,MAX_PAGE_PIXELS,RENDER_PROFILE


def run():
    protocol=os.dup(1);os.dup2(2,1)
    candidate_process_policy()
    result=dict(schema=1,status='FAIL',error=None,page_count=None,page=None,text=None,image=None,pdf_sha256=None)
    try:
        import pypdf
        import pypdfium2 as pdfium
        raw=Path('/inputs/document.pdf').read_bytes()
        result['pdf_sha256']=hashlib.sha256(raw).hexdigest()
        reader=pypdf.PdfReader(io.BytesIO(raw),strict=True)
        if reader.is_encrypted:raise ValueError('encrypted PDF is not supported by this document tool')
        count=len(reader.pages)
        if not 1<=count<=MAX_PAGES:raise ValueError('PDF page limit is '+str(MAX_PAGES))
        page_number=int(sys.argv[1]);result.update(page_count=count,page=page_number)
        if not 1<=page_number<=count:raise ValueError('PDF page is outside the document')
        with pdfium.PdfDocument(raw) as document:
            if len(document)!=count:raise ValueError('independent PDF page counts disagree')
            page=document[page_number-1]
            try:
                width,height=page.get_size()
                if not all(math.isfinite(v) and 0<v<=MAX_PAGE_POINTS for v in (width,height)):
                    raise ValueError('PDF page geometry is unsupported')
                textpage=page.get_textpage()
                try:text=textpage.get_text_range(errors='strict')[:8192]
                finally:textpage.close()
                bitmap=page.render(scale=min(2,MAX_PAGE_PIXELS/max(width,height)))
                try:
                    image=bitmap.to_pil().convert('RGB');output=io.BytesIO();image.save(output,format='PNG')
                    png=output.getvalue()
                    if len(png)>MAX_PDF_BYTES:raise ValueError('rendered PDF page exceeds artifact bound')
                finally:bitmap.close()
            finally:page.close()
        result.update(status='PASS',text=text,image=base64.b64encode(png).decode(),size_points=[width,height],
                      size_pixels=list(image.size),render_profile=RENDER_PROFILE,forms='not initialized; no JavaScript execution')
    except BaseException as error:result['error']=type(error).__name__+': '+str(error)[:3000]
    with os.fdopen(protocol,'w') as stream:stream.write(json.dumps(result,separators=(',',':'))+'\n')
if __name__=='__main__':run()
