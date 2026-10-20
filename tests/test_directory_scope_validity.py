"""Additional path-validity checks, frozen before reading the candidate."""
import unittest,tempfile
from pathlib import Path
from branchwrite.project_scope import expand_directories
class CoveredScopeValidityTests(unittest.TestCase):
 def test_root_does_not_hide_missing_selected_directory(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises((ValueError,OSError)):expand_directories(Path(d),['.','missing'])
 def test_parent_does_not_hide_selected_file_instead_of_directory(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'pkg').mkdir();(p/'pkg/file.py').write_text('pass')
   with self.assertRaises((ValueError,OSError)):expand_directories(p,['pkg','pkg/file.py'])
 def test_parent_does_not_hide_missing_deep_scope(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'pkg').mkdir()
   with self.assertRaises((ValueError,OSError)):expand_directories(p,['pkg','pkg/missing/deep'])
