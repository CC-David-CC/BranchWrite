"""The owner-thread .bw interpreter, on the existing FrameKernel only.

COW owns native state. ToolRegistry owns grants and frozen effects. This driver
admits dependent work only after its input returns; no transcript or second log.
Advanced language forms remain explicit preflight refusals until implemented.
"""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import json
import re
from types import MappingProxyType
from .records import Artifact,encode,decode
from .kernel import CallSpec,ResultContract,TransitionError
from .language import parse,render
from .tool_registry import ToolRegistry,FrozenToolPlan,FileObservation,ToolOutcome
from .tool_dispatch import tool_call,dispatch_tool
from .model_dispatch import model_call,step_model,FrozenModelCall
from . import planning_retry as retry_module
from .cow_client import BranchHead
from .execution import ToolRejected
from .cad_tools import CadPolicy
from .blender_tools import BlenderPolicy
from .verification import FileReadbackPolicy,PageCapturePolicy,InspectedPagePolicy,InteractivePagePolicy,CommandEvidencePolicy,ProjectChecksPolicy,ReadOnlyPolicy
from .model_inputs import model_content
from . import thinking_ladder as ladder_module
from . import task_breakdown as breakdown_module
from . import model_inputs as inputs_module
from . import image_feedback as image_feedback_module
from .image_feedback import image_feedback_call,step_image_feedback,feedback_definition
from . import exploration as exploration_module
from . import parallel_dispatch as parallel_module

class AdmissionError(TransitionError):pass
class ThinkingLadderExhausted(AdmissionError):pass

@dataclass(frozen=True)
class Value:
    type: str
    data: object
    @property
    def wire(self):return (self.type,self.data)

@dataclass(frozen=True)
class Step:
    status: str
    frame: str
    value: dict|None=None

_TYPES={'Text':str,'ToolProposal':str,'ModelInput':(str,list),'COWSource':dict,'World':str,
        'ModelOutput':dict,'TaskBreakdown':dict,'ToolPlan':dict,'ToolOutcome':dict,'Verification':dict,'RepeatResult':dict,
        'ParallelResult':dict,'Selection':dict}
_INITIAL={'Text','ToolProposal','ModelInput','COWSource'}
_SUPPORTED={'TEXT','VALUE','EXPAND','PLAN','ACT','TRANSFORM','VERIFY','REPEAT','PARALLEL.DO','BRANCH','SELECT'}
_TRANSFORMS={'task-breakdown':('ModelOutput','TaskBreakdown'),'cow-source':('ModelOutput','COWSource'),'tool-feedback':('ToolOutcome','Text')}

def _value(wire):
    if type(wire) is not tuple or len(wire)!=2:raise AdmissionError('typed value required')
    name,data=wire
    allowed=_TYPES.get(name)
    if allowed is None or type(data) not in (allowed if type(allowed) is tuple else (allowed,)):raise AdmissionError('value has a different registered type')
    encode(wire)
    if name=='ModelInput':
        try:data=model_content(data)
        except ValueError as exc:raise AdmissionError('invalid typed model input: '+str(exc)) from exc
    if name=='COWSource':
        if set(data)!={'head','mode'} or data['mode'] not in ('ask','append_user'):raise AdmissionError('explicit context-only ask or stopped append_user boundary required')
        BranchHead.parse(data['head'])
    return Value(name,data)

def _output(statement):return statement.output or statement.label

def _reference(log,wire):return log.read_artifact(Artifact(*wire))

def _returned(kernel,frame):
    return decode(_reference(kernel.log,frame['result']))[2]

