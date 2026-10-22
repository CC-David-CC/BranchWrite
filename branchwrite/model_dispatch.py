import re
"""One model FLOW on FrameKernel; no second agent loop or native history.

Every step issues at most one native request. Partial native receipts close only
that request, never the caller's ModelOutput slot. COW owns parser/RNG progress.
"""
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from .records import Artifact,encode,decode,MAX_BYTES
from .kernel import CallSpec,ResultContract,TransitionError
from .cow_client import (CowClient,BranchHead,FrameKey,COWSourceBinding,
    GenerationResult,OperationIndeterminate,ReceiptError,_canonical)
from .cow_actions import completed_thinking_text
from .model_inputs import model_content
from . import model_pause as pause_module
from . import thinking_ladder as ladder_module
from . import model_inputs as inputs_module
from . import kernel as kernel_module, cow_client as client_module, cow_actions as actions_module

class ModelContractError(TransitionError):pass
class ModelSourceChanged(ModelContractError):pass
class ModelBranchBusy(ModelContractError):pass
class ModelReconciliationRequired(RuntimeError):
    def __init__(self,operation_id):
        self.operation_id=operation_id
        super().__init__('original native request is unresolved; reconcile it without a new work ID')

@dataclass(frozen=True)
class FrozenModelCall:
    data:bytes
    @property
    def sha256(self):return sha256(self.data).hexdigest()

@dataclass(frozen=True)
class ModelStep:
    status:str
    frame:str
    native_operation:str|None=None
    value:dict|None=None

_PATHS={'answer':'/cow/text/answer','ask':'/cow/text/ask','append_user':'/cow/text/append-user','continue':'/cow/text/resume'}

def _positive(value,limit):
    if type(value) is not int or not 0<value<=limit:raise ModelContractError('invalid finite model budget')
    return value

def _head(head):return dict(name=head.name,revision=head.revision,tip=head.tip,root=head.root)

def _ref(value):return Artifact(*value)

