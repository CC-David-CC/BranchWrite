"""Finite control grammar is derived from admitted production statements."""
import json,tempfile,unittest
from pathlib import Path
from branchwrite.control_contract import control_contract
from branchwrite.language import ProgramSyntaxError,render
class ControlContractTests(unittest.TestCase):
 def choices(self):return ['ACT execute plan=known-plan -> outcome\n','ABANDON decline target=attempt reason=declined\n']
 def test_contract_binds_frontier_and_canonical_choice_identity(self):
  a=control_contract(self.choices(),frontier_sha256='a'*64);b=control_contract(list(reversed(self.choices())),frontier_sha256='a'*64)
  self.assertEqual(a.identity,b.identity);self.assertEqual(a.grammar,b.grammar);self.assertTrue(a.inference_required)
  self.assertNotEqual(a.identity,control_contract(self.choices(),frontier_sha256='b'*64).identity)
  self.assertEqual(render((a.accept(self.choices()[0]),)),self.choices()[0])
 def test_unlisted_plan_extra_statement_and_partial_have_no_authority(self):
  c=control_contract(self.choices(),frontier_sha256='a'*64)
  for row in ['ACT execute plan=foreign -> outcome\n',self.choices()[0]+self.choices()[1],'ACT execute plan=known-plan -> outcome','The answer is '+self.choices()[0]]:
   with self.subTest(row=repr(row)),self.assertRaises(ProgramSyntaxError):c.accept(row)
 def test_data_and_structural_blocks_cannot_be_control_choices(self):
  for choices in [[],['TEXT data\n|ACT x plan=known\nEND\n'],['FLOW x\nACT a plan=p\nEND\n']]:
   with self.subTest(choices=choices),self.assertRaises(ProgramSyntaxError):control_contract(choices,frontier_sha256='a'*64)
  with self.assertRaises(ProgramSyntaxError):control_contract(self.choices(),frontier_sha256='not-a-digest')
 def test_singleton_is_explicit_host_derivable_choice_not_inference(self):
  c=control_contract([self.choices()[0],self.choices()[0]],frontier_sha256='a'*64)
  self.assertFalse(c.inference_required);self.assertEqual(len(c.choices),1)
 def test_compiles_in_existing_cow_cpu_grammar_without_permitting_foreign_plan(self):
  from serve.cow_grammar import GrammarRegistry
  from test_grammar_first import TinyByteTokenizer
  from context_time_travel.store import IntegrityError
  c=control_contract(self.choices(),frontier_sha256='a'*64);tok=TinyByteTokenizer()
  with tempfile.TemporaryDirectory() as d:
   config=Path(d)/'registry.json';config.write_text(json.dumps(dict(schema=1,states=dict(CONTROL=dict(format='gbnf',source=c.grammar)))))
   registry=GrammarRegistry.load(config,tok,[tok.EOS])
   def consume(text):
    state=registry.start('CONTROL','control-fixture',[],len(tok.tokens));session=registry.restore(state,[])
    for token in tok.encode(text,parse_special=False):state=session.consume(state,token,tok.token_bytes(token),False)
    return session
   for node in c.choices:self.assertTrue(consume(render((node,))).is_complete())
   # Emission is canonical field order; host admission accepts equivalent order.
   self.assertEqual(c.accept(self.choices()[1]),c.accept(render((c.accept(self.choices()[1]),))))
   with self.assertRaises(IntegrityError):consume(self.choices()[1])
   self.assertFalse(consume('ACT execute plan=').is_complete())
   with self.assertRaises(IntegrityError):consume('ACT execute plan=foreign -> outcome\n')
if __name__=='__main__':unittest.main()
