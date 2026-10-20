"""Closed model input values, not another history or image cache.

Images are already-uploaded, namespace-authorized COW identities. No path, URL,
filename hint, role, token ID, embedding or executable enters model input here.
COW validates ownership/expiry and owns encoding, positions and native state.
Local file admission/upload and capture-to-image feedback are separate work.
"""
from copy import deepcopy
import json,re

def model_content(content):
    if type(content) is str:
        if len(content.encode('utf8'))>262144:raise ValueError('model input text exceeds byte bound')
        return content
    if type(content) is not list or not 2<=len(content)<=17:
        raise ValueError('model input requires ordered image/text parts')
    images=texts=0
    for part in content:
        if type(part) is not dict:raise ValueError('model input part must be a closed mapping')
        if part.get('type')=='image':
            if set(part)!={'type','image_id'} or type(part['image_id']) is not str or re.fullmatch('[0-9a-f]{64}',part['image_id']) is None:
                raise ValueError('image part requires an uploaded COW SHA256 identity')
            images+=1
        elif part.get('type')=='text':
            if set(part)!={'type','text'} or type(part['text']) is not str:raise ValueError('text part requires exact text')
            texts+=1
        else:raise ValueError('unsupported model input part type')
    if not 1<=images<=8 or not texts:raise ValueError('model input requires1..8 images and explicit question text')
    if len(json.dumps(content,ensure_ascii=False,separators=(',',':')).encode('utf8'))>262144:
        raise ValueError('model input parts exceed byte bound')
    return deepcopy(content)
