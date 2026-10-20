from pathlib import Path
import hashlib,json,sys,importlib.metadata
from playwright.sync_api import sync_playwright
root=Path(__file__).parent
source=root/sys.argv[1]
rows=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path="/home/dflanag3/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome",headless=True,chromium_sandbox=True)
    for name,width,height in [("desktop",1280,800),("phone",375,812)]:
        context=browser.new_context(viewport=dict(width=width,height=height))
        requests=[];errors=[]
        context.route("**/*",lambda r:r.continue_() if r.request.url.startswith("file:") else r.abort())
        page=context.new_page()
        page.on("request",lambda r:requests.append(r.url))
        page.on("pageerror",lambda e:errors.append(str(e)))
        page.goto(source.resolve().as_uri())
        assert page.locator("h1").is_visible()
        assert page.locator("h1").evaluate("e=>getComputedStyle(e).color")=="rgb(0, 0, 255)"
        page.get_by_role("button",name="Say hello",exact=True).click()
        assert "Hello, David!" in page.locator("body").inner_text()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert not errors,errors
        assert all(x.startswith("file:") for x in requests),requests
        if "followup" in source.name:
            for dog in ("Bella","Max","Luna"):
                assert page.locator("strong, b").filter(has_text=dog).count()>0,("not bold",dog)
        image=root/(source.stem+"-"+name+".png")
        page.screenshot(path=str(image),full_page=True)
        rows.append(dict(viewport=name,width=width,height=height,button=True,blue_heading=True,
            no_overflow=True,no_page_errors=True,requests=requests,screenshot=image.name))
        context.close()
    browser.close()
report=dict(status="PASS",source=source.name,sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    playwright=importlib.metadata.version("playwright"),rows=rows,
    scope="Independent Chromium audit of byte-identical HTML copied directly from client VM; this is not model-driven browser inspection.")
(root/(source.stem+"-audit.json")).write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report))