class ModelAdapter:
    def __init__(self,client,*,run_id,model_contract_id,execution_profile_id,eos_tokens,grammar_mapping=None,model_pause=None,pause_notice=None):
        if not isinstance(client,CowClient) or not client.endpoint_pin:
            raise ModelContractError('existing COW client with host endpoint binding required')
        for value in [run_id,model_contract_id,execution_profile_id]:
            if type(value) is not str or not value or len(value)>256 or any(ord(c)<32 for c in value):
                raise ModelContractError('bounded host identity required')
        if type(eos_tokens) is not tuple or not 1<=len(eos_tokens)<=16 or any(type(t) is not int or t<0 for t in eos_tokens) or len(set(eos_tokens))!=len(eos_tokens):
            raise ModelContractError('actual pinned EOS tokens required')
        if model_pause is not None and not callable(model_pause):raise ModelContractError('Read-only model pause callback required')
        self._model_pause=model_pause;self._pause_notice=pause_notice or (lambda _:None)
        self.client=client;self.run_id=run_id;self.model_contract_id=model_contract_id
        self.execution_profile_id=execution_profile_id;self.eos_tokens=eos_tokens
        mapping={} if grammar_mapping is None else grammar_mapping
        if (type(mapping) is not dict or len(mapping)>64
                or any(type(k) is not str or not k or len(k)>128
                    or type(v) is not str or not re.fullmatch(r'g[0-9a-f]{64}_s[0-9]+',v)
                    for k,v in mapping.items())
                or len(set(mapping.values()))!=len(mapping)):
            raise ModelContractError('exact registered grammar mapping required')
        self._grammar_mapping=encode(mapping)
        sources=tuple(sha256(Path(m).read_bytes()).hexdigest() for m in [__file__,kernel_module.__file__,client_module.__file__,actions_module.__file__,inputs_module.__file__,ladder_module.__file__,pause_module.__file__])
        self.identity=sha256(encode(('bw.model-adapter.v1',run_id,client.endpoint_url,client.endpoint_pin,model_contract_id,execution_profile_id,eos_tokens,sources))).hexdigest()
        if mapping:self.identity=sha256(encode(('bw.registered-model-adapter.v1',self.identity,self._grammar_mapping))).hexdigest()
        self.definition=encode(('bw.model-flow.v1',self.identity))

    def freeze(self,source,*,mode,content=None,settings=None,grammar_state=None,output_format='text',
               request_tokens=1536,max_requests=8,max_output_tokens=12288,max_result_bytes=262144,planning=None):
        if not isinstance(source,BranchHead):raise ModelContractError('observed source head required')
        BranchHead.parse(_head(source))
        if mode not in ('answer','ask','append_user'):raise ModelContractError('initial mode must name the actual COW boundary')
        if mode=='answer' and content is not None:raise ModelContractError('answer cannot append hidden content')
        if mode!='answer':
            try:content=model_content(content)
            except ValueError as exc:raise ModelContractError('invalid explicit model input: '+str(exc)) from exc
        if output_format not in ('text','constrained','thinking'):raise ModelContractError('unsupported output format')
        if output_format=='text':
            if grammar_state is not None:raise ModelContractError('select constrained format for named grammar')
        elif type(grammar_state) is not str or not grammar_state or len(grammar_state)>128:
            raise ModelContractError('constrained/thinking output requires an explicit named startup grammar')
        mapping=decode(self._grammar_mapping)
        if grammar_state is not None and mapping:
            if grammar_state in mapping:grammar_state=mapping[grammar_state]
            elif grammar_state not in mapping.values():
                raise ModelContractError('grammar state is outside admitted registration')
        if settings is not None and type(settings) is not dict:raise ModelContractError('settings must be an explicit native mapping')
        settings=None if settings is None else json.loads(_canonical(settings))
        config=dict(mode=mode,content=content,settings=settings,grammar_state=grammar_state,output_format=output_format,
            request_tokens=_positive(request_tokens,65536),max_requests=_positive(max_requests,64),
            max_output_tokens=_positive(max_output_tokens,1048576),max_result_bytes=_positive(max_result_bytes,1048576))
        value=dict(schema=1,kind='bw.model-call',adapter=self.identity,source=_head(source),config=config)
        if planning is not None:
            try:planning=ladder_module.planning_context(planning)
            except ValueError as exc:raise ModelContractError('invalid host thinking context') from exc
            expected=ladder_module.ladder(planning['mode'])[planning['rung']].grammar_state
            expected=mapping.get(expected,expected)
            if output_format!='thinking' or grammar_state!=expected:
                raise ModelContractError('thinking context requires its exact named budget grammar')
            value['planning']=planning
        return FrozenModelCall(encode(value))

    def plan(self,plan):
        if not isinstance(plan,FrozenModelCall):raise ModelContractError('frozen model call required')
        value=decode(plan.data)
        try:
            source=BranchHead.parse(value['source'])
            if self.freeze(source,planning=value.get('planning'),**value['config']).data!=plan.data:raise ModelContractError('model call identity or schema changed')
        except (KeyError,TypeError,ValueError) as exc:raise ModelContractError('invalid/incompatible model call') from exc
        return value

    def native_definition(self,operation):return encode(('bw.cow-native.v1',self.identity,operation))

    def native(self,frame,plan,index,source,used):
        config=plan['config'];limit=min(config['request_tokens'],config['max_output_tokens']-used)
        seed=sha256(encode(('bw.native-call.v1',self.identity,frame['id'],frame['attempt'],frame['inputs'],index))).hexdigest()[:48]
        identifier='native-'+seed;operation_id='bwnative-'+seed
        mode=config['mode'] if index==0 else 'continue';operation='EXPAND' if index==0 else 'CONTINUE'
        key=FrameKey(self.run_id,frame['id'],frame['id'],frame['attempt'],identifier,'native',index+1,operation_id,source['name'])
        body=self.client._generation_body(source['name'],source['revision'],operation_id,limit,config['settings'],config['grammar_state'])
        if index==0 and mode!='answer':body['content']=config['content']
        request=dict(schema=1,kind='bw.model-native-request',adapter=self.identity,model_frame=frame['id'],index=index,
            endpoint_url=self.client.endpoint_url,source=source,mode=mode,path=_PATHS[mode],body=_canonical(body),frame_key=key.to_json())
        return identifier,operation,request

    def check_journal(self,request):
        key=request['frame_key'];record=self.client.journal.read(key['operation_id'])
        if record is None:return
        expected=request['source']
        binding=record.get('source_binding')
        if (record.get('endpoint_url')!=self.client.endpoint_url or record.get('endpoint_pin')!=self.client.endpoint_pin
                or record.get('path')!=request['path'] or record.get('frame_key')!=key
                or self.client.journal.decode_body(record)!=request['body']
                or binding!=COWSourceBinding(key['operation_id'],expected['name'],expected['name'],expected['revision'],expected['tip'],self.client.endpoint_pin).to_json()):
            raise ModelContractError('native journal does not bind this exact frame/request/source')

    def validate_response(self,request,payload):
        key=request['frame_key'];source=request['source'];body=json.loads(request['body'])
        if type(payload) is not dict or set(payload)!={'operation_id','receipt','answer','source_binding'}:
            raise ModelContractError('invalid retained native response')
        if payload['operation_id']!=key['operation_id']:raise ModelContractError('wrong native operation owner')
        receipt=self.client._receipt(payload['receipt'],operation_id=key['operation_id'],expected_branch=source['name'],expected_revision=source['revision']+1)
        if receipt.branch.root!=source['root']:raise ModelContractError('native result changed canonical root')
        if (receipt.raw.get('model_contract_id')!=self.model_contract_id
                or receipt.raw.get('execution_profile_id')!=self.execution_profile_id):raise ModelContractError('native model/execution profile differs')
        expected=COWSourceBinding(key['operation_id'],source['name'],source['name'],source['revision'],source['tip'],self.client.endpoint_pin)
        if payload['source_binding']!=expected.to_json():raise ModelContractError('native result has a different source')
        answer=payload['answer'];self.client._check_answer_binding(request['path'],answer,receipt.snapshot)
        tokens=answer.get('tokens')
        if (type(tokens) is not list or not 0<len(tokens)<=body['max_tokens']
                or any(type(t) is not int or t<0 for t in tokens) or any(t in self.eos_tokens for t in tokens[:-1])):
            raise ModelContractError('invalid consumed-token result or request budget')
        return GenerationResult(key['operation_id'],receipt,(),answer,'kernel-artifact',expected)

    def execute(self,request):
        body=json.loads(request['body']);key=FrameKey.from_json(request['frame_key']);mode=request['mode']
        options=dict(settings=body.get('settings'),grammar_state=body.get('grammar_state'),frame_key=key)
        args=[body['branch'],body['revision'],body['operation_id']]
        if mode in ('ask','append_user'):args.append(body['content'])
        args.append(body['max_tokens'])
        method={'answer':self.client.answer,'ask':self.client.ask,'append_user':self.client.append_user,'continue':self.client.continue_}[mode]
        with pause_module.PauseWatcher(key.operation_id,self._model_pause,
                self.client.pause_generation,self._pause_notice):
            return method(*args,**options)


