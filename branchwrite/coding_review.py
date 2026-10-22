"""Review complete baseline-bound projects or legacy recorded file-tool edits.

This is read-only evidence, not publication authority. The last successful
command inventory guards against post-verification workspace drift.
"""
import difflib,hashlib,json,os,stat
from pathlib import Path
from .records import RuntimeLog,Artifact,decode
from .kernel import FrameKernel
from .coding_cli import read_launch
from .execution import Executor,Grant
from .tool_registry import ToolRegistry

def review_scope(log,kernel,root,state):
    """Resolve only a canonical, joined selection to its existing owned copy."""
    result=decode(log.read_artifact(Artifact(*root['result'])))[2]
    choices=[v[1] for v in result.get('bindings',{}).values() if v[0]=='Selection']
    if not choices:return Path(state)/'world',root
    if len(choices)!=1 or choices[0].get('verified') is not True:
        raise ValueError('One verified candidate selection required')
    selected=choices[0]['selected']
    if selected['world'] not in ('first','second'):raise ValueError('Unknown candidate world')
    branch=kernel.frame(selected['frame'])
    if branch['state']!='Closed' or branch['result']!=selected['result']:
        raise ValueError('Selected candidate result changed')
    original=decode(log.read_artifact(Artifact(*branch['result'])))[2]
    if (original.get('verified') is not True or original['scope']!=selected['scope']
            or original['world']!=selected['world'] or original['inventory']!=selected['inventory']):
        raise ValueError('Selection does not bind the original verified candidate')
    return Path(state)/'candidates'/selected['world'],kernel.frame(selected['scope'])

