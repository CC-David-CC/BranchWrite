"""Internal fixed entry point, executed only inside the capture namespace."""
import argparse
import json
import os
from pathlib import Path
import sys


def read_browser_input(stream):
    """Validate the entire bounded byte frame before launching a browser."""
    from branchwrite.browser_assets import BrowserAsset, validate_assets
    header = stream.readline(524289)
    if len(header) > 524288 or not header.endswith(b'\n'):
        raise ValueError('invalid browser input action framing')
    header = json.loads(header)
    if type(header) is not dict or set(header) != {'actions','source_bytes','assets'} or type(header['actions']) is not list or len(header['actions']) > 16:
        raise ValueError('invalid browser action sequence')
    size=header['source_bytes']
    rows=header['assets']
    if (type(size) is not int or not 0<=size<=4*1024*1024
            or type(rows) is not list or len(rows)>64):
        raise ValueError('invalid browser input byte bounds')
    payload=stream.read(size)
    if len(payload)!=size:raise ValueError('truncated document')
    assets=[]
    for row in rows:
        if (type(row) is not dict or set(row)!={'path','sha256','bytes','media_type'}
                or type(row['bytes']) is not int or not 0<=row['bytes']<=4*1024*1024):
            raise ValueError('invalid resource descriptor')
        if sum(len(a.body) for a in assets)+row['bytes']>16*1024*1024:
            raise ValueError('resource bundle exceeds the byte bound')
        asset=BrowserAsset(row['path'],stream.read(row['bytes']))
        if asset.manifest!=row:raise ValueError('resource bytes differ from manifest')
        assets.append(asset)
    assets=validate_assets(tuple(assets))
    if stream.read(1):raise ValueError('trailing browser input bytes')
    return header['actions'],payload,assets


def main():
    sys.path.insert(0, '/app')
    from branchwrite.browser_capture import BrowserConfig, PageInspection, PageAction, _render_snapshot
    from branchwrite.browser_assets import BrowserAsset, validate_assets
    parser = argparse.ArgumentParser()
    parser.add_argument('--browser', type=Path, required=True)
    parser.add_argument('--width', type=int, required=True)
    parser.add_argument('--height', type=int, required=True)
    parser.add_argument('--timeout', type=float, required=True)
    parser.add_argument('--document-path',default='index.html')
    parser.add_argument('--inspection-sha256')
    parser.add_argument('--inspection-target')
    args = parser.parse_args()
    action_rows,payload,assets=read_browser_input(sys.stdin.buffer)
    actions=tuple(PageAction(**row) for row in action_rows)
    for path in ('/tmp/home', '/tmp/cache'):
        Path(path).mkdir(mode=0o700)
    witness = dict(schema=1, kind='bubblewrap-browser-v1', chromium_sandbox=True,
        net_ns=os.readlink('/proc/self/ns/net'), pid_ns=os.readlink('/proc/self/ns/pid'),
        mount_ns=os.readlink('/proc/self/ns/mnt'), uid=os.getuid())
    if (args.inspection_sha256 is None) != (args.inspection_target is None):
        raise ValueError('incomplete host inspection request')
    inspection = (None if args.inspection_target is None else PageInspection(
        Path('/inspection/checks.py'), args.inspection_sha256, args.inspection_target))
    result = _render_snapshot(payload, BrowserConfig(args.browser, args.width, args.height,
                                                     args.timeout, inspection, actions),assets=assets,document_path=args.document_path)
    header = dict(browser_version=result.browser_version, url=result.url,
        http_status=result.http_status, served_sha256=result.served_sha256, isolation=witness,
        inspection=result.inspection, actions=result.actions, text=result.text,
        asset_manifest=result.asset_manifest,served_assets=result.served_assets,document_path=result.document_path,
        runtime_errors=result.runtime_errors)
    sys.stdout.buffer.write(json.dumps(header, separators=(',', ':')).encode() + b'\n' + result.png)
    sys.stdout.buffer.flush()


if __name__ == '__main__':
    main()