def model_call(kernel,adapter,*,child_id,attempt_id,slot,plan):
    adapter.plan(plan)
    return CallSpec(child_id,attempt_id,slot,'FLOW',kernel.log.put_artifact(adapter.definition),
                    kernel.log.put_artifact(plan.data),ResultContract('ModelOutput','record'))

def admit_model(kernel,adapter,parent,*,expected_epoch,child_id,attempt_id,slot,next_pc,plan):
    call=model_call(kernel,adapter,child_id=child_id,attempt_id=attempt_id,slot=slot,plan=plan)
    return kernel.spawn(parent,expected_epoch=expected_epoch,calls=(call,),next_pc=next_pc)

def _flow(kernel,adapter,identifier):
    frame=kernel.frame(identifier)
    if (frame['operation']!='FLOW' or frame['contract']!=('ModelOutput','record')
            or kernel.log.read_artifact(_ref(frame['definition']))!=adapter.definition):raise ModelContractError('not this registered model FLOW')
    plan=adapter.plan(FrozenModelCall(kernel.log.read_artifact(_ref(frame['inputs']))))
    return frame,plan

def _prior(kernel,adapter,frame,plan,epochs):
    values=[];source=plan['source'];used=0
    for index in range(epochs):
        child,operation,request=adapter.native(frame,plan,index,source,used)
        value=kernel.slot_value(frame['id'],index+1,'native')
        if (type(value) is not dict or set(value)!={'schema','model_frame','operation_id','request_sha256','response'}
                or type(value['schema']) is not int or value['schema']!=1 or value['model_frame']!=frame['id']
                or value['operation_id']!=request['frame_key']['operation_id']
                or value['request_sha256']!=sha256(encode(request)).hexdigest()):raise ModelContractError('native return has a different frame/request')
        native=kernel.frame(child)
        if (native['operation']!=operation or native['state']!='Closed'
                or native['inputs'][0]!=value['request_sha256']
                or kernel.log.read_artifact(_ref(native['definition']))!=adapter.native_definition(operation)):
            raise ModelContractError('native child/definition does not match frozen call')
        payload=json.loads(kernel.log.read_artifact(_ref(value['response'])))
        result=adapter.validate_response(request,payload);values.append((value,result));source=_head(result.receipt.branch);used+=len(result.answer['tokens'])
    return values,source,used

