"""Actual nonexecuting CLI processes; source read is not effect admission."""
import os,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class ProgramCliTests(unittest.TestCase):
 def run_cli(self,*args):return subprocess.run([sys.executable,'-B','-m','branchwrite',*args],cwd=ROOT,env={**os.environ,'PYTHONPATH':str(ROOT)},capture_output=True,timeout=10)
 def test_check_reports_syntax_only_and_changes_no_files(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'workflow.bw';raw=b'FLOW task\nACT call plan=not-authorized\nEND\n';p.write_bytes(raw)
   result=self.run_cli('check',str(p));self.assertEqual(result.returncode,0,result.stderr)
   self.assertIn(b'Execution: NOT_RUN',result.stdout);self.assertEqual(p.read_bytes(),raw);self.assertEqual(list(Path(d).iterdir()),[p])
 def test_canonicalize_outputs_exact_program_without_editing_source(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'workflow.bw';raw=b'PLAN p from=x against=y -> frozen\n';p.write_bytes(raw)
   result=self.run_cli('canonicalize',str(p));self.assertEqual(result.returncode,0,result.stderr)
   self.assertEqual(result.stdout,b'PLAN p against=y from=x -> frozen\n');self.assertEqual(p.read_bytes(),raw)
 def test_bad_utf8_crlf_and_truncated_program_exit_nonzero_without_outputs(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'workflow.bw'
   for raw,reason in [(b'FLOW a\r\nEND\r\n',b'LF'),(b'FLOW a\n',b'unfinished'),(b'\xff',b'UTF-8')]:
    p.write_bytes(raw)
    result=self.run_cli('check',str(p));self.assertEqual(result.returncode,2);self.assertNotIn(b'Syntax OK',result.stdout);self.assertIn(reason,result.stderr)
 def test_canonicalize_preserves_utf8_literal_bytes(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'workflow.bw';raw='TEXT literal\n|Cow \U0001f42e and \u03b1\u2028\u03b2\nEND\n'.encode('utf8');p.write_bytes(raw)
   result=self.run_cli('canonicalize',str(p));self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stdout,raw)
 def test_oversize_input_is_rejected_before_parser_entry(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'workflow.bw';p.write_bytes(b'x'*1000001)
   script="import branchwrite.__main__ as cli\ndef deny(*a,**k):raise AssertionError('oversize input reached parser')\ncli.parse=deny\nraise SystemExit(cli.main(['check',"+repr(str(p))+"]))\n"
   result=subprocess.run([sys.executable,'-B','-c',script],cwd=ROOT,env={**os.environ,'PYTHONPATH':str(ROOT)},capture_output=True,timeout=10)
   self.assertEqual(result.returncode,2);self.assertIn(b'source byte limit',result.stderr)
 def test_check_has_no_native_or_tool_dispatch(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'workflow.bw';p.write_bytes(b'FLOW task\nACT do plan=p\nEND\n')
   script="import socket,subprocess\ndef deny(*a,**k):raise AssertionError('no network/process dispatch')\nsocket.socket=deny\nsubprocess.Popen=deny\nfrom branchwrite.__main__ import main\nraise SystemExit(main(['check',"+repr(str(p))+"]))\n"
   result=subprocess.run([sys.executable,'-B','-c',script],cwd=ROOT,env={**os.environ,'PYTHONPATH':str(ROOT)},capture_output=True,timeout=10)
   self.assertEqual(result.returncode,0,result.stderr)
 def test_fifo_source_is_rejected_without_waiting_for_a_writer(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'workflow.bw';os.mkfifo(p,0o600)
   result=self.run_cli('check',str(p));self.assertEqual(result.returncode,2);self.assertIn(b'regular file',result.stderr)
 def test_unimplemented_run_never_claims_execution_support(self):
  result=self.run_cli('run','untrusted.bw');self.assertEqual(result.returncode,2);self.assertNotIn(b'PASS',result.stdout)
if __name__=='__main__':unittest.main()
