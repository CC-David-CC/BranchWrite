# Test-only immutable registry fixture: constrain only the initial4K final action.
from branchwrite import coding_defaults
_original_registry=coding_defaults.grammar_registry
def recovery_fixture(registry):
 result=_original_registry(registry)
 before={name:json.dumps(value,sort_keys=True) for name,value in result['states'].items()}
 literal=json.dumps(dict(tool='finish',arguments=dict(answer='Deliberate initial completion probe.')),separators=(',',':'))
 result['states']['BW_TOOLS']['source']['final']=dict(format='gbnf',source='root ::= '+json.dumps(literal)+'\n')
 assert all(json.dumps(value,sort_keys=True)==before[name] for name,value in result['states'].items() if name!='BW_TOOLS')
 Path(os.environ['BW_RECOVERY_REGISTRY_PROOF']).write_text(json.dumps(dict(scope='Forced initial finish control; not a model-quality failure',only_state_changed='BW_TOOLS',next_state_unchanged='BW_TOOLS_THINK_8192',registry=result),indent=2)+'\n')
 return result
coding_defaults.grammar_registry=recovery_fixture
