"""Discovery checks precede workflow mutations and preserve old COW connections."""
import copy
from types import SimpleNamespace
import unittest
from branchwrite.capabilities import observe, CapabilityError
from branchwrite.cow_client import RequestRejected


def report():
    return dict(schema=1,service='context-cow',model_contract_id='a'*64,
        execution_profile_id='b'*64,workers=[],limits={},scheduling='fifo',
        features={name:dict(supported=True,enabled=True,qualification='startup-checked')
                  for name in ('text','inline_grammars','branches','controllers')})


class Transport:
    def __init__(self,value=None,code=None):
        self.value=report() if value is None else value
        self.code=code;self.calls=[]
    def request(self,method,path):
        self.calls.append((method,path))
        if self.code is not None:
            error=RequestRejected('HTTP test rejection')
            error.status_code=self.code
            raise error
        return SimpleNamespace(json_value=copy.deepcopy(self.value))


class CapabilityTests(unittest.TestCase):
    def check(self,transport,**kwargs):
        return observe(transport,model_contract_id='a'*64,execution_profile_id='b'*64,**kwargs)

    def test_checked_observation_is_read_only_and_bound_to_the_pinned_profile(self):
        transport=Transport()
        result=self.check(transport)
        self.assertEqual(result['execution_profile_id'],'b'*64)
        self.assertEqual(transport.calls,[('GET','/cow/capabilities')])
        for key in ('model_contract_id','execution_profile_id'):
            value=report();value[key]='c'*64
            with self.subTest(key=key),self.assertRaises(CapabilityError):self.check(Transport(value))

    def test_disabled_and_malformed_capabilities_fail_before_any_post(self):
        for change in ({'enabled':False},{'supported':False},{'enabled':1}):
            value=report();value['features']['text'].update(change)
            transport=Transport(value)
            with self.subTest(change=change),self.assertRaises(CapabilityError):self.check(transport)
            self.assertEqual(transport.calls,[('GET','/cow/capabilities')])

    def test_only_404_uses_validated_legacy_info_and_never_grants_new_features(self):
        info=dict(schema=1,service='context-cow',model_contract_id='a'*64,
            execution_profile_id='b'*64,eos_tokens=[1],capabilities=dict(text=True,inline_grammars=True))
        legacy=self.check(Transport(code=404),legacy_info=info)
        self.assertEqual(legacy['schema'],0)
        with self.assertRaises(CapabilityError):
            self.check(Transport(code=404),legacy_info=info,required=('peer_transfer',))
        for code in (401,403,409,503):
            with self.subTest(code=code),self.assertRaises(RequestRejected):
                self.check(Transport(code=code),legacy_info=info)


if __name__=='__main__':unittest.main()
