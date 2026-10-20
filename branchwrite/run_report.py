"""Read-only presentation of canonical results. Check success is not task acceptance.

The model's finish text is evidence of what it reported, never a verifier. Do
not infer success/failure from English phrases or infer completion from exit 0.
"""
from pathlib import Path
import unicodedata
from .kernel import FrameKernel
from .records import RuntimeLog, Artifact, decode, CorruptLog


def terminal_text(text):
    """Keep readable Unicode while preventing model-supplied terminal controls."""
    return "".join(char if char in "\n\t" or unicodedata.category(char) not in ("Cc", "Cf")
                   else "\\u%04x" % ord(char) for char in text)


def read_report(state):
    with RuntimeLog(Path(state) / "ledger", read_only=True) as log:
        roots = [frame for frame in FrameKernel(log).frames() if frame["parent"] is None]
        if len(roots) != 1 or roots[0]["contract"] != ("ProgramResult", "record"):
            raise CorruptLog("run has no unique coding result")
        root = roots[0]
        result = dict(status="waiting", checks_passed=None, answer=None, acceptance="not_independently_established")
        if root["state"] != "Closed":
            return result
        payload = decode(log.read_artifact(Artifact(*root["result"])))[2]
        if type(payload.get("verified")) is not bool:
            raise CorruptLog("result has no verification boolean")
        result.update(status="finished", checks_passed=payload["verified"])
        # Follow the root's final lexical outcome. Never show a finish from an
        # abandoned iteration or a different branch just because it is newer.
        binding = payload.get("bindings", {}).get("outcome")
        if binding is not None:
            if not isinstance(binding, tuple) or len(binding) != 2 or binding[0] != "ToolOutcome":
                raise CorruptLog("invalid final outcome binding")
            outcome = binding[1]
            if outcome.get("tool") == "finish" and outcome.get("requested_finish") is True:
                ref = Artifact(*outcome["stdout"])
                if ref.size_bytes > 4 * 1024 * 1024:
                    raise CorruptLog("finish answer exceeds display bound")
                result["answer"] = log.read_artifact(ref).decode("utf-8", errors="strict")
        return result


def continuation_projection(state, connection):
    """Last completed model turn, or the original prefix if none completed.

    A partial native answer is not repurposed as a stopped user boundary. A
    new steering task forks the last complete boundary and receives fresh file
    facts. An unresolved tool or native operation must be reconciled first.
    """
    with RuntimeLog(Path(state)/'ledger',read_only=True) as log:
        kernel=FrameKernel(log);frames=kernel.frames();root=kernel.frame('program')
        for frame in frames:
            if frame['dispatch'] is not None and frame['state']!='Closed':
                raise ValueError('an operation is unresolved; reconcile before branching')
        initial=decode(log.read_artifact(Artifact(*root['inputs'])))['bindings'].get('current')
        selected=None
        if initial is not None:selected=initial[1]
        for frame in frames:
            if frame['state']=='Closed' and frame['contract']==('ModelOutput','record'):
                result=decode(log.read_artifact(Artifact(*frame['result'])))[2]
                receipt=result['native_receipt']
                if receipt['model_contract_id']!=connection['model_contract_id'] or receipt['execution_profile_id']!=connection['execution_profile_id']:
                    raise ValueError('model result belongs to a different execution profile')
                selected=dict(head=receipt['branch'],mode='append_user')
        completed=any(frame['state']=='Closed' and frame['contract']==('ModelOutput','record') for frame in frames)
        if selected is None:return dict(context=None,contains_request=completed)
        head=selected['head']
        context=dict(branch=head['name'],tip=head['tip'],root=head['root'],revision=head['revision'],
            model_contract_id=connection['model_contract_id'],execution_profile_id=connection['execution_profile_id'],mode=selected['mode'])
        return dict(context=context,contains_request=completed)


def continuation_context(state, connection):
    return continuation_projection(state,connection)['context']


def initial_context(state, connection):
    """Read the originally admitted model boundary, including a prepared prefix.

    Editing the first user request can fork that retained prefix rather than
    publishing a second bootstrap. The existing workflow owns these references.
    No log, token history, controller or checkpoint is reconstructed here.
    """
    with RuntimeLog(Path(state)/'ledger',read_only=True) as log:
        kernel=FrameKernel(log);root=kernel.frame('program')
        if root['parent'] is not None or root['contract']!=('ProgramResult','record'):
            raise CorruptLog('run has no coding root')
        current=decode(log.read_artifact(Artifact(*root['inputs']))).get('bindings',{}).get('current')
        if current is None:return None
        if type(current) is not tuple or len(current)!=2 or current[0]!='COWSource':
            raise CorruptLog('invalid original COW boundary')
        value=current[1];head=value['head']
        result=dict(branch=head['name'],tip=head['tip'],root=head['root'],revision=head['revision'],
            model_contract_id=connection['model_contract_id'],execution_profile_id=connection['execution_profile_id'],mode=value['mode'])
        from .workspace_versions import WorkspaceVersions
        return WorkspaceVersions._context(result)
