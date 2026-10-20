import inspect,textwrap,unittest,json,io
from pathlib import Path
import branchwrite.cow_client as module
import test_generation_reconciliation as cases
original=module.CowClient.reconcile_generation
source=textwrap.dedent(inspect.getsource(original))
mutants={
 'skip-durable-proof':('if not observation.durable:', 'if False:'),
 'skip-endpoint-owner':('if (record.get("endpoint_url") != self.endpoint_url\n            or record.get("endpoint_pin") != self.endpoint_pin):','if False:'),
 'skip-proof-receipt-comparison':('if (len(completions) != 1 or _canonical(completions[0].get("receipt"))\n            != _canonical(dict(observation.receipt.raw))):','if False:'),
}
results=[]
for name,(old,new) in mutants.items():
 assert old in source,(name,source)
 namespace=dict(module.__dict__);exec(compile(source.replace(old,new),'<mutant-'+name+'>','exec'),namespace)
 try:
  module.CowClient.reconcile_generation=namespace['reconcile_generation']
  output=io.StringIO();suite=unittest.defaultTestLoader.loadTestsFromTestCase(cases.GenerationReconciliationTests)
  result=unittest.TextTestRunner(stream=output,verbosity=2).run(suite)
  Path(__file__).with_name(name+'.log').write_text(output.getvalue())
  row=dict(mutant=name,executed=result.testsRun,failures=len(result.failures),errors=len(result.errors),detected=not result.wasSuccessful())
  results.append(row)
 finally:module.CowClient.reconcile_generation=original
Path(__file__).with_name('mutation-results.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2));assert all(r['detected'] for r in results)
