"""Immutable asset bytes through the real sandboxed browser; no model fixtures."""
import hashlib
import io
from pathlib import Path
import unittest

from branchwrite.browser_capture import BrowserConfig, PageAction, render_snapshot
from dataclasses import replace


class AssetContractTests(unittest.TestCase):
    def asset_type(self):
        from branchwrite.browser_assets import BrowserAsset
        return BrowserAsset

    def test_manifest_binds_exact_bytes_and_derived_media_type(self):
        Asset=self.asset_type()
        a=Asset('styles/site.css', b'body { color: red; }')
        self.assertEqual(a.media_type,'text/css; charset=utf-8')
        self.assertEqual(a.manifest,dict(path=a.path,sha256=hashlib.sha256(a.body).hexdigest(),
                                       bytes=len(a.body),media_type=a.media_type))
        with self.assertRaises(AttributeError):a.path='other.css'

    def test_paths_reject_traversal_urls_reserved_and_ambiguous_spelling(self):
        Asset=self.asset_type()
        for name in ('../x.png','/x.png','a/../x.png','a//x.png','./x.png',
                     'a\\x.png','index.html','https://example.test/x.png',
                     'a?x.png','a#x.png','a%2fx.png','x\x00.png'):
            with self.subTest(name=name),self.assertRaises(ValueError):Asset(name,b'x')

    def test_only_bounded_immutable_known_resource_types(self):
        Asset=self.asset_type()
        for name,body in [('x.png',bytearray(b'x')),('x.html',b'x'),
                          ('x.png',b'x'*(4*1024*1024+1))]:
            with self.subTest(name=name),self.assertRaises(ValueError):Asset(name,body)

    def test_duplicate_and_total_bundle_limits(self):
        from branchwrite.browser_assets import BrowserAsset, validate_assets
        a=BrowserAsset('x.png',b'x')
        for assets in ([a],(a,a),tuple(BrowserAsset(f'{i}.png',b'x') for i in range(65)),
                       tuple(BrowserAsset(f'{i}.png',b'x'*(4*1024*1024)) for i in range(5))):
            with self.subTest(count=len(assets)),self.assertRaises(ValueError):validate_assets(assets)


class BrowserAssetTests(unittest.TestCase):
    def setUp(self):
        from branchwrite.browser_assets import BrowserAsset
        self.Asset=BrowserAsset
        self.config=BrowserConfig(Path('/home/dflanag3/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome'))

    def png(self):
        from PIL import Image
        image=Image.new('RGB',(16,12),(11,173,91))
        b=io.BytesIO();image.save(b,format='PNG');return b.getvalue()

    def test_real_png_css_and_js_load_from_exact_frozen_bundle(self):
        from PIL import Image
        assets=(self.Asset('assets/marker.png',self.png()),
                self.Asset('style.css',b'body{margin:0;background:rgb(17,29,43)}img{display:block}'),
                self.Asset('app.js',b'document.querySelector("#check").onclick=()=>document.querySelector("#state").textContent="resource executed";'))
        payload=b'<link rel="stylesheet" href="style.css"><body><img src="assets/marker.png"><p id="state"></p><button id="check">Check</button><script src="app.js"></script></body>'
        r=render_snapshot(payload,replace(self.config,actions=(PageAction("click","check"),)),assets=assets)
        self.assertIn("resource executed",r.text)
        self.assertEqual(r.asset_manifest,tuple(a.manifest for a in assets))
        self.assertEqual({x['path'] for x in r.served_assets},{a.path for a in assets})
        self.assertEqual({x['sha256'] for x in r.served_assets},{a.manifest['sha256'] for a in assets})
        with Image.open(io.BytesIO(r.png)) as im:
            self.assertEqual(im.getpixel((5,5))[:3],(11,173,91))
            self.assertEqual(im.getpixel((100,5))[:3],(17,29,43))
        self.assertTrue(r.isolation['worker_exited'])
        self.assertEqual(r.isolation['namespace_members_after'],[])
        self.assertTrue(r.isolation['chromium_sandbox'])

    def test_assets_are_captured_not_read_from_a_host_directory(self):
        body=self.png()
        asset=self.Asset('a.png',body)
        r=render_snapshot(b'<img src="a.png">',self.config,assets=(asset,))
        self.assertEqual(r.served_assets[0]['sha256'],hashlib.sha256(body).hexdigest())

    def test_missing_local_resource_fails(self):
        with self.assertRaisesRegex(ValueError,'unsupported resource'):
            render_snapshot(b'<img src="missing.png">',self.config,assets=())

    def test_external_resource_still_fails(self):
        with self.assertRaisesRegex(ValueError,'unsupported resource'):
            render_snapshot(b'<img src="https://example.invalid/m.png">',self.config,
                            assets=(self.Asset('a.png',self.png()),))

    def test_query_alias_is_not_a_second_resource_identity(self):
        with self.assertRaisesRegex(ValueError,'unsupported resource'):
            render_snapshot(b'<img src="a.png?v=1">',self.config,
                            assets=(self.Asset('a.png',self.png()),))

    def test_navigation_to_an_asset_is_rejected(self):
        with self.assertRaises(ValueError):
            render_snapshot(b'<script>location.href="app.js"</script>',self.config,
                            assets=(self.Asset('app.js',b'void 0;'),))

    def test_unicode_and_spaces_have_one_encoded_request_identity(self):
        asset=self.Asset('markers/green marker-λ.png',self.png())
        r=render_snapshot('<img src="markers/green marker-λ.png">'.encode(),self.config,
                          assets=(asset,))
        self.assertEqual(r.served_assets[0]['path'],asset.path)

    def test_empty_bundle_preserves_existing_document_capture(self):
        r=render_snapshot(b'<p>plain</p>',self.config)
        self.assertEqual(r.asset_manifest,())
        self.assertEqual(r.served_assets,())


if __name__=='__main__':unittest.main()
