"""Production parser against normative examples and independent frozen oracle."""
import itertools,random,unittest
from pathlib import Path
from branchwrite.language import parse,render,Statement,DEFINITIONS,OPERATIONS,ProgramSyntaxError
from reference import language as oracle
ROOT=Path(__file__).resolve().parents[1]
def projected(nodes):
 return tuple((x.opcode,x.label,x.attributes,x.output,x.literal,projected(x.body)) for x in nodes)
def reference(nodes):
 return tuple((x.op,x.name,x.fields,x.result,x.text,reference(x.children)) for x in nodes)
class ProgramLanguageTests(unittest.TestCase):
 def test_published_examples_match_independent_reference(self):
  for p in (ROOT/'examples').glob('*.bw'):
   source=p.read_text()
   with self.subTest(path=p.name):self.assertEqual(projected(parse(source)),reference(oracle.parse(source)));self.assertEqual(parse(render(parse(source))),parse(source))
 def test_definitions_cover_exact_contract_without_mutable_views(self):
  self.assertEqual(OPERATIONS,oracle.OPERATIONS);self.assertEqual(set(DEFINITIONS),set(oracle.FIELDS))
  for name,d in DEFINITIONS.items():
   self.assertEqual(set(d.required),set(oracle.FIELDS[name][0].split()));self.assertEqual(set(d.optional),set(oracle.FIELDS[name][1].split()))
  with self.assertRaises(TypeError):DEFINITIONS['SHELL']=None
 def test_each_definition_and_optional_field_uses_same_production_parser(self):
  for op,d in DEFINITIONS.items():
   attrs={k:('2' if k=='max' else 'value') for k in d.required+d.optional}
   row=op+' command'+''.join(' '+k+'='+v for k,v in attrs.items())+'\n'
   source=row+'END\n' if op=='TEXT' or d.block else row
   with self.subTest(op=op):self.assertEqual(projected(parse(source)),reference(oracle.parse(source)))
 def test_field_order_has_one_canonical_meaning(self):
  for keys in itertools.permutations(['input=x','target=y','evidence=z']):
   source='COMMIT publish '+' '.join(keys)+' -> receipt\n'
   self.assertEqual(render(parse(source)),'COMMIT publish evidence=z input=x target=y -> receipt\n')
 def test_text_control_like_lines_stay_exact_literal_data(self):
  source='FLOW work\nTEXT payload\n|ACT x plan=bad\n|END\n||literal\n|\n|\u03b1\u2028\u03b2 \U0001f42e\n|\tdata\nEND\nEND\n'
  node=parse(source)[0].body[0]
  self.assertEqual(node.literal,'ACT x plan=bad\nEND\n|literal\n\n\u03b1\u2028\u03b2 \U0001f42e\n\tdata\n');self.assertEqual(render(parse(source)),source)
 def test_empty_text_and_nested_explicit_stack(self):
  self.assertEqual(parse('TEXT note\nEND\n')[0].literal,'')
  source='FLOW a\nREPEAT b max=2 until=ready exhausted=abandon\nBRANCH c base=root\nACT d plan=known -> out\nEND\nEND\nEND\n'
  self.assertEqual(projected(parse(source)),reference(oracle.parse(source)))
 def test_limits_and_exact_integer_budget_types(self):
  with self.assertRaises(ProgramSyntaxError):parse('FLOW a\nFLOW b\nEND\nEND\n',max_depth=1)
  with self.assertRaises(ProgramSyntaxError):parse('TEXT n\n|\U0001f42e\nEND\n',max_bytes=16)
  with self.assertRaises(ProgramSyntaxError):parse('FLOW a\nACT b plan=x\nEND\n',max_nodes=1)
  for kwargs in [dict(max_depth=True),dict(max_bytes=-1),dict(max_nodes=0)]:
   with self.subTest(kwargs=kwargs),self.assertRaises(ProgramSyntaxError):parse('FLOW a\nEND\n',**kwargs)
 def test_bad_control_and_truncated_blocks_are_rejected(self):
  rows=['','FLOW a\nEND','FLOW a\r\nEND\r\n','FLOW a\n\nEND\n','ACT a plan=p plan=q\n','ACT a plan=p unsafe=yes\n','ACT a\n','ASK a from=x task=t profile=p\n','DO a plan=p\n','LOOK a target=x\n','CHECK a input=x contract=c\n','STOP a target=x reason=x\n','ACT a plan=p;rm\n','{"tool":"ACT"}\n','END\n','FLOW a\n','TEXT a\nACT x plan=p\nEND\n','TEXT a\n|data\n','EXEC a plan=p\n','REPEAT r max=0 until=x exhausted=y\nEND\n','REPEAT r max=01 until=x exhausted=y\nEND\n','REPEAT r max=1000001 until=x exhausted=y\nEND\n','ACT a plan=p -> x extra\n','ACT a plan=p -> x -> y\n','ACT\ta plan=p\n','ACT  a plan=p\n',' ACT a plan=p\n','TEXT a\n|\x00\nEND\n','ACT a plan="p"\n','ACT 1a plan=p\n','TEXT a -> b\nEND\n']
  for row in rows:
   with self.subTest(row=repr(row)),self.assertRaises(ProgramSyntaxError):parse(row)
 def test_render_rejects_invalid_hand_constructed_tree(self):
  for kwargs in [dict(opcode='ACT',label='a',attributes=(('plan','x'),),body=(Statement('TEXT','n',literal=''),)),dict(opcode='TEXT',label='n',literal='missing LF'),dict(opcode='ACT',label='a',attributes=(('plan','x'),('plan','y')))]:
   with self.subTest(kwargs=kwargs),self.assertRaises(ProgramSyntaxError):render((Statement(**kwargs),))
 def test_seeded_variants_match_oracle_without_copying_its_parser(self):
  rng=random.Random(271828)
  for i in range(120):
   op=rng.choice(sorted(OPERATIONS));d=DEFINITIONS[op];fields=[k+'=handle-'+str(rng.randrange(100)) for k in d.required];rng.shuffle(fields)
   source='FLOW task'+str(i)+'\nTEXT literal\n|END and COMMIT remain data \U0001f42e\nEND\n'+op+' work '+' '.join(fields)+' -> result\nEND\n'
   with self.subTest(i=i):self.assertEqual(projected(parse(source)),reference(oracle.parse(source)));self.assertEqual(render(parse(source)),oracle.render(oracle.parse(source)))
 def test_production_has_no_reference_import(self):
  for name in ['language.py','control_contract.py','__main__.py']:
   import ast
   tree=ast.parse((ROOT/'branchwrite'/name).read_text())
   for n in ast.walk(tree):
    if isinstance(n,ast.ImportFrom):self.assertFalse((n.module or '').startswith('reference'))
    if isinstance(n,ast.Import):self.assertFalse(any(a.name.startswith('reference') for a in n.names))
if __name__=='__main__':unittest.main()
