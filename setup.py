"""Build-only copies of canonical examples; no second source asset set."""
from pathlib import Path
from setuptools import setup
from setuptools.command.build_py import build_py
EXAMPLES=("coding.bw","terminal-worked-examples.txt","tool-worked-examples.txt","line-file-worked-examples.txt","literal-file-worked-examples.txt","pdf-worked-examples.txt")
class ClientBuild(build_py):
 def run(self):
  super().run()
  target=Path(self.build_lib)/"branchwrite"/"_examples"
  target.mkdir(parents=True,exist_ok=True)
  for name in EXAMPLES:self.copy_file(str(Path("examples")/name),str(target/name))
setup(cmdclass={"build_py":ClientBuild})
