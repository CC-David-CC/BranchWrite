"""Actual domain execution cannot bypass current canonical PDF page evidence."""
import json,tempfile,unittest
from pathlib import Path
from branchwrite.execution import Executor,Grant
from branchwrite.tool_registry import ToolRegistry
from branchwrite.kernel import FrameKernel
from branchwrite.records import RuntimeLog
from branchwrite.interpreter import Interpreter,Value
from branchwrite.pdf_tools import PdfCapability
from branchwrite.cad_tools import CadCapability
from branchwrite.cad_execution import CadRuntime
from branchwrite.blender_tools import BlenderCapability
from branchwrite.blender_execution import BlenderRuntime
from test_pdf_execution import SOURCE as PDF
from test_cad_execution import RUNTIME,SOURCE as CAD
from test_cad_evaluation import LIBS
from test_cad_geometry import spec
from test_blender_execution import ROOT,SOURCE as SCENE

class DomainPdfCompletionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.pdf=PdfCapability();cls.cad=CadCapability(CadRuntime(RUNTIME,timeout=30,osmesa=LIBS),spec())
  cls.blender=BlenderCapability(BlenderRuntime(ROOT),Path('/home/dflanag3/spatial-artifacts/bw-blender-20261020/mcpvenv/bin/python'))
 def execute(self,family,all_pages,change_source=False,rebuild=False):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source=root/'source';source.mkdir();(source/'report.py').write_bytes(PDF)
   entry='model.py' if family=='cad' else 'scene.py';(source/entry).write_bytes(CAD if family=='cad' else SCENE)
   ex=Executor.create(source,root/'world',project_input=True)
   registry=ToolRegistry(ex,Grant((),False,project_files=True),pdf=self.pdf,**{family:getattr(self,family)})
   actions=[('build_pdf',dict(path='report.py',output='report.pdf'))]
   if all_pages:actions.append(('render_pdf',dict(path='report.pdf',page=2)))
   if change_source:
    actions.append(('read_file',dict(path='report.py')))
    changed=PDF.replace(b'Measurements',b'New Measurements')
    actions.append(('replace_text_file',dict(path='report.py',lines=changed.decode().splitlines(),line_ending='LF',final_newline=True)))
    if rebuild:
     actions.extend([('build_pdf',dict(path='report.py',output='report.pdf')),('render_pdf',dict(path='report.pdf',page=2))])
   actions.append(('inspect_cad' if family=='cad' else 'inspect_scene',dict(path=entry)))
   bindings={};program='FLOW domain-document\n'
   for i,(tool,args) in enumerate(actions):
    key='proposal'+str(i);bindings[key]=Value('ToolProposal',json.dumps(dict(tool=tool,arguments=args)))
    program+='PLAN plan'+str(i)+' from='+key+' against=world -> plan\nACT act'+str(i)+' plan=plan -> outcome\n'
   bindings['done']=Value('ToolProposal',json.dumps(dict(tool='finish',arguments=dict(answer='done'))))
   contract='cad-geometry-and-finish' if family=='cad' else 'blender-scene-and-finish'
   program+='PLAN final from=done against=world -> plan\nACT finish plan=plan -> outcome\nVERIFY check input=outcome contract='+contract+' -> verified\nEND\n'
   with RuntimeLog(root/'ledger') as log:
    kernel=FrameKernel(log);runtime=Interpreter(kernel,registry,verification=dict(schema=1,**{family:True}));runtime.start(program,bindings)
    result=runtime.run();outcomes=tuple(runtime._visible_tool_outcomes(kernel.frame('program')))
    self.assertEqual([v['tool'] for _,v in outcomes],[tool for tool,_ in actions]+['finish'],'every admitted fixture action must actually execute')
    self.assertEqual(ex._read_private_bytes('report.py'),PDF.replace(b'Measurements',b'New Measurements') if change_source else PDF)
    for _,value in outcomes:
     if value['tool']=='finish':
      self.assertIsNone(value['exit_code']);self.assertEqual(value['disposition'],'completion_requested')
     else:self.assertEqual(value['exit_code'],0,(value['tool'],value['disposition']))
    domain=next(v for _,v in reversed(outcomes) if v['tool'] in ('inspect_cad','inspect_scene'))
    self.assertEqual(domain['exit_code'],0,domain);self.assertIn(domain['disposition'],('cad_checked','scene_checked'))
    return result.value['verified']
 def test_cad_pass_cannot_hide_unrendered_pdf_page(self):self.assertFalse(self.execute('cad',False))
 def test_blender_pass_cannot_hide_unrendered_pdf_page(self):self.assertFalse(self.execute('blender',False))
 def test_cad_and_all_current_pdf_pages_can_pass(self):self.assertTrue(self.execute('cad',True))
 def test_blender_and_all_current_pdf_pages_can_pass(self):self.assertTrue(self.execute('blender',True))
 def test_current_cad_cannot_hide_a_stale_pdf_build(self):self.assertFalse(self.execute('cad',True,True))
 def test_current_blender_cannot_hide_a_stale_pdf_build(self):self.assertFalse(self.execute('blender',True,True))
 def test_cad_accepts_rebuilt_and_rerendered_pdf_after_edit(self):self.assertTrue(self.execute('cad',True,True,True))
 def test_blender_accepts_rebuilt_and_rerendered_pdf_after_edit(self):self.assertTrue(self.execute('blender',True,True,True))
