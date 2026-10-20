import unittest, math
from decimal import Decimal
from reference.codec import encode, decode

VALUES=[None,True,False,0,1,-1,2**200,-2**200,0.0,-0.0,1.25,Decimal('1.2300'),Decimal('-0.00'),'', 'λ\u2028🚀', b'', b'\xff\x00',(),[],{},(1,'a',b'b'),{'b':[None,True],'a':Decimal('2.00')}]
class CodecTests(unittest.TestCase):
    def test_bool_int_encodings_distinct(self):self.assertNotEqual(encode(True),encode(1))
    def test_text_bytes_encodings_distinct(self):self.assertNotEqual(encode('abc'),encode(b'abc'))
    def test_tuple_list_encodings_distinct(self):self.assertNotEqual(encode(()),encode([]))
    def test_map_order_canonical(self):self.assertEqual(encode({'b':2,'a':1}),encode({'a':1,'b':2}))
    def test_absent_field_not_null(self):self.assertNotEqual(encode({}),encode({'x':None}))
    def test_float_negative_zero(self):self.assertNotEqual(encode(0.0),encode(-0.0))
    def test_decimal_scale_preserved(self):self.assertEqual(decode(encode(Decimal('1.2300'))).as_tuple(),Decimal('1.2300').as_tuple())
    def test_depth_bounded(self):
        value=0
        for _ in range(45):value=(value,)
        with self.assertRaises(ValueError):encode(value)
    def test_duplicate_keys_rejected(self):
        p=encode('x')+encode(1)+encode('x')+encode(2)
        with self.assertRaises(ValueError):decode(b'm'+str(len(p)).encode()+b':'+p)
    def test_truncation_all_nonempty_suffixes(self):
        p=encode({'nested':(1,2,'abc')})
        for i in range(len(p)):
            with self.subTest(cut=i), self.assertRaises(ValueError):decode(p[:i])
for i,value in enumerate(VALUES):
    def check(self,value=value):
        result=decode(encode(value))
        self.assertIs(type(result),type(value));self.assertEqual(result,value)
        self.assertEqual(encode(result),encode(value))
    setattr(CodecTests,f'test_roundtrip_{i:02}',check)
BAD=[b'',b'i2:01',b'i2:-0',b'u01:x',b'n1:x',b'b1:2',b'i1:1x',b'z0:',b'u1:\xff',b'm3:n0:',b'f3:nan']
for i,data in enumerate(BAD):
    def check(self,data=data):
        with self.assertRaises(ValueError):decode(data)
    setattr(CodecTests,f'test_bad_encoding_{i:02}',check)
for i,value in enumerate([math.nan,math.inf,-math.inf,Decimal('NaN'),{1:'bad'},object()]):
    def check(self,value=value):
        with self.assertRaises(ValueError):encode(value)
    setattr(CodecTests,f'test_bad_value_{i:02}',check)