class Interpreter:
    def __init__(self,kernel,registry,*,adapter=None,profiles=None,verification=None,progress=None,
                 worlds=None,parallel_budgets=None,dispatcher=None):
        if not isinstance(registry,ToolRegistry):raise AdmissionError('actual host ToolRegistry required')
        if progress is not None and not callable(progress):raise AdmissionError('progress observer must be callable')
        self._progress=progress
        self.kernel=kernel;self.registry=registry;self.adapter=adapter
        self.dispatcher=dispatcher
        self._parallel_budget_data=encode({} if parallel_budgets is None else parallel_budgets)
        for value in self.parallel_budgets.values():exploration_module.budget(value)
        self.worlds={}
        for name,spec in ({} if worlds is None else worlds).items():
            if (type(name) is not str or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]*',name)
                    or type(spec) is not dict or set(spec)-{'registry','verification'} or 'registry' not in spec):
                raise AdmissionError('Named host candidate worlds required')
            self.worlds[name]=Interpreter(kernel,spec['registry'],adapter=adapter,profiles=profiles,
                verification=spec.get('verification'),progress=progress,dispatcher=dispatcher)
        self.worlds=MappingProxyType(self.worlds)
        try:
            policy=FileReadbackPolicy
            if type(verification) is dict:
                if 'blender' in verification:policy=BlenderPolicy
                elif 'cad' in verification:policy=CadPolicy
                elif 'read_only' in verification:policy=ReadOnlyPolicy
                elif 'selected_checks' in verification:policy=ProjectChecksPolicy
                elif 'commands' in verification:policy=CommandEvidencePolicy
                elif 'interactive_captures' in verification:policy=InteractivePagePolicy
                elif 'inspected_captures' in verification:policy=InspectedPagePolicy
                elif 'captures' in verification:policy=PageCapturePolicy
            self._file_policy=None if verification is None else policy.admit(verification,registry)
        except (ValueError,ToolRejected) as exc:raise AdmissionError('invalid host file verification policy: '+str(exc)) from exc
        self._profile_data=encode({} if profiles is None else profiles)
        if type(self.profiles) is not dict or any(type(k) is not str or type(v) is not dict for k,v in self.profiles.items()):raise AdmissionError('host model profiles must be named mappings')
        for profile in self.profiles.values():
            if profile.get('kind')=='image-feedback':
                if (set(profile)!={'kind','source'} or type(profile['source']) is not str
                    or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]*',profile['source'])):
                    raise AdmissionError('image feedback profile requires one named source binding')
            elif set(profile)-{'settings','grammar_state','output_format','request_tokens','max_requests','max_output_tokens','max_result_bytes','thinking_ladder'}:
                raise AdmissionError('unknown model profile field')
        for profile in self.profiles.values():
            if 'thinking_ladder' not in profile:continue
            try:rungs=ladder_module.ladder(profile['thinking_ladder'])
            except ValueError as exc:raise AdmissionError('unknown thinking ladder mode') from exc
            if profile.get('output_format')!='thinking' or profile.get('grammar_state')!=rungs[0].grammar_state:
                raise AdmissionError('thinking ladder requires its initial immutable budget grammar')
        from . import tool_progress as progress_module
        from . import kernel as kernel_module, language as language_module, records as records_module, tool_dispatch as tool_module, verification as verification_module
        sources=tuple(sha256(Path(module).read_bytes()).hexdigest() for module in [__file__,kernel_module.__file__,language_module.__file__,records_module.__file__,tool_module.__file__,verification_module.__file__,inputs_module.__file__,image_feedback_module.__file__,ladder_module.__file__,retry_module.__file__,breakdown_module.__file__,progress_module.__file__,exploration_module.__file__])
        self.identity=sha256(encode(('bw.interpreter.v1',registry.identity,None if adapter is None else adapter.identity,
            self.profiles,None if self._file_policy is None else self._file_policy.identity,sources))).hexdigest()
        if self.worlds or self.parallel_budgets:
            self.identity=sha256(encode(('bw.parallel-interpreter.v1',self.identity,
                {name:context.identity for name,context in self.worlds.items()},self.parallel_budgets,
                None if dispatcher is None else dispatcher.slots,sha256(Path(parallel_module.__file__).read_bytes()).hexdigest()))).hexdigest()

    def _emit_progress(self,event):
        """Cosmetic observation from the workflow owner, never a durable result.

        Only fixed event names and closed tool names leave this boundary: no model text, arguments,
        secrets or mutable frame values. A broken display cannot turn an actual
        effect into an unresolved operation or cause it to be retried.
        """
        if self._progress is not None:
            try:self._progress(event)
            except Exception:self._progress=None

    @property
    def parallel_budgets(self):return decode(self._parallel_budget_data)

    @property
    def profiles(self):
        # Caller mutations cannot silently change the frozen execution identity.
        return decode(self._profile_data)

    def _check_program(self,source,bindings):
        return self.preflight(source,{name:value.type for name,value in bindings.items()})

    def preflight(self,source,binding_types):
        # Lexical types are compile-time inputs, not invented native snapshots.
        if type(binding_types) is not dict or any(t not in _TYPES for t in binding_types.values()):raise AdmissionError('registered lexical types required')
        program=parse(source)
        if len(program)!=1 or program[0].opcode!='FLOW' or program[0].output is not None or program[0].attributes:
            raise AdmissionError('one root FLOW with no parameters required')
        env=dict(binding_types)
        def require(name,types):
            if env.get(name) not in types:raise AdmissionError('missing or incompatible typed binding: '+name)
        def check(body):
            for statement in body:
                op=statement.opcode;a=dict(statement.attributes)
                if op not in _SUPPORTED:raise AdmissionError('unsupported execution operation: '+op)
                if op=='TEXT':typ='Text'
                elif op=='VALUE':
                    require(a['ref'],{a['type']});typ=a['type']
                elif op=='EXPAND':
                    require(a['from'],{'COWSource'});require(a['task'],{'Text','ModelInput'})
                    if self.adapter is None or a['profile'] not in self.profiles or 'kind' in self.profiles[a['profile']]:raise AdmissionError('registered model profile required')
                    typ='ModelOutput'
                elif op=='PLAN':
                    require(a['from'],{'ModelOutput','ToolProposal'});require(a['against'],{'World'});typ='ToolPlan'
                elif op=='ACT':require(a['plan'],{'ToolPlan'});typ='ToolOutcome'
                elif op=='TRANSFORM':
                    if a['contract'] not in _TRANSFORMS:raise AdmissionError('unsupported transform contract')
                    source_type,typ=_TRANSFORMS[a['contract']];require(a['input'],{source_type})
                    if 'evidence' in a:
                        if a['contract']!='tool-feedback':raise AdmissionError('verification evidence is only supported for tool-feedback')
                        require(a['evidence'],{'Verification'})
                    if 'profile' in a:
                        selected=self.profiles.get(a['profile'],{})
                        if a['contract']!='tool-feedback' or self.adapter is None or selected.get('kind')!='image-feedback':
                            raise AdmissionError('registered image feedback profile required')
                        require(selected['source'],{'COWSource'});typ='ModelInput'
                elif op=='VERIFY':
                    contracts={'blender-scene-and-finish':BlenderPolicy,'cad-geometry-and-finish':CadPolicy,'read-only-and-finish':ReadOnlyPolicy,'project-checks-and-finish':ProjectChecksPolicy,'command-evidence-and-finish':CommandEvidencePolicy,'file-readback-and-finish':FileReadbackPolicy,
                        'page-capture-and-finish':PageCapturePolicy,'page-inspection-and-finish':InspectedPagePolicy,
                        'interactive-page-inspection-and-finish':InteractivePagePolicy}
                    if a['contract'] not in ('unit-tests-and-finish',*contracts) or 'profile' in a:raise AdmissionError('unsupported verifier contract')
                    if a['contract'] in contracts:
                        if self._file_policy is None:raise AdmissionError('host file verification policy required')
                        if type(self._file_policy) is not contracts[a['contract']]:
                            raise AdmissionError('matching host capture policy required')
                    elif not self.registry._grant.allow_tests or self.registry._grant.project_files or any(p=='tests' or p.startswith('tests/') for p in (*self.registry._grant.edit_paths,*self.registry._grant.create_paths)):
                        raise AdmissionError('verification requires granted tests with protected test paths')
                    require(a['input'],{'ToolOutcome'});typ='Verification'
                elif op=='REPEAT':
                    if a['exhausted'] not in ('stop','abandon'):raise AdmissionError('unsupported exhausted disposition')
                    check(statement.body);require(a['until'],{'Verification'});typ='RepeatResult'
                elif op=='PARALLEL.DO':
                    require(a['base'],{'COWSource'})
                    if self.adapter is None:raise AdmissionError('Parallel exploration requires a COW adapter')
                    exploration_module.preflight(self,statement,env)
                    typ='ParallelResult'
                elif op=='SELECT':
                    require(a['input'],{'ParallelResult'});typ='Selection'
                else:raise AdmissionError('BRANCH is only admitted inside PARALLEL.DO')
                env[_output(statement)]=typ
        check(program[0].body)
        return program[0]

    def start(self,source,bindings=None):
        supplied={} if bindings is None else bindings
        if type(supplied) is not dict:raise AdmissionError('named host bindings required')
        frozen={}
        for name,value in supplied.items():
            if type(name) is not str or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]*',name) or name=='world' or not isinstance(value,Value) or value.type not in _INITIAL:
                raise AdmissionError('invalid initial host binding')
            frozen[name]=_value(decode(encode(value.wire)))
        frozen['world']=Value('World',self.registry.world)
        root=self._check_program(source,frozen);canonical=render((root,))
        inputs=encode(dict(schema=1,identity=self.identity,bindings={k:v.wire for k,v in frozen.items()}))
        frames=self.kernel.frames()
        if frames:
            old=self.kernel.frame('program')
            if _reference(self.kernel.log,old['definition'])!=canonical.encode() or _reference(self.kernel.log,old['inputs'])!=inputs:raise AdmissionError('run already owns a different program or inputs')
            return old
        return self.kernel.create_root('program','program-attempt',self.kernel.log.put_artifact(canonical.encode()),self.kernel.log.put_artifact(inputs),ResultContract('ProgramResult','record'))

    def _load(self,frame):
        inputs=decode(_reference(self.kernel.log,frame['inputs']))
        if type(inputs) is not dict or inputs.get('schema')!=1 or inputs.get('identity')!=self.identity:raise AdmissionError('interpreter identity changed; no automatic migration')
        source=_reference(self.kernel.log,frame['definition']).decode('utf8')
        nodes=parse(source)
        if len(nodes)!=1:raise AdmissionError('scope definition must have one node')
        return nodes[0],inputs

    def _children(self,frame):
        return sorted((f for f in self.kernel.frames() if f['parent']==frame['id']),key=lambda f:f['parent_epoch'])

    def _environment(self,frame,inputs,node):
        env={k:_value(v) for k,v in inputs['bindings'].items()}
        # Only resumed predecessors enter lexical scope, never an early result.
        for child in self._children(frame):
            if child['parent_epoch']>frame['pc']:continue
            statement=node.body[child['parent_epoch']-1];value=_returned(self.kernel,child)
            if child['contract']==('RepeatResult','record'):
                env.update({k:_value(v) for k,v in value['bindings'].items()})
                env[_output(statement)]=Value('RepeatResult',dict(disposition=value['disposition'],iterations=value['iterations']))
            elif child['contract']==('BindingResult','record'):env[_output(statement)]=_value(value['value'])
            else:env[_output(statement)]=Value(child['contract'][0],value)
        return env

    def _visible_results(self,frame,contract):
        return self.kernel.visible_results(frame,contract)

    def _visible_tool_outcomes(self,frame):
        result=[]
        for child,value in self._visible_results(frame,('ToolOutcome','record')):
            plan=decode(_reference(self.kernel.log,child['inputs']))
            if type(plan) is tuple and len(plan)==8 and plan[:3]==('bw.tool-plan.v2',self.registry.identity,self.registry.world):
                result.append((child,value))
        return tuple(result)

    def _planning_model_for_tool(self,frame,operation_id):
        # Follow the actual ACT's lexical PLAN binding, not the last model
        # output in the log. Two equal tool proposals can have different origins.
        matches=[f for f,value in self._visible_tool_outcomes(frame) if value.get('operation_id')==operation_id]
        if not matches:return None
        if len(matches)!=1:raise AdmissionError('tool operation has ambiguous workflow ownership')
        tool=matches[0]
        parent=self.kernel.frame(tool['parent']);node,inputs=self._load(parent)
        index=tool['parent_epoch']-1
        if not 0<=index<len(node.body) or node.body[index].opcode!='ACT':
            raise AdmissionError('tool result does not belong to an admitted ACT')
        before={**parent,'pc':index}
        env=self._environment(before,inputs,node)
        plan=env[dict(node.body[index].attributes)['plan']]
        if plan.type!='ToolPlan' or plan.data.get('valid') is not True or plan.data['data']!=_reference(self.kernel.log,tool['inputs']):
            raise AdmissionError('tool result does not bind its lexical PLAN')
        identifier=plan.data.get('model_frame')
        if identifier is None:return None
        model=self.kernel.frame(identifier)
        if model['contract']!=('ModelOutput','record') or model['state']!='Closed' or _returned(self.kernel,model).get('model_frame')!=identifier:
            raise AdmissionError('tool PLAN has no settled original model output')
        return identifier

    def _observations(self,frame):
        return tuple(FileObservation(*value['observation']) for _,value in self._visible_tool_outcomes(frame)
            if value['observation'] is not None)

    def _pure(self,value,identifier,provenance=()):
        data=encode(dict(schema=1,value=value.wire,provenance=tuple((a.sha256,a.size_bytes) for a in provenance)))
        return CallSpec(identifier,'attempt-'+identifier[5:],'result','FLOW',self.kernel.log.put_artifact(encode(('bw.binding.v1',self.identity))),
            self.kernel.log.put_artifact(data),ResultContract('BindingResult','record'))

    def _feedback_verification(self,frame,outcome,verdict):
        """Export a bounded public view of an actual, visible verifier return.

        Protected expected files, oracle details and answer fixtures never enter
        this projection. This is historical feedback, not a new verification or
        authority to mark the task successful.
        """
        if verdict.get('outcome_operation_id')!=outcome.get('operation_id'):
            raise AdmissionError('verification belongs to a different tool outcome')
        proof=None
        for witness,value in reversed(tuple(self._visible_results(frame,('BindingResult','record')))):
            if value.get('value')!=('Verification',verdict):continue
            parent=self.kernel.frame(witness['parent']);node,_=self._load(parent)
            statement=node.body[witness['parent_epoch']-1]
            if (statement.opcode=='VERIFY' and witness['state']=='Closed'
                    and _reference(self.kernel.log,witness['definition'])==encode(('bw.binding.v1',self.identity))):
                proof=Artifact(*witness['result']);break
        if proof is None:raise AdmissionError('matching recorded verification predecessor required')
        if verdict.get('status') not in ('pass','fail'):raise AdmissionError('invalid recorded verification status')
        public={k:verdict[k] for k in ('status','policy','reason','task_verdict','outcome_operation_id') if k in verdict}
        for key in ('policy','reason','task_verdict','outcome_operation_id'):
            if key in public and (type(public[key]) is not str or len(public[key].encode('utf8'))>2048):raise AdmissionError('unbounded verifier feedback')
        # Only user-selected checks expose their own names/statuses. Protected
        # inspections and expected-value policies have no detail export here.
        if verdict.get('policy')=='project-checks-and-finish':
            if 'check_status' in verdict or 'finish_required' in verdict:
                if verdict.get('check_status') not in ('pass','fail') or type(verdict.get('finish_required')) is not bool:
                    raise AdmissionError('invalid selected-check progress')
                public['check_status']=verdict['check_status']
                public['finish_required']=verdict['finish_required']
            for key in ('checks','remote_checks'):
                checks=verdict.get(key,())
                if not isinstance(checks,(tuple,list)) or len(checks)>128:raise AdmissionError('bounded selected checks required')
                public[key]=[{k:row[k] for k in ('name','target','status','exit_code','disposition') if k in row} for row in checks]
            for key in ('local_checks_required','remote_targets_requiring_checks'):
                if key in verdict:public[key]=verdict[key]
            documents=verdict.get('pdf_documents',())
            if documents:
                public['pdf_documents']=[dict(path=row['path'],status=row['status'],page_count=row.get('page_count'),
                    missing_pages=row.get('missing_pages',[])[:16],missing_page_count=len(row.get('missing_pages',[]))) for row in documents[:16]]
        public['scope']='recorded checked boundary'
        if len(json.dumps(public,ensure_ascii=True).encode())>32768:raise AdmissionError('verifier feedback exceeds bound')
        return public,proof

    def _verification(self,outcome,*,policy='unit-tests-and-finish',frame=None):
        result=self._verification_result(outcome,policy=policy,frame=frame)
        return dict(result,task_verdict=ladder_module.task_verdict(outcome,result),
                    outcome_operation_id=outcome.get('operation_id'))

    def _verification_result(self,outcome,*,policy='unit-tests-and-finish',frame=None):
        if policy in ('blender-scene-and-finish','cad-geometry-and-finish','read-only-and-finish','project-checks-and-finish','command-evidence-and-finish','file-readback-and-finish','page-capture-and-finish','page-inspection-and-finish','interactive-page-inspection-and-finish'):
            if self._file_policy is None or frame is None:raise AdmissionError('host file verification policy and visible scope required')
            if outcome.get('requested_finish') is not True:
                if policy=='project-checks-and-finish' and self._file_policy.progress_feedback:
                    # Evaluate existing visible receipts, not a model assertion or
                    # another tool call. Check readiness and task completion are
                    # different facts: the explicit finish gate stays closed.
                    checked=self._file_policy.verify(self.registry,self.kernel.log,self._visible_tool_outcomes(frame))
                    return dict(checked,status='fail',check_status=checked['status'],finish_required=True,
                        reason=('selected checks passed on current files; request finish after confirming they cover the task'
                            if checked['status']=='pass' else checked['reason']))
                return dict(status='fail',policy=policy,reason='explicit finish request required')
            return self._file_policy.verify(self.registry,self.kernel.log,self._visible_tool_outcomes(frame))
        if policy!='unit-tests-and-finish':raise AdmissionError('unsupported verifier contract')
        # This explicitly named policy checks the actual registered unit-test
        # receipt and current bytes. It is not universal semantic acceptance or
        # protection against hostile test-output forgery by candidate code.
        if frame is None:raise AdmissionError('visible unit-test verification scope required')
        latest=None
        # A settled tool elsewhere in the log is not an observation available
        # to this continuation. Reuse lexical, resumed predecessor visibility.
        for candidate,value in self._visible_tool_outcomes(frame):
            if value['tool']=='run_tests':latest=(candidate,value)
        reason='finish request and successful current unit-test receipt required';passed=False
        if outcome.get('requested_finish') is True and latest:
            frame,value=latest
            if value['disposition']=='exited' and value['exit_code']==0:
                stderr=_reference(self.kernel.log,value['stderr'])
                count=re.search(rb'\nRan ([1-9][0-9]*) tests? in ',stderr)
                plan=decode(_reference(self.kernel.log,frame['inputs']))
                bound=(type(plan) is tuple and len(plan)==8
                    and plan[:4]==('bw.tool-plan.v2',self.registry.identity,self.registry.world,'run_tests')
                    and value.get('plan_sha256')==frame['inputs'][0]
                    and frame['dispatch'] is not None
                    and value.get('operation_id')==frame['dispatch'][0]
                    and frame['operation']==self.registry.operation_kind('run_tests')
                    and _reference(self.kernel.log,frame['definition'])==self.registry.definition_bytes('run_tests'))
                with self.registry.executor._lock:
                    self.registry._world_check();current=self.registry._inventory()
                passed=bound and count is not None and plan[6]==current
                reason='current unit-test receipt matched' if passed else 'empty test suite or workspace changed since tests'
        return dict(status='pass' if passed else 'fail',policy='unit-tests-and-finish',reason=reason)

    def _thinking_call(self,frame,identifier,profile_name,profile,source,content):
        mode=profile.pop('thinking_ladder')
        models={}
        for candidate,value in self._visible_results(frame,('ModelOutput','record')):
            owner=value.get('model_frame')
            if owner in models:continue
            actual=self.kernel.frame(owner)
            if (actual['state']!='Closed' or actual['contract']!=('ModelOutput','record')
                    or _reference(self.kernel.log,actual['definition'])!=self.adapter.definition):
                raise AdmissionError('planning origin is not a completed registered model FLOW')
            plan=self.adapter.plan(FrozenModelCall(_reference(self.kernel.log,actual['inputs'])))
            context=plan.get('planning')
            if context is None or context['profile']!=profile_name or context['mode']!=mode:continue
            returned=_returned(self.kernel,actual)
            if (value['plan_sha256']!=actual['inputs'][0] or returned['native_receipt']!=value['native_receipt']
                    or returned.get('model_frame')!=owner or returned.get('text')!=value.get('text')
                    or value['source_snapshot']!=plan['source']['tip']):
                raise AdmissionError('planning result changed its original model source')
            head=BranchHead.parse(value['native_receipt']['branch'])
            if head.root!=plan['source']['root']:
                raise AdmissionError('planning model result changed canonical root')
            models[owner]=dict(frame=actual,plan=plan,context=context,value=value,head=head)
        previous=next((m for m in reversed(tuple(models.values())) if m['head']==source),None)
        origin=identifier if previous is None else previous['context']['origin_model_frame']
        failures=[]
        if previous is not None:
            first=models.get(origin)
            if (first is None or first['context']['origin_model_frame']!=origin
                    or first['context']['rung']!=0 or first['context']['handled_failures']
                    or first['plan']['source']['root']!=source.root):
                raise AdmissionError('original thinking model is not visible in this root/profile')
            seen=set()
            outcomes={v['operation_id']:(f,v) for f,v in self._visible_tool_outcomes(frame)}
            for witness,value in self._visible_results(frame,('BindingResult','record')):
                wire=value.get('value')
                if type(wire) is not tuple or len(wire)!=2 or wire[0]!='Verification':continue
                verdict=wire[1];owner=verdict.get('planning_model_frame');model=models.get(owner)
                if verdict.get('task_verdict')!='verified_failure' or model is None or model['context']['origin_model_frame']!=origin:continue
                if _reference(self.kernel.log,witness['definition'])!=encode(('bw.binding.v1',self.identity)):
                    raise AdmissionError('thinking failure is not a registered host verification')
                operation=verdict.get('outcome_operation_id');observed=outcomes.get(operation)
                if (observed is None or ladder_module.task_verdict(observed[1],verdict)!='verified_failure'
                        or self._planning_model_for_tool(frame,operation)!=owner):
                    raise AdmissionError('thinking failure does not bind its original ACT/PLAN')
                tool_plan=decode(_reference(self.kernel.log,observed[0]['inputs']))
                proposed_tool,proposed_args=self.registry.parse(model['value']['text'])
                if (tool_plan[:4]!=('bw.tool-plan.v2',self.registry.identity,self.registry.world,'finish')
                        or proposed_tool!='finish' or proposed_args!=tool_plan[4]):
                    raise AdmissionError('failed finish differs from its original model proposal')
                if operation not in seen:
                    seen.add(operation);failures.append((operation,witness,model))
        handled=() if previous is None else previous['context']['handled_failures']
        failure_ids=tuple(row[0] for row in failures)
        if handled!=failure_ids[:len(handled)]:
            raise AdmissionError('thinking plan handled failures are not visible predecessors')
        rung=0 if previous is None else previous['context']['rung']
        retry=len(failure_ids)>len(handled)
        if retry:
            if len(failure_ids)!=len(handled)+1 or failures[-1][2]['frame']['id']!=previous['frame']['id']:
                raise AdmissionError('retry requires one newly failed current planning attempt')
            rung=ladder_module.next_attempt(mode,rung,'verified_failure')
            if rung is None:raise ThinkingLadderExhausted('all configured thinking rungs failed host verification')
        context=ladder_module.planning_context(dict(schema=1,profile=profile_name,mode=mode,rung=rung,
            origin_model_frame=origin,handled_failures=failure_ids))
        profile={**profile,'grammar_state':ladder_module.ladder(mode)[rung].grammar_state,'planning':context}
        if not retry:
            plan=self.adapter.freeze(source,mode=content[0],content=content[1],**profile)
            return model_call(self.kernel,self.adapter,child_id=identifier,attempt_id='attempt-'+identifier[5:],slot='result',plan=plan)
        # Reuse the failed call's exact input and boundary. Its prefix may not
        # yet contain the last tool/image feedback; do not discard that input.
        failed=previous['plan'];original=models[origin]['plan']['config']['content']
        def text(value):
            return value if type(value) is str else '\n'.join(v['text'] for v in value if v['type']=='text')
        goal=text(original)
        if len(goal.encode('utf8'))>32768:goal='Complete the original task retained in this branch and the preserved input.'
        observations=text(content[1])
        if len(observations.encode('utf8'))>32768:
            observations='[Tail of already-visible observations]\n'+observations.encode('utf8')[-32000:].decode('utf8',errors='replace')
        guidance=ladder_module.recovery_guidance(goal,observations)
        prior=failed['config']['content']
        if type(prior) is str:new_content=prior+'\n\n'+guidance
        else:
            new_content=model_content(prior)
            index=next(i for i in reversed(range(len(new_content))) if new_content[i]['type']=='text')
            new_content[index]['text']+='\n\n'+guidance
        with self.registry.executor._lock:
            self.registry._world_check()
            world=self.kernel.log.put_artifact(encode(('bw.planning-world.v1',self.registry.world,self.registry._inventory())))
        provenance=(Artifact(*failures[-1][1]['result']),Artifact(*previous['frame']['result']),
                    Artifact(*models[origin]['frame']['inputs']),world)
        return retry_module.retry_model_call(self.kernel,self.adapter,child_id=identifier,
            attempt_id='attempt-'+identifier[5:],slot='result',source=source,snapshot=failed['source']['tip'],
            mode=failed['config']['mode'],content=new_content,profile=profile,provenance=provenance)

    def _admit(self,frame,node,env):
        statement=node.body[frame['pc']];op=statement.opcode;a=dict(statement.attributes)
        identifier='call-'+sha256(encode((self.identity,frame['id'],frame['epoch'],frame['pc']))).hexdigest()[:48]
        provenance=()
        if op=='TEXT':value=Value('Text',statement.literal)
        elif op=='VALUE':value=env[a['ref']]
        elif op=='EXPAND':
            source=env[a['from']].data;profile=self.profiles[a['profile']]
            if 'thinking_ladder' in profile:
                return self._thinking_call(frame,identifier,a['profile'],profile,BranchHead.parse(source['head']),
                    (source['mode'],env[a['task']].data))
            plan=self.adapter.freeze(BranchHead.parse(source['head']),mode=source['mode'],content=env[a['task']].data,**profile)
            return model_call(self.kernel,self.adapter,child_id=identifier,attempt_id='attempt-'+identifier[5:],slot='result',plan=plan)
        elif op=='PLAN':
            if env[a['against']].data!=self.registry.world:raise AdmissionError('wrong world binding')
            proposed=env[a['from']];text=proposed.data['text'] if proposed.type=='ModelOutput' else proposed.data
            try:
                plan=self.registry.freeze(text,observations=self._observations(frame))
                value=Value('ToolPlan',dict(valid=True,data=plan.data,model_frame=proposed.data['model_frame'] if proposed.type=='ModelOutput' else None))
            except ToolRejected as exc:
                value=Value('ToolPlan',dict(valid=False,error=str(exc)[:1024],proposal_sha256=sha256(text.encode()).hexdigest()))
        elif op=='ACT':
            data=env[a['plan']].data
            if data['valid']:
                return tool_call(self.kernel,self.registry,child_id=identifier,attempt_id='attempt-'+identifier[5:],slot='result',plan=FrozenToolPlan(data['data']))
            outcome=ToolOutcome('rejected_before_admission',None,0.0,b'',data['error'].encode(),identifier,data['proposal_sha256'],'unadmitted')
            result,provenance=outcome.publish(self.kernel.log);value=Value('ToolOutcome',result)
        elif op=='TRANSFORM':
            source=env[a['input']]
            if a['contract']=='task-breakdown':
                # Derivation only: a proposed graph cannot grant tools, run a
                # child, select a prefill, or satisfy a host verification.
                data=source.data;origin=self.kernel.frame(data['model_frame'])
                if (origin['state']!='Closed' or origin['contract']!=('ModelOutput','record')
                        or _returned(self.kernel,origin)!=data):
                    raise AdmissionError('breakdown lacks its original completed model result')
                try:plan=breakdown_module.parse_breakdown(data['text']);reason=None
                except ValueError as exc:plan=None;reason=str(exc)[:1024]
                value=Value('TaskBreakdown',dict(schema=1,valid=plan is not None,plan=plan,reason=reason,
                    source=dict(model_frame=origin['id'],snapshot=data['source_snapshot'],
                                plan_sha256=data['plan_sha256'],text_sha256=sha256(data['text'].encode('utf8')).hexdigest())))
                provenance=(Artifact(*origin['result']),Artifact(*origin['inputs']))
            elif a['contract']=='cow-source':
                value=Value('COWSource',dict(head=source.data['native_receipt']['branch'],mode='append_user'))
                value=_value(value.wire)
            else:
                data=source.data;observed=data['observation']
                observation=None if observed is None else dict(world=observed[0],path=observed[1],source_sha256=observed[2])
                feedback=dict(tool=data['tool'],operation_id=data['operation_id'],plan_sha256=data['plan_sha256'],disposition=data['disposition'],exit_code=data['exit_code'],observation=observation)
                if data['tool'] in ('run_shell','run_check'):
                    # The accepted native argv already binds the exact program.
                    # Keep it beside its status so the model need not reconstruct
                    # quoting from an earlier proposal. This grants no new work.
                    feedback['command']=data['details']['argv'][-1]
                    feedback['shell_context']=dict(working_directory='prepared project root; use project-relative paths',
                        source_writes='use granted file-edit tools; shell can publish only explicitly granted output paths',
                        script_execution='use sh script.sh with its arguments for a readable script without execute permission')
                    feedback['shell_context']['completion']=('Exploration only; run_shell does not register a completion check. Use run_check with a stable name and an actual assertion when granted.' if data['tool']=='run_shell' else 'Named completion check: return zero when the tested requirement holds, including assertions about expected nonzero subprocess statuses.')
                if data['tool'] in ('remote_command','check_remote','upload_file'):
                    feedback['command']=data['details'].get('command')
                    feedback['target']=data['details'].get('target')
                    if data['tool']=='upload_file':
                        feedback['command']='host byte upload; source was not rewritten by the model'
                        for key in ('source_path','source_sha256','source_bytes','remote_path'):feedback[key]=data['details'].get(key)
                for field in ('stdout','stderr'):
                    raw=_reference(self.kernel.log,data[field]);shown=raw[:32768]
                    try:display=shown.decode('utf-8');lossy=False
                    except UnicodeDecodeError:display=shown.decode('utf-8',errors='replace');lossy=True
                    # A bounded text view is not the original output. Preserve
                    # the existing raw artifact and expose its exact identity;
                    # even a truncated valid stream can end inside a code point.
                    feedback[field]=display
                    feedback[field+'_truncated']=len(raw)>len(shown)
                    feedback[field+'_artifact']=dict(sha256=data[field][0],bytes=data[field][1])
                    feedback[field+'_display']=dict(encoding='utf-8',errors='replace',lossy=lossy,source_bytes=len(shown))
                if data['tool'] in ('run_shell','run_check'):
                    # Observed stderr can explain a failed subcommand even when
                    # a later echo makes Bash return zero. Keep the real status
                    # and raw artifacts; this hint never certifies a failure.
                    messages=[]
                    if 'read-only file system' in feedback['stderr'].lower():
                        messages.append('stderr mentions a read-only filesystem. If a source edit was attempted, use the granted file-edit tools; shell writes do not change protected source files.')
                    if 'permission denied' in feedback['stderr'].lower():
                        messages.append('stderr mentions permission denied. If a readable shell script lacks execute permission, test it with sh script.sh and its arguments; do not assume chmod is granted.')
                    if messages:
                        feedback['diagnostic_guidance']=dict(basis='observed stderr text; not a task verdict',messages=messages,
                            verification='A later echo can hide a failed subcommand in exit_code. Use explicit assertions or preserve the failing status in a named check.')
                # Only project trusted, bounded stage names. Do not dump arbitrary
                # details (runtime paths, environment or credentials) into prompts.
                # These hints never replace raw output or host verification.
                if data['exit_code'] not in (None,0) or data['disposition'] in ('rejected_before_admission','pdf_failed','cad_failed','scene_failed','timeout','output_limit'):
                    stage=data['disposition']
                    if data['tool'] in ('build_pdf','inspect_cad'):
                        observed=data['details'].get('build_disposition' if data['tool']=='build_pdf' else 'disposition')
                        if observed in ('missing_artifact','output_rejected','timeout','output_limit','worker_failed','background_processes','exited'):stage=observed
                    action='Inspect stderr, stdout and the recorded status. Check existing effects before repeating a command; a nonzero exit does not undo its work.'
                    if stage=='rejected_before_admission':
                        action='Correct the request using the reported reason and existing tool schema/grant. Read current file bytes before retrying an edit; do not bypass a denied permission.'
                    elif data['tool'] in ('build_pdf','inspect_cad'):
                        expected='document.pdf' if data['tool']=='build_pdf' else 'part.step'
                        if stage in ('missing_artifact','output_rejected'):
                            action='Update the source to export a fresh regular nonempty '+expected+' in the isolated working directory. Then run the build tool again; the requested destination name is published by the host.'
                        elif stage=='timeout':
                            action='Inspect the source for hangs or excessive work. Simplify or fix it before rebuilding within the configured time budget; do not assume an output was published.'
                        elif stage=='output_limit':
                            action='Reduce excessive program output before rebuilding. Inspect the retained bounded diagnostics; no successful artifact is established.'
                        else:
                            action='Inspect the execution diagnostics and geometry/page checks, repair the source, then rebuild and inspect the current artifact before claiming success.'
                    elif data['tool']=='inspect_scene':
                        action='Inspect the scene error, measurements and available rendered views. Repair the source and rerun scene inspection; do not accept an earlier render as the current result.'
                    feedback['problem']=dict(stage=stage,summary='Tool did not establish success; consult the observed diagnostics and verification.',next_action=action)
                if data['image'] is not None:
                    feedback['image']=dict(sha256=data['image'][0],bytes=data['image'][1],media_type='image/png')
                    feedback['capture']=data['details']
                if 'evidence' in a:
                    feedback['verification'],proof=self._feedback_verification(frame,data,env[a['evidence']].data)
                    provenance=(*provenance,proof)
                text=json.dumps(feedback,ensure_ascii=True,sort_keys=True)
                if 'profile' in a:
                    if data['image'] is not None:
                        source_name=self.profiles[a['profile']]['source']
                        return image_feedback_call(self.kernel,self.adapter,identifier=identifier,
                            source=BranchHead.parse(env[source_name].data['head']),image=Artifact(*data['image']),text=text)
                    value=Value('ModelInput',text)
                else:value=Value('Text',text)
        elif op=='VERIFY':
            outcome=env[a['input']].data
            result=self._verification(outcome,policy=a['contract'],frame=frame)
            origin=self._planning_model_for_tool(frame,outcome.get('operation_id'))
            if origin is not None:result['planning_model_frame']=origin
            value=Value('Verification',result)
        elif op=='REPEAT':
            return CallSpec(identifier,'attempt-'+identifier[5:],'result','FLOW',self.kernel.log.put_artifact(render((statement,)).encode()),
                self.kernel.log.put_artifact(encode(dict(schema=1,identity=self.identity,bindings={k:v.wire for k,v in env.items()}))),ResultContract('RepeatResult','record'))
        elif op=='PARALLEL.DO':
            return exploration_module.call(self,frame,statement,env,identifier)
        elif op=='SELECT':
            value,provenance=exploration_module.select(self,env[a['input']].data,a['rule'],frame)
        else:raise AdmissionError('unsupported execution operation: '+op)
        return self._pure(value,identifier,provenance)

    def _scope(self,identifier):
        frame=self.kernel.frame(identifier);node,inputs=self._load(frame)
        if frame['state']=='Closed':return Step('complete',identifier,_returned(self.kernel,frame))
        if frame['state']=='Waiting':return self._wait(frame)
        if frame['state']!='Ready':raise AdmissionError('scope has unresolved settlement')
        env=self._environment(frame,inputs,node)
        if frame['pc']==len(node.body):
            verified=any(v.type=='Verification' and v.data.get('status')=='pass' for v in env.values())
            # Verification is meaningful only at the byte revision it checked.
            if verified:
                finishes=[v.data for v in env.values() if v.type=='ToolOutcome' and v.data.get('requested_finish') is True]
                verified=bool(finishes) and any(self._verification(finishes[-1],policy=v.data['policy'],frame=frame)['status']=='pass'
                    for v in env.values() if v.type=='Verification' and v.data.get('status')=='pass')
            selections=[v.data for v in env.values() if v.type=='Selection']
            if selections:verified=any(exploration_module.selection_current(self,v) for v in selections)
            value=dict(schema=1,bindings={k:v.wire for k,v in env.items()},verified=verified)
            self.kernel.finish(identifier,value);return Step('complete',identifier,value)
        try:call=self._admit(frame,node,env)
        except ThinkingLadderExhausted as exc:
            return Step('thinking_ladder_exhausted',identifier,dict(reason=str(exc)))
        self.kernel.spawn(identifier,expected_epoch=frame['epoch'],calls=(call,),next_pc=frame['pc']+1)
        return Step('admitted',call.child_id)

    def _repeat(self,identifier):
        frame=self.kernel.frame(identifier);node,inputs=self._load(frame);attrs=dict(node.attributes)
        if frame['state']=='Closed':return Step('complete',identifier,_returned(self.kernel,frame))
        if frame['state']=='Waiting':return self._wait(frame)
        if frame['state']!='Ready':raise AdmissionError('repeat has unresolved settlement')
        prior=None
        if frame['pc']:
            child=self._children(frame)[-1];prior=_returned(self.kernel,child)
            inputs=dict(inputs,bindings=prior['bindings'])
        tested=inputs['bindings'].get(attrs['until'])
        passed=bool(prior and tested and tested[0]=='Verification' and tested[1]['status']=='pass' and prior['verified'])
        if passed or frame['pc']>=int(attrs['max']):
            result=dict(schema=1,bindings=inputs['bindings'],iterations=frame['pc'],disposition='verified' if passed else 'exhausted')
            self.kernel.finish(identifier,result);return Step('complete',identifier,result)
        from .language import Statement
        definition=render((Statement('FLOW','iteration',body=node.body),)).encode()
        child_id='call-'+sha256(encode((self.identity,identifier,frame['epoch']))).hexdigest()[:48]
        call=CallSpec(child_id,'attempt-'+child_id[5:],'result','FLOW',self.kernel.log.put_artifact(definition),
            self.kernel.log.put_artifact(encode(inputs)),ResultContract('ProgramResult','record'))
        self.kernel.spawn(identifier,expected_epoch=frame['epoch'],calls=(call,),next_pc=frame['pc']+1)
        return Step('admitted',child_id)

    def _wait(self,frame):
        children=[c for c in self._children(frame) if c['parent_epoch']==frame['epoch']]
        if len(children)!=1:raise AdmissionError('sequential interpreter requires exactly one admitted child')
        child=children[0]
        if child['state']=='Closed':
            self.kernel.resume(frame['id'],frame['epoch']);return Step('resumed',frame['id'])
        contract=child['contract'][0]
        if contract=='ProgramResult':return self._scope(child['id'])
        if contract=='RepeatResult':return self._repeat(child['id'])
        if contract=='ParallelResult':return exploration_module.step_parallel(self,child['id'])
        if contract=='ModelOutput':
            if self.dispatcher is None or child['state']=='Ready':self._emit_progress('model_started')
            if _reference(self.kernel.log,child['definition'])==retry_module.retry_definition(self.adapter):
                report=retry_module.step_retry_model(self.kernel,self.adapter,child['id'],dispatcher=self.dispatcher)
            else:report=step_model(self.kernel,self.adapter,child['id'],dispatcher=self.dispatcher)
            if report.status!='waiting':self._emit_progress('model_step_returned')
            return Step('model_'+report.status,child['id'],report.value)
        if contract=='ToolOutcome':
            self._emit_progress('tool_started')
            # Presentation cannot change dispatch or settlement, including on
            # malformed records: the actual dispatcher remains authoritative.
            try:
                from .tool_progress import tool_start_event
                detail=tool_start_event(_reference(self.kernel.log,child['inputs']),self.registry.identity,self.registry.world)
                if detail is not None:self._emit_progress(detail)
            except Exception:pass
            value=dispatch_tool(self.kernel,self.registry,child['id'],dispatcher=self.dispatcher)
            if value is None:return Step('tool_waiting',child['id'])
            self._emit_progress('tool_returned')
            return Step('tool_returned',child['id'],value)
        if contract=='BindingResult':
            if self.adapter is not None and _reference(self.kernel.log,child['definition'])==feedback_definition(self.adapter):
                value=step_image_feedback(self.kernel,self.adapter,child['id'])
                return Step('image_uploaded',child['id'],value)
            if _reference(self.kernel.log,child['definition'])!=encode(('bw.binding.v1',self.identity)):raise AdmissionError('pure definition changed')
            value=decode(_reference(self.kernel.log,child['inputs']));_value(value['value'])
            self.kernel.finish(child['id'],dict(value=value['value']),provenance=tuple(Artifact(*a) for a in value['provenance']))
            return Step('binding_returned',child['id'])
        raise AdmissionError('unsupported admitted result contract')

    def step(self):
        root=self.kernel.frame('program');node,inputs=self._load(root)
        self._check_program(render((node,)),{k:_value(v) for k,v in inputs['bindings'].items()})
        return self._scope('program')

    def run(self,*,max_steps=1024,control=None):
        if self.dispatcher is None:return self._run_steps(max_steps=max_steps,control=control)
        self.dispatcher.admitting=True
        try:
            result=self._run_steps(max_steps=max_steps,control=control)
        except BaseException as original:
            try:self.dispatcher.drain()
            except BaseException as error:original.add_note('Other parallel work also needs reconciliation: '+str(error))
            raise
        self.dispatcher.drain()
        return result

    def _run_steps(self,*,max_steps=1024,control=None):
        if type(max_steps) is not int or not 0<max_steps<=1000000:raise AdmissionError('finite positive step budget required')
        if control is not None and not callable(control):raise AdmissionError('host control callback required')
        count=0
        while count<max_steps:
            # The host may stop admission at a settled step boundary. It cannot
            # rewrite a frozen call, invent a result or repeat an uncertain effect.
            if control is not None and control():return Step('interrupted','program')
            report=self.step()
            if self.dispatcher is not None and report.status in ('parallel_waiting','model_waiting','tool_waiting'):
                self.dispatcher.wait(.05)
                continue
            count+=1
            if report.frame=='program' and report.status=='complete':return report
            if report.status in ('model_budget_exhausted','thinking_ladder_exhausted'):return report
        return Step('step_budget_exhausted','program')
