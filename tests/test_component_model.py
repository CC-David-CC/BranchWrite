import hashlib,json,unittest
from branchwrite.component_model import reference_report,compare_report,parse_report,schema,question
class ComponentReportTests(unittest.TestCase):
 def observation(self):
  raw=b'literal $HOME \xff\x00\n'
  return dict(status='PASS',checks=dict(real_component_fixture=True),actual=dict(disposition='exited',exit_code=7,stdout=dict(hex=raw.hex(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()),stderr=dict(hex='',bytes=0,sha256=hashlib.sha256(b'').hexdigest())),feedback=dict(stdout=raw.decode('utf8','replace'),stderr='',stdout_display=dict(lossy=True),stderr_display=dict(lossy=False),command='example',exit_code=7))
 def test_exact_line_endings_status_and_original_byte_counts(self):
  observation=self.observation();truth=reference_report(observation)
  self.assertTrue(truth['stdout_final_lf']);self.assertTrue(truth['stdout_lossy'])
  actual,errors=compare_report(json.dumps(truth),truth);self.assertEqual(errors,{})
  changed=dict(truth,stdout=truth['stdout'].rstrip('\n'),exit_code=0)
  self.assertEqual(set(compare_report(json.dumps(changed),truth)[1]),{'stdout','exit_code'})
 def test_bool_cannot_impersonate_integer(self):
  truth=reference_report(self.observation());truth['exit_code']=True
  with self.assertRaises(ValueError):parse_report(json.dumps(truth))
 def test_duplicate_or_extra_fields_rejected(self):
  with self.assertRaises(ValueError):parse_report('{"a":1,"a":2}')
  truth=reference_report(self.observation());truth['unexpected']=1
  with self.assertRaises(ValueError):parse_report(json.dumps(truth))
 def test_corrupt_or_failed_observation_rejected(self):
  o=self.observation();o['actual']['stdout']['bytes']+=1
  with self.assertRaises(ValueError):reference_report(o)
  o=self.observation();o['status']='FAIL'
  with self.assertRaises(ValueError):reference_report(o)
 def test_question_and_grammar_do_not_embed_expected_verdict(self):
  o=self.observation();o['expected']='SECRET_EXPECTATION'
  self.assertNotIn('SECRET_EXPECTATION',question(o))
  self.assertNotIn('enum',json.dumps(schema()))
if __name__=='__main__':unittest.main()
