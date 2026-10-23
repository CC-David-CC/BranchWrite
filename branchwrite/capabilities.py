"""Read-only COW capability negotiation; never a second workflow authority."""
import json
import re


class CapabilityError(ValueError):
    pass


def _identity(value, model_contract_id, execution_profile_id):
    if type(value) is not dict or value.get('service') != 'context-cow':
        raise CapabilityError('COW capability service is invalid')
    for key, expected in (('model_contract_id',model_contract_id),('execution_profile_id',execution_profile_id)):
        if (type(value.get(key)) is not str or not re.fullmatch('[0-9a-f]{64}',value[key])
                or value[key] != expected):
            raise CapabilityError('COW capability differs from pinned '+key)


def validate(value, *, model_contract_id, execution_profile_id, required=('text','inline_grammars')):
    _identity(value,model_contract_id,execution_profile_id)
    if (type(value.get('schema')) is not int or value['schema'] != 1
            or set(value) != {'schema','service','model_contract_id','execution_profile_id',
                             'workers','features','limits','scheduling'}):
        raise CapabilityError('Unsupported COW capability schema')
    if (type(value['workers']) is not list or len(value['workers']) > 256
            or type(value['features']) is not dict or len(value['features']) > 128
            or type(value['limits']) is not dict or len(value['limits']) > 32
            or type(value['scheduling']) is not str):
        raise CapabilityError('COW capability report exceeds supported bounds')
    for name, feature in value['features'].items():
        if (type(name) is not str or not re.fullmatch('[a-z][a-z0-9_]{0,63}',name)
                or type(feature) is not dict or set(feature) != {'supported','enabled','qualification'}
                or type(feature['supported']) is not bool or type(feature['enabled']) is not bool
                or (feature['enabled'] and not feature['supported'])
                or feature['qualification'] not in ('startup-checked','experimental','qualified','unsupported')):
            raise CapabilityError('Invalid COW feature declaration: '+str(name))
    for worker in value['workers']:
        if (type(worker) is not dict or set(worker) != {'worker','health','model_contract_id','execution_profile_id','native'}
                or worker['model_contract_id'] != model_contract_id
                or worker['execution_profile_id'] != execution_profile_id):
            raise CapabilityError('Worker capability is not bound to the selected model/profile')
        if worker['native'] is not None:
            native=worker['native']
            if (type(native) is not dict or native.get('model_contract_id') != model_contract_id
                    or native.get('execution_profile_id') != execution_profile_id):
                raise CapabilityError('Native worker capability identity differs')
    for name in required:
        if not value['features'].get(name,{}).get('enabled',False):
            raise CapabilityError('COW capability is unavailable or disabled: '+name)
    return json.loads(json.dumps(value,allow_nan=False))


def observe(transport, *, model_contract_id, execution_profile_id,
            required=('text','inline_grammars'), legacy_info=None):
    from .cow_client import RequestRejected
    try:
        value=transport.request('GET','/cow/capabilities').json_value
    except RequestRejected as error:
        if getattr(error,'status_code',None) != 404:raise
        info=(legacy_info if legacy_info is not None
              else transport.request('GET','/cow/info').json_value)
        _identity(info,model_contract_id,execution_profile_id)
        if (type(info.get('schema')) is not int or info['schema'] != 1
                or type(info.get('capabilities')) is not dict):
            raise CapabilityError('Unsupported legacy COW discovery')
        for name in required:
            if name not in ('text','inline_grammars') or info['capabilities'].get(name) is not True:
                raise CapabilityError('Legacy COW does not advertise '+name)
        return dict(schema=0,service='context-cow',model_contract_id=model_contract_id,
            execution_profile_id=execution_profile_id,features={name:dict(
                supported=info['capabilities'].get(name) is True,
                enabled=info['capabilities'].get(name) is True,qualification='legacy')
                for name in ('text','inline_grammars')})
    return validate(value,model_contract_id=model_contract_id,
        execution_profile_id=execution_profile_id,required=required)
