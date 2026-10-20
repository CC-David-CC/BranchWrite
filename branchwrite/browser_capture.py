"""Client-side rendering of one captured HTML snapshot.

The public entry point requires the Linux browser-host namespace boundary;
Chromium's renderer sandbox also stays enabled. The byte server and Playwright
run inside that same isolated network. Bounded DOM-ID click/fill recipes run in a fresh context per capture. Explicitly
captured resource bytes may be supplied; navigation and persistent sessions remain
unsupported. No live directory or unsafe fallback is provided.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import math
import re
import os
from pathlib import Path
import threading
import time
import tempfile
from urllib.parse import quote
from .browser_assets import validate_assets, document_path as validate_document_path


@dataclass(frozen=True)
class PageInspection:
    """Host-selected immutable checker; never a model-provided module/path.

    custom admits task-specific host checks with the same source hash and OS
    boundary as catalog checks. It may supply an interact callback. Existing
    catalog targets retain their original behavior and protected assertions.
    """
    path: Path
    sha256: str
    target: str

    def __post_init__(self):
        path = Path(self.path)
        if (not path.is_absolute() or self.target not in ('H03', 'H04', 'H05', 'H06', 'H07', 'H08', 'H09', 'H10', 'H11', 'H12', 'custom')
                or not isinstance(self.sha256, str) or len(self.sha256) != 64
                or any(c not in '0123456789abcdef' for c in self.sha256)):
            raise ValueError('invalid host page inspection descriptor')
        object.__setattr__(self, 'path', path)


@dataclass(frozen=True)
class PageAction:
    """A bounded DOM-ID action, never script, URL, selector language or shell."""
    kind: str
    target: str
    value: str = ''

    def __post_init__(self):
        if (type(self.kind) is not str or self.kind not in ('click', 'fill')
                or type(self.target) is not str
                or re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', self.target) is None
                or type(self.value) is not str or len(self.value.encode('utf8')) > 4096
                or (self.kind == 'click' and self.value != '')):
            raise ValueError('invalid bounded browser action')

    @property
    def wire(self):
        return dict(kind=self.kind, target=self.target, value=self.value)


def page_action_recipe(value):
    """Parse the bounded wire recipe once for planning and execution."""
    if type(value) is not list or not 1 <= len(value) <= 16:
        raise ValueError('browser recipe requires one to16 actions')
    if any(type(row) is not dict or set(row) != {'kind', 'target', 'value'} for row in value):
        raise ValueError('closed browser action fields required')
    return tuple(PageAction(**row) for row in value)


@dataclass(frozen=True)
class BrowserConfig:
    """Host-owned configuration; model actions cannot select executable/options."""
    executable: Path
    width: int = 640
    height: int = 480
    timeout: float = 15.0
    inspection: PageInspection | None = None
    actions: tuple[PageAction, ...] = ()
    viewports: tuple[tuple[str,int,int], ...] = ()

    def __post_init__(self):
        executable = Path(self.executable)
        if not executable.is_absolute():
            raise ValueError("browser executable must be an absolute host-selected path")
        for value in (self.width, self.height):
            if type(value) is not int or not 1 <= value <= 2048:
                raise ValueError("browser viewport dimension is outside the host bound")
        if self.width * self.height > 2_000_000:
            raise ValueError("browser viewport area exceeds the host bound")
        if (type(self.timeout) not in (int, float) or not math.isfinite(self.timeout)
                or not 0 < self.timeout <= 30):
            raise ValueError("browser timeout is outside the host bound")
        object.__setattr__(self, "executable", executable)
        if self.inspection is not None and not isinstance(self.inspection, PageInspection):
            raise ValueError('page inspection must be a host descriptor')
        if (type(self.actions) is not tuple or len(self.actions) > 16
                or any(not isinstance(a, PageAction) for a in self.actions)):
            raise ValueError('browser actions require a bounded immutable tuple')
        if self.inspection is not None and self.actions:
            raise ValueError('protected inspection cannot be a model action sequence')

        if type(self.viewports) is not tuple or len(self.viewports)>8:
            raise ValueError('one immutable bounded viewport menu required')
        names=set();sizes=set();rows=[]
        for row in self.viewports:
            if (type(row) is not tuple or len(row)!=3 or type(row[0]) is not str
                    or re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,31}',row[0]) is None):
                raise ValueError('invalid named viewport')
            name,width,height=row
            BrowserConfig(executable,width,height,self.timeout)
            if name in names or (width,height) in sizes:
                raise ValueError('duplicate viewport name or geometry')
            names.add(name);sizes.add((width,height));rows.append(row)
        if rows and (self.width,self.height) not in sizes:
            raise ValueError('viewport menu must name the default geometry')
        object.__setattr__(self,'viewports',tuple(sorted(rows)))

    def for_viewport(self,name=None):
        """Select only a host-named geometry;keep the immutable menu."""
        if name is None:return self
        for candidate,width,height in self.viewports:
            if type(name) is str and name==candidate:
                from dataclasses import replace
                return replace(self,width=width,height=height)
        raise ValueError('viewport is not granted by the host')

    def name_for_size(self,width,height):
        if type(width) is not int or type(height) is not int:
            raise ValueError('exact viewport integer geometry required')
        if not self.viewports and (width,height)==(self.width,self.height):return None
        for name,w,h in self.viewports:
            if (width,height)==(w,h):return name
        raise ValueError('viewport geometry is not granted by the host')

    def at_size(self,width,height):
        return self.for_viewport(self.name_for_size(width,height))



@dataclass(frozen=True)
class RenderedPage:
    png: bytes
    browser_version: str
    url: str
    http_status: int
    served_sha256: str
    isolation: dict | None = None
    inspection: dict | None = None
    actions: tuple = ()
    text: str = ""
    asset_manifest: tuple = ()
    served_assets: tuple = ()
    document_path: str = "index.html"
    runtime_errors: tuple[str, ...] = ()


def render_snapshot(payload: bytes, config: BrowserConfig, *, assets=(), document_path="index.html") -> RenderedPage:
    """Capture model-written bytes under the registered Linux OS boundary."""
    if not isinstance(config, BrowserConfig):
        raise ValueError('host browser configuration is required')
    if type(payload) is not bytes or len(payload) > 4 * 1024 * 1024:
        raise ValueError('browser source must be bounded captured bytes')
    from .browser_isolation import render_isolated
    assets=validate_assets(assets)
    document_path=validate_document_path(document_path)
    if document_path in {a.path for a in assets}:raise ValueError('document aliases a resource')
    return render_isolated(payload, config, assets=assets, document_path=document_path)


def _render_snapshot(payload: bytes, config: BrowserConfig, *, assets=(), document_path="index.html") -> RenderedPage:
    """Navigate a real URL served from captured bytes, then capture actual pixels.

    A new browser/context owns each capture. No host directory is exposed; there
    is no arbitrary URL or resource lookup. Missing dependencies and sandbox
    failures are explicit errors, never synthetic captures or skipped passes.
    This tool accepts one HTML document and an explicit immutable resource bundle. Optional bounded DOM-ID
    actions execute before capture; they never select script or a URL. Protected
    checkers and model action recipes cannot be combined in one browser request.
    """
    if not isinstance(config, BrowserConfig):
        raise ValueError("host browser configuration is required")
    if type(payload) is not bytes or len(payload) > 4 * 1024 * 1024:
        raise ValueError("browser source must be bounded captured bytes")
    if not config.executable.is_file() or not os.access(config.executable, os.X_OK):
        raise ValueError("configured browser executable is unavailable")
    from PIL import Image
    from playwright.sync_api import sync_playwright

    assets=validate_assets(assets)
    document_path=validate_document_path(document_path)
    if document_path in {a.path for a in assets}:raise ValueError('document aliases a resource')
    document_url='/'+quote(document_path,safe='/')
    resources={'/'+quote(a.path,safe='/'):a for a in assets}
    served_assets=[]
    source_sha = hashlib.sha256(payload).hexdigest()
    served = []
    blocked = []
    errors = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            asset=resources.get(self.path)
            if self.path == document_url:
                body,media_type=payload,"text/html; charset=utf-8"
            elif asset is not None:
                body,media_type=asset.body,asset.media_type
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", media_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)
            if asset is None:served.append(source_sha)
            else:served_assets.append(asset.manifest)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever,
                              kwargs={"poll_interval": 0.02}, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    url = origin + document_url
    deadline = time.monotonic() + config.timeout

    def remaining():
        milliseconds = int((deadline - time.monotonic()) * 1000)
        if milliseconds <= 0:
            raise TimeoutError("browser capture deadline expired")
        return milliseconds

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=str(config.executable),
                headless=True, chromium_sandbox=True, timeout=remaining())
            try:
                context = browser.new_context(viewport={"width": config.width, "height": config.height},
                    device_scale_factor=1, locale="en-US", timezone_id="UTC",
                    service_workers="block", reduced_motion="reduce", accept_downloads=False)
                try:
                    def route(request):
                        resource=request.request.url.removeprefix(origin)
                        if request.request.url == url:
                            request.continue_()
                        elif (request.request.url == origin+resource and resource in resources
                                and request.request.resource_type != 'document'
                                and len(served_assets)<256):
                            request.continue_()
                        elif request.request.url == origin + "/favicon.ico":
                            request.fulfill(status=404, body="")
                        else:
                            blocked.append("unsupported resource")
                            request.abort()

                    def websocket(socket):
                        blocked.append("unsupported websocket resource")
                        socket.close()

                    context.route("**/*", route)
                    context.route_web_socket("**/*", websocket)
                    page = context.new_page()
                    page.on("pageerror", lambda error: errors.append((str(error) or "JavaScript exception")[:1024])
                            if len(errors) < 16 else None)
                    response = page.goto(url, wait_until="load", timeout=remaining())
                    if (response is None or response.status != 200 or page.url != url
                            or response.body() != payload):
                        raise ValueError("browser did not receive the pinned source bytes")
                    actions = []
                    for action in config.actions:
                        target = page.locator('[id="' + action.target + '"]')
                        if target.count() != 1:
                            raise ValueError('browser action requires a unique DOM ID')
                        if action.kind == 'click':
                            target.click(timeout=remaining())
                        else:
                            target.fill(action.value, timeout=remaining())
                        actions.append(action.wire)
                        if page.url != url or len(context.pages) != 1:
                            raise ValueError('browser action attempted navigation or a new page')
                    text = page.locator('body').inner_text(timeout=remaining())[:8192] if actions else ''
                    # Default Playwright caret hiding leaves empty inline style
                    # attributes on inputs. A transient screenshot stylesheet
                    # hides the caret without that residual DOM mutation.
                    png = page.screenshot(type="png", full_page=False, animations="disabled", caret="initial",
                                          style="* { caret-color: transparent !important; }",
                                          timeout=remaining())
                    if blocked:
                        raise ValueError("browser attempted an unsupported resource")
                    # Candidate JavaScript failures are observations, not unknown
                    # host effects. Only the normal, fully validated/retired worker
                    # path may publish them. Protected verification still fails.
                    if errors and config.inspection is not None:
                        raise ValueError("page execution failed: " + errors[0][:256])
                    if not served or any(value != source_sha for value in served):
                        raise ValueError("browser source-serving witness is incomplete")
                    if len(png) > 8 * 1024 * 1024:
                        raise ValueError("browser screenshot exceeds the byte bound")
                    with Image.open(io.BytesIO(png)) as image:
                        image.load()
                        if image.format != "PNG" or image.size != (config.width, config.height):
                            raise ValueError("browser returned invalid screenshot dimensions/format")
                    inspection = None
                    if config.inspection is not None:
                        import importlib.util
                        from playwright.sync_api import expect
                        check = config.inspection
                        if hashlib.sha256(check.path.read_bytes()).hexdigest() != check.sha256:
                            raise ValueError('inspection source changed inside the worker')
                        spec = importlib.util.spec_from_file_location('host_page_checks', check.path)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        expect.set_options(timeout=min(1500, remaining()))
                        inspection = dict(schema=1, target=check.target, inspector_sha256=check.sha256,
                                          status='PASS', error=None, actions=[])
                        with tempfile.TemporaryDirectory(prefix='bw-inspection-') as directory:
                            path = Path(directory) / 'captured.png'
                            path.write_bytes(png)
                            try:
                                # Use the unchanged supplied assertions on this
                                # actual live page and these actual PNG bytes.
                                module.structure(page, check.target, expect)
                                if (check.target in ('H06', 'H07', 'H08', 'H09', 'H10', 'H11', 'H12')
                                        or (check.target=='custom' and callable(getattr(module,'interact',None)))):
                                    # The trusted checker drives real browser events;
                                    # model text cannot manufacture an action receipt.
                                    module.interact(page, check.target, expect, inspection['actions'])
                                    png = page.screenshot(type='png', full_page=False, animations='disabled', caret='initial',
                                                          style='* { caret-color: transparent !important; }',
                                                          timeout=remaining())
                                    path.write_bytes(png)
                                    # A working counter must also preserve the
                                    # page after its handlers have executed.
                                    module.structure(page, check.target, expect)
                                module.pixels(path, page, check.target, '01')
                            except AssertionError as error:
                                inspection.update(status='FAIL', error=str(error)[:2048])
                                if check.target in ('H06', 'H07', 'H08', 'H09', 'H10', 'H11', 'H12', 'custom'):
                                    # Retain the actual resulting failing page.
                                    png = page.screenshot(type='png', full_page=False, animations='disabled', caret='initial',
                                                          style='* { caret-color: transparent !important; }',
                                                          timeout=remaining())
                        if blocked or errors:
                            raise ValueError('page execution or resource failure during inspection')
                    return RenderedPage(png, browser.version, url, response.status, source_sha,
                                        inspection=inspection, actions=tuple(actions), text=text,
                                        asset_manifest=tuple(a.manifest for a in assets),
                                        served_assets=tuple(served_assets),document_path=document_path,
                                        runtime_errors=tuple(errors))
                finally:
                    context.close()
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        if thread.is_alive():
            raise RuntimeError("browser snapshot server did not stop")
