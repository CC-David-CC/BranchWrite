from pathlib import Path
import json
b=Path(__file__).parent
plan=json.loads((b/'oracle-plan.json').read_text())
audit=json.loads((b/'ledger-audit-result.json').read_text())
shells=[t for t in audit['tools'] if t['tool']=='run_shell']
assert any(t['arguments']['command']==plan['required_command'] and t['exit_code']==0 for t in shells)
stale=[t for t in shells if any(name in t['arguments']['command'] for name in plan['forbidden_stale_commands'])]
assert not stale,stale
value=dict(status='PASS',required_command=plan['required_command'],shell_commands=[dict(command=t['arguments']['command'],exit_code=t['exit_code']) for t in shells],stale_command_count=len(stale))
(b/'policy-audit-result.json').write_text(json.dumps(value,indent=2));print(json.dumps(value))