def _finish_or_partial(kernel,adapter,frame,plan,values):
    result=values[-1][1];config=plan['config'];answer=result.answer;tokens=answer['tokens'];complete=tokens[-1] in adapter.eos_tokens
    text=None
    if config['output_format']!='thinking':
        text=''.join(r.answer['text'] for _,r in values)
        if len(text.encode('utf8'))>config['max_result_bytes']:
            raise ModelContractError('model output exceeded its frozen byte budget; no further request')
    if not complete:
        if answer.get('stopped') is True or (isinstance(answer.get('thinking'),dict) and answer['thinking'].get('complete') is True):
            raise ModelContractError('stopped/malformed output without consumed EOS; no hidden repair')
        return ModelStep('partial',frame['id'],result.operation_id)
    if answer.get('stopped') is False:raise ModelContractError('EOS result contradicts active flag')
    if config['grammar_state'] is not None and answer.get('grammar_complete') is not True:
        raise ModelContractError('named grammar did not report complete')
    if config['output_format']=='thinking':
        try:text=completed_thinking_text(result,adapter.eos_tokens)
        except ValueError as exc:raise ModelContractError('no complete receipt-bound thinking final') from exc
    if len(text.encode('utf8'))>config['max_result_bytes']:raise ModelContractError('complete model value exceeds the frozen byte budget')
    value=dict(schema=1,model_frame=frame['id'],plan_sha256=frame['inputs'][0],output_format=config['output_format'],text=text,
        native_receipt=dict(result.receipt.raw),source_snapshot=plan['source']['tip'],
        consumed_output_tokens=sum(len(r.answer['tokens']) for _,r in values),request_count=len(values),
        responses=tuple(v['response'] for v,_ in values))
    kernel.finish(frame['id'],value,provenance=tuple(_ref(v['response']) for v,_ in values))
    return ModelStep('complete',frame['id'],result.operation_id,value)

def _branch_free(kernel,adapter,branch,*,owner,exclude=None):
    # A settled request releases GPU execution, not its open logical turn.
    # Derive branch ownership from the first admitted native child and its
    # still-open ModelOutput parent; do not create another lease/state ledger.
    frames=kernel.frames();by_id={f['id']:f for f in frames}
    for frame in frames:
        if frame['contract']!=('COWNativeReceipt','record'):continue
        parent=by_id.get(frame['parent'])
        logical_owner=(parent is not None and parent['id']!=owner
            and parent['contract']==('ModelOutput','record') and parent['state']!='Closed')
        pending=(frame['id']!=exclude and frame['state']!='Closed' and frame['dispatch'] is not None)
        if not logical_owner and not pending:continue
        ref=frame['inputs'] if logical_owner else frame['dispatch'][1]
        request=decode(kernel.log.read_artifact(_ref(ref)))
        if type(request) is not dict or request.get('kind')!='bw.model-native-request':raise ModelContractError('malformed admitted native intent')
        if request['endpoint_url']==adapter.client.endpoint_url and request['source']['name']==branch:
            raise ModelBranchBusy('another unresolved model FLOW/request owns this branch')

