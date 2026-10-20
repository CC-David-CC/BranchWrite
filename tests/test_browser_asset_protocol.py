import io
import json
import unittest
from branchwrite.browser_assets import BrowserAsset


class AssetFrameTests(unittest.TestCase):
    def parse(self,header,body=b''):
        from branchwrite.browser_worker import read_browser_input
        return read_browser_input(io.BytesIO(json.dumps(header).encode()+b'\n'+body))

    def header(self,**kw):
        return dict(actions=[],source_bytes=0,assets=[],**kw)

    def test_round_trip_exact_source_resource_and_actions(self):
        a=BrowserAsset('site.css',b'body{}')
        header=dict(actions=[dict(kind='click',target='go',value='')],source_bytes=3,assets=[a.manifest])
        actions,source,assets=self.parse(header,b'abc'+a.body)
        self.assertEqual(actions,header['actions'])
        self.assertEqual(source,b'abc')
        self.assertEqual(assets,(a,))

    def test_truncated_document_rejected(self):
        h=self.header();h['source_bytes']=3
        with self.assertRaisesRegex(ValueError,'truncated document'):self.parse(h,b'ab')

    def test_corrupt_resource_rejected_before_browser(self):
        a=BrowserAsset('site.css',b'body{}');h=self.header();h['assets']=[a.manifest]
        with self.assertRaisesRegex(ValueError,'differ from manifest'):self.parse(h,b'Body{}')

    def test_truncated_resource_rejected(self):
        a=BrowserAsset('site.css',b'body{}');h=self.header();h['assets']=[a.manifest]
        with self.assertRaisesRegex(ValueError,'differ from manifest'):self.parse(h,b'body{')

    def test_altered_media_type_rejected(self):
        a=BrowserAsset('site.css',b'body{}');row={**a.manifest,'media_type':'text/javascript'};h=self.header();h['assets']=[row]
        with self.assertRaisesRegex(ValueError,'differ from manifest'):self.parse(h,a.body)

    def test_legacy_or_extra_fields_rejected(self):
        for h in [dict(actions=[]),{**self.header(),'other':1}]:
            with self.subTest(h=h),self.assertRaises(ValueError):self.parse(h)

    def test_oversized_and_noninteger_lengths_rejected(self):
        for n in [-1,True,4*1024*1024+1,1.5]:
            h=self.header();h['source_bytes']=n
            with self.subTest(n=n),self.assertRaisesRegex(ValueError,'byte bounds'):self.parse(h)

    def test_trailing_bytes_rejected(self):
        with self.assertRaisesRegex(ValueError,'trailing'):self.parse(self.header(),b'x')

    def test_duplicate_paths_rejected(self):
        a=BrowserAsset('site.css',b'x');h=self.header();h['assets']=[a.manifest,a.manifest]
        with self.assertRaisesRegex(ValueError,'duplicate'):self.parse(h,b'xx')


if __name__=='__main__':unittest.main()