def inspect_changes(state):
    state=Path(state);launch=read_launch(state);config=launch['config']
    with RuntimeLog(state/'ledger',read_only=True) as log:
        kernel=FrameKernel(log);root=kernel.frame('program')
        if root['state']!='Closed':raise ValueError('review requires a completed run')
        if root['contract']!=('ProgramResult','record'):raise ValueError('coding program required')
        result=decode(log.read_artifact(Artifact(*root['result'])))[2]
        if result.get('verified') is not True:raise ValueError('review requires recorded successful verification')
        inputs=decode(log.read_artifact(Artifact(*root['inputs'])))
        digest=hashlib.sha256(json.dumps(config,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
        if inputs['bindings'].get('host-config-sha256')!=('Text',digest):
            raise ValueError('saved configuration differs from canonical run')
        # No executor creation, shell setup or tool execution. Only the existing
        # no-follow bounded file reader and shared inventory algorithm are used.
        world,scope=review_scope(log,kernel,root,state)
        ex=Executor(Path(config['source']),world,world/'workspace')
        registry=ToolRegistry(ex,Grant((),False))
        before_inventory=registry._inventory()
        outcomes=kernel.visible_results(scope,('ToolOutcome','record'))
        originals={};changes={};last_inventory=None
        permissions=Grant(**config['grant'])
        for frame,value in outcomes:
            plan=decode(log.read_artifact(Artifact(*frame['inputs'])))
            if type(plan) is not tuple or len(plan)!=8 or plan[0]!='bw.tool-plan.v2':
                raise ValueError('unsupported recorded tool plan')
            _,_,_,tool,args,preimages,inventory,_=plan
            if scope['id']!=root['id'] and plan[2]!=registry.world:continue
            if value.get('tool')!=tool:raise ValueError('recorded tool and plan disagree')
            if tool=='read_file' and value.get('disposition')=='read' and value.get('exit_code')==0:
                ref=Artifact(*value['stdout'])
                originals.setdefault((args['path'],ref.sha256),log.read_artifact(ref))
            if tool in ('run_shell','run_check','run_tests') and value.get('disposition')=='exited' and value.get('exit_code')==0:
                last_inventory=inventory
            if tool not in ('replace','replace_text_file','create_file','create_text_file','set_mode') or value.get('disposition')!='applied' or value.get('exit_code')!=0:
                continue
            path=args['path']
            permission='create_paths' if tool.startswith('create') else 'mode_paths' if tool=='set_mode' else 'edit_paths'
            if not permissions.permits_file(permission,path):raise ValueError('recorded edit exceeds saved file grant')
            if path not in changes:
                if len(preimages)!=1 or preimages[0][0]!=path:raise ValueError('edit has no exact preimage')
                _,old_sha,old_mode=preimages[0]
                old=b'' if old_sha is None else originals.get((path,old_sha))
                if old is None:raise ValueError('immutable original read is unavailable for '+ascii(path))
                changes[path]=(old,old_sha,old_mode)
        if last_inventory is None or before_inventory!=last_inventory:
            raise ValueError('workspace differs from the last successful command inventory')
        from .project_baseline import BINDING,parse_reference
        saved=inputs['bindings'].get(BINDING)
        if saved is not None:
            if type(saved) is not tuple or len(saved)!=2 or saved[0]!='Text':
                raise ValueError('invalid canonical project input binding')
            result=_full_review(log,registry,config,parse_reference(saved[1]),before_inventory)
            if registry._inventory()!=before_inventory:raise ValueError('workspace changed during review')
            return result
        rows=[]
        for path,(old,old_sha,old_mode) in sorted(changes.items()):
            new=ex._read_private_bytes(path)
            snapshot=registry._snapshot(path)
            try:
                diff=''.join(difflib.unified_diff(old.decode('utf8').splitlines(keepends=True),new.decode('utf8').splitlines(keepends=True),fromfile='before/'+path,tofile='after/'+path))
                binary=False
            except UnicodeError:diff=None;binary=True
            rows.append(dict(path=path,before_sha256=old_sha,after_sha256=hashlib.sha256(new).hexdigest(),
                             before_mode=old_mode,after_mode=snapshot[2],binary=binary,diff=diff,
                             before_bytes=len(old),after_bytes=len(new)))
        if registry._inventory()!=before_inventory:raise ValueError('workspace changed during review')
        return dict(schema=1,coverage='recorded-file-tools',recorded_verified=True,
                    complete_project_patch=False,current_inventory=before_inventory,changes=rows)


def _full_review(log,registry,config,baseline_ref,current_inventory):
    from .project_baseline import load,reference_text
    baseline=load(log,baseline_ref);ex=registry.executor
    files={};directories={}
    for directory,dirs,names,fd in os.fwalk(ex.workspace,follow_symlinks=False):
        relative=Path(directory).relative_to(ex.workspace)
        for name in dirs:
            info=os.stat(name,dir_fd=fd,follow_symlinks=False)
            if not stat.S_ISDIR(info.st_mode):raise ValueError('workspace directory link')
            directories[(relative/name).as_posix()]=stat.S_IMODE(info.st_mode)
        for name in names:
            path=(relative/name).as_posix()
            raw=ex._read_private_bytes(path);snapshot=registry._snapshot(path)
            if hashlib.sha256(raw).hexdigest()!=snapshot[1]:raise ValueError('workspace changed during read')
            files[path]=dict(bytes=raw,sha256=snapshot[1],mode=snapshot[2])
    grant=config['grant'];rows=[];permissions=Grant(**grant)
    for path in sorted(set(baseline['files'])|set(files)):
        old=baseline['files'].get(path);new=files.get(path)
        if new is None:raise ValueError('file deletion has no grant: '+ascii(path))
        if old==new:continue
        if old is None:
            if not permissions.permits_file('create_paths',path):raise ValueError('file creation exceeds grant: '+ascii(path))
            if new['mode']&0o111 and path not in grant.get('mode_paths',[]):raise ValueError('new executable mode requires a mode grant')
        else:
            if old['bytes']!=new['bytes'] and not permissions.permits_file('edit_paths',path):
                raise ValueError('file modification exceeds grant: '+ascii(path))
            if old['mode']!=new['mode']:
                if (path not in grant.get('mode_paths',[]) or
                    (old['mode']^new['mode'])&~grant.get('mode_mask',0)):
                    raise ValueError('file mode exceeds grant: '+ascii(path))
        before=b'' if old is None else old['bytes'];after=new['bytes']
        binary=bytes([0]) in before or bytes([0]) in after
        try:
            text_before=before.decode('utf8');text_after=after.decode('utf8')
            diff=None if binary else ''.join(difflib.unified_diff(text_before.splitlines(keepends=True),text_after.splitlines(keepends=True),fromfile='before/'+path,tofile='after/'+path))
        except UnicodeError:binary=True;diff=None
        rows.append(dict(path=path,before_sha256=None if old is None else old['sha256'],after_sha256=new['sha256'],
                         before_mode=None if old is None else old['mode'],after_mode=new['mode'],
                         before_bytes=len(before),after_bytes=len(after),binary=binary,diff=diff,
                         before_final_newline=before.endswith(bytes([10])),after_final_newline=after.endswith(bytes([10]))))
    permitted_files=[path for path in files if path not in baseline['files'] and permissions.permits_file('create_paths',path)]
    permitted_parents={parent.as_posix() for path in permitted_files+grant.get('create_paths',[]) for parent in Path(path).parents if str(parent)!='.'}
    for path,mode in baseline['directories'].items():
        if path not in directories:raise ValueError('directory deletion has no grant: '+ascii(path))
        if directories[path]!=mode:raise ValueError('directory mode has no grant: '+ascii(path))
    for path in directories.keys()-baseline['directories'].keys():
        if path not in permitted_parents:raise ValueError('directory creation exceeds grant: '+ascii(path))
    return dict(schema=1,coverage='complete-project',recorded_verified=True,complete_project_patch=True,
                baseline_reference=reference_text(baseline_ref),baseline_inventory=baseline['inventory'],
                current_inventory=current_inventory,changes=rows,
                created_directories=[dict(path=path,mode=directories[path]) for path in sorted(directories.keys()-baseline['directories'].keys())])


def command(state,*,as_json=False):
    import sys
    try:result=inspect_changes(state)
    except (OSError,ValueError,RuntimeError,KeyError) as exc:
        print('branchwrite: '+ascii(str(exc)),file=sys.stderr);return 2
    if as_json:print(json.dumps(result,sort_keys=True))
    else:
        print('Complete project patch: '+('YES' if result['complete_project_patch'] else 'NO (recorded file-tool edits only)'))
        print('Current workspace matches the last successful command inventory.')
        for row in result['changes']:
            print(ascii(row['path'])+': '+str(row['before_bytes'])+' -> '+str(row['after_bytes'])+' bytes')
            text=row['diff'] if row['diff'] is not None else '[binary file]'
            print(''.join(c if c.isprintable() or c in chr(10)+chr(9) else ascii(c)[1:-1] for c in text))
    return 0
