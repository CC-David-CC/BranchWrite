"""Bounded immutable resources; no paths are ever opened by the browser."""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import PurePosixPath

MAX_ASSETS=64
MAX_ASSET_BYTES=4*1024*1024
MAX_BUNDLE_BYTES=16*1024*1024
_MEDIA={'.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg',
        '.webp':'image/webp','.gif':'image/gif','.svg':'image/svg+xml',
        '.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8',
        '.woff':'font/woff','.woff2':'font/woff2','.txt':'text/plain; charset=utf-8'}


def document_path(value):
    if (type(value) is not str or not value or len(value.encode('utf8'))>1024
            or any(ord(c)<32 or ord(c)==127 or c in '\\\\%?#:' for c in value)):
        raise ValueError('document path must have one bounded local URL identity')
    path=PurePosixPath(value)
    if (path.is_absolute() or path.as_posix()!=value
            or any(part in ('.','..') for part in path.parts)):
        raise ValueError('document path must be canonical')
    return value


@dataclass(frozen=True)
class BrowserAsset:
    path: str
    body: bytes

    def __post_init__(self):
        name=self.path
        if (type(name) is not str or not name or len(name.encode('utf8'))>1024
                or any(ord(c)<32 or ord(c)==127 or c in '\\\\%?#:' for c in name)):
            raise ValueError('asset path must have one bounded local URL identity')
        path=PurePosixPath(name)
        if (path.is_absolute() or path.as_posix()!=name
                or any(part in ('.','..') for part in path.parts) or name=='index.html'):
            raise ValueError('asset path must be canonical and cannot replace the document')
        if path.suffix.lower() not in _MEDIA:
            raise ValueError('unsupported browser resource type')
        if type(self.body) is not bytes or len(self.body)>MAX_ASSET_BYTES:
            raise ValueError('asset requires bounded immutable bytes')

    @property
    def media_type(self):return _MEDIA[PurePosixPath(self.path).suffix.lower()]

    @property
    def manifest(self):
        return dict(path=self.path,sha256=sha256(self.body).hexdigest(),
                    bytes=len(self.body),media_type=self.media_type)


def validate_assets(assets):
    if (type(assets) is not tuple or len(assets)>MAX_ASSETS
            or any(type(a) is not BrowserAsset for a in assets)):
        raise ValueError('assets require a bounded immutable tuple')
    if len({a.path for a in assets})!=len(assets):
        raise ValueError('duplicate browser asset paths')
    if sum(len(a.body) for a in assets)>MAX_BUNDLE_BYTES:
        raise ValueError('browser asset bundle exceeds the byte bound')
    return assets
