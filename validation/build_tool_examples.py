"""Build three host-authored, actually executed tool demonstrations.

These are teaching examples, not model-generated successes, not held-out workload
answers and not approved LoRA training pairs. No model or inference is needed.
"""
import hashlib,json,sys
from pathlib import Path
from branchwrite.execution import Executor,Grant
from branchwrite.tool_registry import ToolRegistry
from branchwrite.records import RuntimeLog,Artifact
from branchwrite.kernel import FrameKernel
from branchwrite.interpreter import Interpreter,Value

def build(destination,output):
    output.mkdir(mode=0o700,exist_ok=False)
    cases=[('limits.py','clamp', 'return min(low, min(high, value))','return max(low, min(high, value))',
        'Clamp a value between low and high; preserve the support functions.',
        'self.assertEqual(clamp(8, 2, 5), 5)\n  self.assertEqual(clamp(-1, 2, 5), 2)\n  self.assertEqual(clamp(3, 2, 5), 3)',
        'def clamp(value, low, high):\n    """Return the nearest value inside the inclusive limits."""\n    return min(low, min(high, value))\n'),
      ('labels.py','slug','return text.strip().lower().replace(" ", "_")','return text.strip().lower().replace(" ", "-")',
        'Slug separators must be hyphens, not underscores; preserve other behavior.',
        'self.assertEqual(slug("  HELLO World  "), "hello-world")\n  self.assertEqual(slug("Solo"), "solo")\n  self.assertEqual(slug(""), "")',
        'def slug(text):\n    """Normalize a short display label to a lowercase identifier."""\n    return text.strip().lower().replace(" ", "_")\n'),
      ('sequences.py','stable_unique','return sorted(set(values))','return list(dict.fromkeys(values))',
        'Remove duplicates but preserve the order of first appearance.',
        'self.assertEqual(stable_unique([3, 1, 3, 2]), [3, 1, 2])\n  self.assertEqual(stable_unique([]), [])\n  self.assertEqual(stable_unique(["z", "a", "z"]), ["z", "a"])',
        'def stable_unique(values):\n    """Keep the first occurrence of each hashable entry."""\n    return sorted(set(values))\n')]
    notes=['# Three worked BranchWrite tool examples\n\nThese examples are hypothetical tasks on different files. They were authored by the host and executed through the real registered tools to check them. They are demonstrations, not current work. In the real task, use only the files named by the live tool schema and the actual current read result. Do not copy example hashes or paths.\n\nA world hash identifies the owned workspace. A source_sha256 identifies exact file bytes. They are different identities. The host binds observation.source_sha256 from the latest actual observation of that same file. Do not put checksum fields in model tool proposals. Preserve the exact before text including spaces and newlines. A rejected plan does not change the file; retain the last valid read until current bytes change.\n\nEach example shows the full file to read, a small exact replacement, actual tests and a finish request. A finish request is not a test result. If tests fail, use their feedback and keep working. No shell, hidden tools, new permissions or modifications to tests are allowed. The same protocol works with different tasks and many support functions.\n']
    manifest=[]
    for index,(filename,function,before,after,task,assertions,target) in enumerate(cases,1):
        folder=output/('example-'+str(index));folder.mkdir(mode=0o700);source=folder/'source';source.mkdir(mode=0o700);(source/'tests').mkdir();(source/'tests/__init__.py').write_bytes(b'')
        # A realistic shared utility module. Tests exercise all these independent
        # helpers, so an overwrite of the whole file cannot fake the small fix.
        helpers=[]
        descriptions=[
          ('trim','value.strip()','Remove surrounding whitespace without changing interior characters.'),
          ('lower','value.lower()','Normalize case using the ordinary Python Unicode lowercase operation.'),
          ('upper','value.upper()','Return uppercase text; this helper must remain unchanged by a task.'),
          ('words','value.split()','Split on runs of whitespace and discard empty surrounding segments.'),
          ('lines','value.splitlines()','Separate logical lines while removing each line ending.'),
          ('length','len(value)','Count elements in a sequence without mutating or sorting its values.'),
          ('nonempty','bool(value)','Return whether the supplied sequence contains any elements.'),
          ('first','value[0] if value else None','Return the first element or None for an empty sequence.'),
          ('last','value[-1] if value else None','Return the final element or None for an empty sequence.'),
          ('copy_items','list(value)','Make a shallow list copy, preserving order and duplicate elements.'),
          ('reversed_items','list(reversed(value))','Make a reversed list without changing the input sequence.'),
          ('sorted_items','sorted(value)','Make a sorted copy for callers which explicitly request sorting.'),
          ('even_items','list(value[::2])','Select positions zero, two, four and so on in their original order.'),
          ('odd_items','list(value[1::2])','Select positions one, three, five and so on in their original order.'),
          ('as_tuple','tuple(value)','Return an immutable sequence of the supplied elements in order.'),
          ('as_text','str(value)','Produce the normal string representation without custom interpolation.'),
          ('total','sum(value)','Add numeric entries; the zero-length sequence has total zero.'),
          ('positive_items','[item for item in value if item > 0]','Retain only positive numbers in encounter order.'),
          ('negative_items','[item for item in value if item < 0]','Retain only negative numbers in encounter order.'),
          ('absolute_items','[abs(item) for item in value]','Take elementwise absolute values without reordering the sequence.'),
          ('nonzero_items','[item for item in value if item != 0]','Drop zero entries while retaining duplicate nonzero entries.'),
          ('enumerated_items','list(enumerate(value))','Attach each zero-based position to its original element.'),
          ('paired_items','list(zip(value[::2], value[1::2]))','Pair adjacent elements, omitting an unmatched final element.'),
          ('unique_count','len(set(value))','Count distinct hashable entries without promising an ordering.'),
          ('joined_words','" ".join(value)','Join an iterable of words with exactly one ASCII space.'),
          ('pipe_joined','"|".join(value)','Join text values with a literal vertical-bar separator.'),
          ('comma_joined','",".join(value)','Join text values with a literal comma separator.'),
          ('bracketed','"[" + str(value) + "]"','Add visible square brackets around a diagnostic value.'),
          ('prefixed','"item:" + str(value)','Add the stable diagnostic prefix used by this utility module.'),
          ('suffixed','str(value) + ":item"','Add a diagnostic suffix without modifying the original object.')]
        for name,expression,description in descriptions:
            helpers.append('def '+name+'(value):\n    """'+description+'\n\n    This is an independent shared helper. Preserve its public name, accepted\n    argument and return expression when repairing a different function below.\n    The test suite also exercises module import and unchanged support behavior.\n    """\n    return '+expression+'\n\n')
        original=('"""Small shared utilities; modify only the behavior requested by the task."""\n\n'+''.join(helpers)+target).encode()
        (source/filename).write_bytes(original)
        tests='import unittest\nfrom '+filename[:-3]+' import '+function+', trim, first, total, copy_items\nclass Behavior(unittest.TestCase):\n def test_requested_behavior(self):\n  '+assertions+'\n def test_preserved_helpers(self):\n  self.assertEqual(trim("  x  "), "x")\n  self.assertEqual(first([8, 4]), 8)\n  self.assertEqual(total([2, 3, 4]), 9)\n  self.assertEqual(copy_items([2, 1, 2]), [2, 1, 2])\n'
        (source/'tests/test_behavior.py').write_text(tests,newline='\n')
        executor=Executor.create(source,folder/'world');registry=ToolRegistry(executor,Grant((filename,),True,read_paths=(filename,)))
        proposals=[dict(tool='read_file',arguments=dict(path=filename)),dict(tool='replace',arguments=dict(path=filename,before=before,after=after)),dict(tool='run_tests',arguments=dict(suite='unit')),dict(tool='finish',arguments=dict(answer='Requested behavior is repaired and the registered tests pass.'))]
        body=[];bindings={}
        for step,proposal in enumerate(proposals):
            name='proposal'+str(step);bindings[name]=Value('ToolProposal',json.dumps(proposal))
            body.extend(['PLAN plan'+str(step)+' from='+name+' against=world -> frozen','ACT action'+str(step)+' plan=frozen -> outcome'+str(step)])
        body.append('VERIFY checked input=outcome3 contract=unit-tests-and-finish -> verified')
        program='FLOW example\n'+'\n'.join(body)+'\nEND\n'
        with RuntimeLog(folder/'ledger') as log:
            runtime=Interpreter(FrameKernel(log),registry);runtime.start(program,bindings);result=runtime.run(max_steps=128)
            assert result.value['verified'],result
            notes.append('\n## Worked example '+str(index)+': '+task+'\n\nUSER TASK: '+task+'\n')
            for step,proposal in enumerate(proposals):
                outcome=result.value['bindings']['outcome'+str(step)][1];observed=outcome['observation']
                feedback=dict(tool=outcome['tool'],disposition=outcome['disposition'],exit_code=outcome['exit_code'],observation=None if observed is None else dict(world=observed[0],path=observed[1],source_sha256=observed[2]),stdout=log.read_artifact(Artifact(*outcome['stdout'])).decode('utf8'),stderr=log.read_artifact(Artifact(*outcome['stderr'])).decode('utf8'))
                notes.append('\nASSISTANT EXAMPLE ACTION:\n'+json.dumps(proposal,ensure_ascii=True)+'\nHOST TOOL FEEDBACK:\n'+json.dumps(feedback,ensure_ascii=True)+'\n')
                if step==0:notes.append('\nDecision explanation: the read has returned real file bytes. The source_sha256 field above belongs to those bytes. The world field is not a file checksum. The entire module is present so an exact small edit can preserve every other helper. The host freezes the observed digest without making the model copy it. Select a before string which occurs exactly once. The response grammar constrains structure; it does not choose the right edit for you.\n')
                if step==1:notes.append('\nDecision explanation: this is a completed mutation, not a proposal. Read its disposition before assuming it happened. The new observation binds the edited bytes. The earlier checksum no longer describes the new file, so the host binds the latest visible observation for a later edit and rejects stale bytes. Now run the registered unit tests. Do not claim finish on the basis of a plausible-looking edit.\n')
                if step==2:notes.append('\nDecision explanation: the actual registered runner exited zero and ran a nonempty suite. The preserved-helper tests are important because only the requested behavior should change. If the exit code were nonzero, this would be a repair loop, not a finish. Read the failing assertion, read relevant granted files again when needed, propose an exact correction and rerun tests. Do not change the tests or invent passing output.\n')
            manifest.append(dict(example=index,filename=filename,source_sha256=hashlib.sha256(original).hexdigest(),verified=result.value['verified'],world=registry.world))
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(''.join(notes),encoding='utf8',newline='\n')
    (output/'result.json').write_text(json.dumps(dict(status='THREE_AUTHORED_EXAMPLES_EXECUTED',examples=manifest,document=str(destination),sha256=hashlib.sha256(destination.read_bytes()).hexdigest()),indent=2)+'\n')
    print(json.dumps(dict(path=str(destination),bytes=destination.stat().st_size,examples=3)))
if __name__=='__main__':build(Path(sys.argv[1]),Path(sys.argv[2]))
