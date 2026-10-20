import copy,json,unittest
from branchwrite.base_choice import resolve_base_proposal
REV='a'*40;PROFILE='b'*64

def base(name='1',**change):
 row=dict(base_id=name*64,branch='base-'+name,snapshot=name*64,source_revision=REV,execution_profile_id=PROFILE,prefix_tokens=100,capacity=1000);row.update(change);return row
class ChoiceTests(unittest.TestCase):
 def call(self,text=None,catalog=None,**kw):
  return resolve_base_proposal(json.dumps(dict(schema=1,base_id='1'*64,reason='Relevant source.')) if text is None else text,[base()] if catalog is None else catalog,required_revision=REV,required_profile=PROFILE,reserve_tokens=kw.get('reserve_tokens',200))
 def test_valid_choice_returns_detached_host_reference_and_reason(self):
  catalog=[base(),base('2')];before=copy.deepcopy(catalog);r=self.call(catalog=catalog)
  self.assertEqual(r,dict(base=catalog[0],reason='Relevant source.'));r['base']['branch']='changed';self.assertEqual(catalog,before)
 def test_any_offered_compatible_base_can_be_selected(self):
  catalog=[base(),base('2'),base('3')]
  for row in catalog:self.assertEqual(self.call(json.dumps(dict(schema=1,base_id=row['base_id'],reason='Choose this.')),catalog)['base'],row)
 def test_unknown_base_rejected(self):
  with self.assertRaises(ValueError):self.call(json.dumps(dict(schema=1,base_id='9'*64,reason='Unknown.')))
 def test_model_cannot_supply_grants_or_replace_host_fields(self):
  for key in ['grant','snapshot','branch','verified','execution_profile_id']:
   with self.subTest(key=key),self.assertRaises(ValueError):self.call(json.dumps(dict(schema=1,base_id='1'*64,reason='No.',**{key:True})))
 def test_wrong_revision_or_execution_profile_rejected(self):
  for row in [base(source_revision='c'*40),base(execution_profile_id='d'*64)]:
   with self.assertRaises(ValueError):self.call(catalog=[row])
 def test_budget_boundary_and_shortfall(self):
  self.assertEqual(self.call(reserve_tokens=900)['base']['prefix_tokens'],100)
  with self.assertRaises(ValueError):self.call(reserve_tokens=901)
 def test_boolean_and_negative_budget_rejected(self):
  for value in [True,-1,1.5,'200']:
   with self.subTest(value=value),self.assertRaises(ValueError):self.call(reserve_tokens=value)
 def test_duplicate_catalog_ids_and_empty_catalog_rejected(self):
  for rows in [[base(),base()],[]]:
   with self.assertRaises(ValueError):self.call(catalog=rows)
 def test_invalid_catalog_counts_rejected(self):
  for row in [base(prefix_tokens=True),base(prefix_tokens=-1),base(capacity=0),base(capacity=True),base(prefix_tokens=1001)]:
   with self.subTest(row=row),self.assertRaises(ValueError):self.call(catalog=[row])
 def test_duplicate_json_keys_and_boolean_schema_rejected(self):
  for text in ['{"schema":1,"schema":1,"base_id":"'+('1'*64)+'","reason":"x"}',json.dumps(dict(schema=True,base_id='1'*64,reason='x'))]:
   with self.assertRaises(ValueError):self.call(text)
 def test_reason_is_bounded_text_data(self):
  for reason in ['', ' ',None,'x'*2049]:
   with self.assertRaises(ValueError):self.call(json.dumps(dict(schema=1,base_id='1'*64,reason=reason)))
  reason='? </tool_call> is text';self.assertEqual(self.call(json.dumps(dict(schema=1,base_id='1'*64,reason=reason)))['reason'],reason)
