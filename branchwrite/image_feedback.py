"""Repeatable image cache fill on the one FrameKernel, never model execution.

Freeze bytes, endpoint, source head and namespace before send. After a lost
acknowledgment only this content-addressed upload may repeat. Native generation
keeps its separate original-intent/no-automatic-resend rules. A closed result
is read locally. No model transcript, native state or second image cache lives here.
"""
from hashlib import sha256
from pathlib import Path
import json
from .records import Artifact,encode,decode
from .kernel import CallSpec,ResultContract,TransitionError
from .cow_client import BranchHead,ReceiptError,_canonical,_image_metadata
from .model_inputs import model_content

def _head(source):return dict(name=source.name,revision=source.revision,tip=source.tip,root=source.root)
def feedback_definition(adapter):
    return encode(('bw.image-feedback.v1',adapter.identity,sha256(Path(__file__).read_bytes()).hexdigest()))

def image_feedback_call(kernel,adapter,*,identifier,source,image,text):
    if not isinstance(source,BranchHead) or not isinstance(image,Artifact):
        raise TransitionError('actual source and immutable image artifact required')
    model_content(text);_image_metadata(kernel.log.read_artifact(image))
    namespace=adapter.client.image_namespace(source)
    request=dict(schema=1,kind='bw.image-feedback',adapter=adapter.identity,
        endpoint_url=adapter.client.endpoint_url,endpoint_pin=adapter.client.endpoint_pin,
        source=_head(source),namespace_id=namespace,image=(image.sha256,image.size_bytes),text=text)
    return CallSpec(identifier,'attempt-'+identifier,'result','TRANSFORM',
        kernel.log.put_artifact(feedback_definition(adapter)),kernel.log.put_artifact(encode(request)),
        ResultContract('BindingResult','record'))

def _input(kernel,adapter,frame):
    if (frame['operation']!='TRANSFORM' or frame['contract']!=('BindingResult','record')
        or kernel.log.read_artifact(Artifact(*frame['definition']))!=feedback_definition(adapter)):
        raise TransitionError('not this image feedback definition')
    request=decode(kernel.log.read_artifact(Artifact(*frame['inputs'])))
    keys={'schema','kind','adapter','endpoint_url','endpoint_pin','source','namespace_id','image','text'}
    if (type(request) is not dict or set(request)!=keys or type(request['schema']) is not int
        or request['schema']!=1 or request['kind']!='bw.image-feedback' or request['adapter']!=adapter.identity
        or request['endpoint_url']!=adapter.client.endpoint_url or request['endpoint_pin']!=adapter.client.endpoint_pin):
        raise TransitionError('image feedback request identity changed')
    source=BranchHead.parse(request['source']);image=Artifact(*request['image'])
    model_content(request['text']);_image_metadata(kernel.log.read_artifact(image))
    return request,source,image

def _accepted(kernel,request,image,value):
    expected=('ModelInput',[dict(type='image',image_id=image.sha256),dict(type='text',text=request['text'])])
    if type(value) is not dict or set(value)!={'value','upload'} or value['value']!=expected:
        raise TransitionError('image feedback result differs from frozen input')
    ack=json.loads(kernel.log.read_artifact(Artifact(*value['upload'])))
    width,height,media=_image_metadata(kernel.log.read_artifact(image))
    if (type(ack) is not dict or ack.get('namespace_id')!=request['namespace_id']
        or ack.get('image_id')!=image.sha256 or type(ack.get('bytes')) is not int or ack['bytes']!=image.size_bytes
        or type(ack.get('width')) is not int or type(ack.get('height')) is not int
        or (ack['width'],ack['height'])!=(width,height) or ack.get('media_type')!=media
        or type(ack.get('expires_ns')) is not int or ack['expires_ns']<=0):
        raise ReceiptError('retained image acknowledgement differs from frozen bytes')
    return value

def step_image_feedback(kernel,adapter,identifier):
    frame=kernel.frame(identifier);request,source,image=_input(kernel,adapter,frame)
    if frame['state']=='Closed':
        return _accepted(kernel,request,image,decode(kernel.log.read_artifact(Artifact(*frame['result'])))[2])
    if frame['state'] not in ('Ready','Waiting'):
        raise TransitionError('image upload has an unsupported settlement state')
    if adapter.client.image_namespace(source)!=request['namespace_id']:
        raise ReceiptError('image feedback namespace changed')
    operation='bwimage-'+sha256(encode((frame['id'],frame['attempt'],frame['inputs']))).hexdigest()[:48]
    if frame['dispatch'] is None:
        kernel.dispatch(identifier,operation,Artifact(*frame['inputs']))
    elif frame['dispatch']!=(operation,frame['inputs']):
        raise TransitionError('image dispatch differs from its original intent')
    # Resuming an uncertain cache fill deliberately repeats these exact bytes.
    # It neither changes a branch nor evaluates/draws/consumes model tokens.
    uploaded=adapter.client.upload_image(request['namespace_id'],kernel.log.read_artifact(image))
    ack=kernel.log.put_artifact(_canonical(dict(uploaded.raw)))
    value=dict(value=('ModelInput',[dict(type='image',image_id=image.sha256),dict(type='text',text=request['text'])]),
        upload=(ack.sha256,ack.size_bytes))
    _accepted(kernel,request,image,value)
    kernel.record_result(identifier,operation,value,provenance=(image,ack),settled=True)
    return value
