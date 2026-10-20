import hashlib,tempfile,unittest
from pathlib import Path
from PIL import Image
import build123d as b
from test_cad_geometry import fixture
from branchwrite.cad_render import render_step
class CadRenderTests(unittest.TestCase):
 def test_views_are_derived_from_exact_step_and_revisions_change_pixels(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);p=root/'part.step';b.export_step(fixture(),p)
   result=render_step(p,root/'views')
   self.assertEqual(result['artifact_sha256'],hashlib.sha256(p.read_bytes()).hexdigest())
   self.assertEqual(set(result['views']),{'top','bottom','side','isometric'})
   self.assertGreater(result['triangles'],100)
   for row in result['views'].values():
    image=Path(row['path']);self.assertEqual(hashlib.sha256(image.read_bytes()).hexdigest(),row['sha256'])
    with Image.open(image) as im:self.assertEqual(im.format,'PNG');self.assertGreater(im.width,400)
   self.assertTrue(Path(result['contact_sheet']['path']).is_file())
   b.export_step(fixture(notch_x=-47),p);other=render_step(p,root/'mirrored')
   self.assertNotEqual(result['artifact_sha256'],other['artifact_sha256'])
   self.assertNotEqual(result['views']['top']['sha256'],other['views']['top']['sha256'])
 def test_existing_output_directory_is_not_overwritten(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);p=root/'part.step';b.export_step(fixture(),p)
   out=root/'views';out.mkdir();(out/'keep').write_text('keep')
   with self.assertRaises(FileExistsError):render_step(p,out)
   self.assertEqual((out/'keep').read_text(),'keep')