def step_model(kernel,adapter,identifier,*,dispatcher=None):
    """Owner-thread step. Never poll/resend uncertain work or close a partial FLOW."""
    frame,plan=_flow(kernel,adapter,identifier)
    if frame['state']=='Closed':
        value=decode(kernel.log.read_artifact(_ref(frame['result'])))[2]
        return ModelStep('complete',identifier,value=value)
    if frame['state'] not in ('Ready','Waiting'):raise ModelContractError('model FLOW has an unsupported settlement state')
    done=frame['epoch'] if frame['state']=='Ready' else frame['epoch']-1
    values,source,used=_prior(kernel,adapter,frame,plan,done)
    if frame['state']=='Ready' and values:
        # Revalidate even a previously rejected partial before spending more
        # budget. A saved bad view must not turn into a hidden repair on retry.
        report=_finish_or_partial(kernel,adapter,frame,plan,values)
        if report.status=='complete':return report
    if frame['state']=='Ready':
        config=plan['config']
        if done>=config['max_requests'] or used>=config['max_output_tokens']:return ModelStep('budget_exhausted',identifier)
        _branch_free(kernel,adapter,source['name'],owner=identifier)
        if _head(adapter.client.head(source['name']))!=source:raise ModelSourceChanged('source head changed; do not rebase/replay implicitly')
        child_id,operation,request=adapter.native(frame,plan,done,source,used)
        inputs=kernel.log.put_artifact(encode(request));definition=kernel.log.put_artifact(adapter.native_definition(operation))
        kernel.spawn(identifier,expected_epoch=done,calls=(CallSpec(child_id,'attempt-'+child_id[7:],'native',operation,definition,inputs,ResultContract('COWNativeReceipt','record')),),next_pc=done+1)
        frame=kernel.frame(identifier)
    else:child_id,operation,request=adapter.native(frame,plan,done,source,used)
    child=kernel.frame(child_id);expected=encode(request)
    if (child['operation']!=operation or kernel.log.read_artifact(_ref(child['inputs']))!=expected
            or kernel.log.read_artifact(_ref(child['definition']))!=adapter.native_definition(operation)):
        raise ModelContractError('pending native child differs from frozen operation')
    if child['state']!='Closed':
        _branch_free(kernel,adapter,source['name'],owner=identifier,exclude=child_id);adapter.check_journal(request)
        if child['dispatch'] is None:
            if _head(adapter.client.head(source['name']))!=source:raise ModelSourceChanged('source changed before native send')
            if dispatcher is not None and not dispatcher.available:
                return ModelStep('waiting',identifier)
            kernel.dispatch(child_id,request['frame_key']['operation_id'],_ref(child['inputs']))
            if dispatcher is None:result=adapter.execute(request)
            else:
                dispatcher.submit(request['frame_key']['operation_id'],lambda:adapter.execute(request),
                    collect=lambda:step_model(kernel,adapter,identifier,dispatcher=dispatcher))
                return ModelStep('waiting',identifier,request['frame_key']['operation_id'])
        elif dispatcher is not None and dispatcher.contains(request['frame_key']['operation_id']):
            if not dispatcher.ready(request['frame_key']['operation_id']):
                return ModelStep('waiting',identifier,request['frame_key']['operation_id'])
            result=dispatcher.take(request['frame_key']['operation_id'])
        else:
            try:result=adapter.client.read_completed_generation(request['frame_key']['operation_id'])
            except (OperationIndeterminate,ReceiptError) as exc:raise ModelReconciliationRequired(request['frame_key']['operation_id']) from exc
        adapter.check_journal(request)
        payload=dict(operation_id=result.operation_id,receipt=dict(result.receipt.raw),answer=dict(result.answer),source_binding=None if result.source_binding is None else result.source_binding.to_json())
        adapter.validate_response(request,payload)
        raw=_canonical(payload)
        if len(raw)>MAX_BYTES:raise ModelContractError('native response exceeds artifact budget')
        ref=kernel.log.put_artifact(raw)
        value=dict(schema=1,model_frame=identifier,operation_id=result.operation_id,request_sha256=child['inputs'][0],response=(ref.sha256,ref.size_bytes))
        kernel.record_result(child_id,result.operation_id,value,provenance=(ref,),settled=True)
    kernel.resume(identifier,frame['epoch'])
    frame=kernel.frame(identifier);values,_,_=_prior(kernel,adapter,frame,plan,frame['epoch'])
    return _finish_or_partial(kernel,adapter,frame,plan,values)
