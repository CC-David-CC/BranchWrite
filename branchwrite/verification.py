"""Host-selected file completion; no model verdict or executable verifier plugin.

This bounded policy verifies expected file bytes plus a visible actual read. It
is not a semantic judge or a replacement for protected coding/browser checks.
"""
from dataclasses import dataclass
from hashlib import sha256
import re
from .execution import _relative_path,ToolRejected
from .records import Artifact,encode,decode

@dataclass(frozen=True)
class FileReadbackPolicy:
    files: tuple
    modes: tuple = ()

    @classmethod
    def admit(cls,spec,registry):
        if type(spec) is not dict or set(spec)!={'schema','files'} or type(spec['schema']) is not int or spec['schema']!=1:
            raise ValueError('closed file verification schema required')
        entries=spec['files']
        if type(entries) is not list or not 1<=len(entries)<=64:raise ValueError('one to64 file expectations required')
        files=[];modes=[]
        for item in entries:
            if type(item) is not dict or set(item) not in ({'path','sha256'},{'path','sha256','mode'}):raise ValueError('exact path,SHA256 and optional basic mode required')
            path=item['path'];digest=item['sha256']
            if type(path) is not str or _relative_path(path)!=path or path not in registry._grant.read_paths:
                raise ValueError('verification path must be explicitly readable in this world')
            if type(digest) is not str or re.fullmatch('[0-9a-f]{64}',digest) is None:raise ValueError('lowercase file SHA256 required')
            if 'mode' in item:
                mode=item['mode']
                if type(mode) is not str or re.fullmatch('0[0-7]{3}',mode) is None:
                    raise ValueError('four octal digits without special bits required')
                modes.append((path,mode))
            files.append((path,digest))
        if len({p for p,_ in files})!=len(files):raise ValueError('duplicate verification path')
        return cls(tuple(sorted(files)),tuple(sorted(modes)))

    @property
    def identity(self):
        # Existing byte-only policies keep their original identity and receipts.
        value=(('bw.file-readback-policy.v2',self.files,self.modes) if self.modes
               else ('bw.file-readback-policy.v1',self.files))
        return sha256(encode(value)).hexdigest()

    def verify(self,registry,log,outcomes):
        """Read receipts must be resumed predecessors, supplied by Interpreter.

        A create/replace observation is not readback. An unrelated root, unsettled
        child, stale hash or a model finish claim cannot provide this witness.
        Actual filesystem checks use the existing locked no-follow reader.
        """
        checked=[];mode_expectations=dict(self.modes)
        with registry.executor._lock:
            registry._world_check()
            for path,expected in self.files:
                snapshot=registry._snapshot(path);actual=snapshot[1]
                witness=None
                if actual==expected:
                    for frame,value in outcomes:
                        if (value['tool']=='read_file' and value['disposition']=='read' and value['exit_code']==0
                            and value['observation']==(registry.world,path,expected)):
                            body=log.read_artifact(Artifact(*value['stdout']))
                            if sha256(body).hexdigest()==expected:witness=frame['id']
                row=dict(path=path,expected_sha256=expected,actual_sha256=actual,read_frame=witness)
                if path in mode_expectations:
                    row.update(expected_mode=mode_expectations[path],
                        actual_mode=None if snapshot[2] is None else format(snapshot[2],'04o'))
                checked.append(row)
        passed=all(row['actual_sha256']==row['expected_sha256'] and row['read_frame'] is not None
            and ('expected_mode' not in row or row['actual_mode']==row['expected_mode']) for row in checked)
        return dict(status='pass' if passed else 'fail',policy='file-readback-and-finish',
            reason=(('current file bytes,permissions and visible read receipts matched' if passed else 'expected bytes,permissions or visible actual readback missing')
                    if self.modes else ('current file bytes and visible read receipts matched' if passed else 'expected bytes or visible actual readback missing')),
            policy_identity=self.identity,files=tuple(checked))


def _render_options(assets,path):
    options={}
    if assets:options['assets']=assets
    if path!='index.html':options['document_path']=path
    return options


def _current_asset_manifest(registry):
    return [a.manifest for a in registry.executor._browser_assets(registry._grant)]


def _same_assets(registry,manifest):
    try:return _current_asset_manifest(registry)==manifest
    except (ToolRejected,ValueError,OSError):return False


def _capture_bundle(registry,log,frame,value,path):
    """Bind all bytes to the admitted plan and existing artifact roots."""
    try:
        details=value['details']
        assets=registry.executor._browser_assets(registry._grant)
        manifest=[a.manifest for a in assets]
        if details.get('document_path')!=path or details.get('asset_manifest')!=manifest:
            return None
        served=details.get('served_assets')
        if type(served) is not list or any(row not in manifest for row in served):return None
        plan=decode(log.read_artifact(Artifact(*frame['inputs'])))
        if (type(plan) is not tuple or len(plan)!=8
                or plan[:4]!=('bw.tool-plan.v2',registry.identity,registry.world,value['tool'])
                or value['plan_sha256']!=frame['inputs'][0] or plan[4]['path']!=path
                or (plan[5],plan[6])!=registry._dependencies(value['tool'],plan[4])):
            return None
        registry._bound_arguments(value['tool'],plan[4])
        viewport_name=registry.executor._browser.name_for_size(*details['viewport'])
        if details.get('viewport_name')!=viewport_name or plan[4].get('viewport')!=viewport_name:return None
        for a in assets:
            # A receipt naming a digest is insufficient: exact bytes must be
            # durably rooted in the same canonical workflow artifact store.
            if log.read_artifact(Artifact(a.manifest['sha256'],len(a.body)))!=a.body:return None
        return dict(asset_manifest=manifest,served_assets=served,document_path=path,viewport_name=viewport_name)
    except (ToolRejected,KeyError,TypeError,ValueError,OSError):
        return None


@dataclass(frozen=True)
class PageCapturePolicy:
    files: FileReadbackPolicy
    captures: tuple

    @classmethod
    def admit(cls,spec,registry):
        if type(spec) is not dict or set(spec)!={'schema','files','captures'}:
            raise ValueError('closed page capture policy required')
        files=FileReadbackPolicy.admit(dict(schema=spec['schema'],files=spec['files']),registry)
        entries=spec['captures'];browser=registry.executor._browser
        if browser is None or type(entries) is not list or not 1<=len(entries)<=16:
            raise ValueError('host browser and one to16 captures required')
        expected=dict(files.files);captures=[]
        for item in entries:
            if type(item) is not dict or set(item)!={'path','width','height'}:raise ValueError('exact capture path and viewport required')
            path=item['path'];width=item['width'];height=item['height']
            if type(path) is not str or path not in expected or path not in registry._grant.capture_paths:
                raise ValueError('capture requires expected source bytes and explicit capture grant')
            try:browser.name_for_size(width,height)
            except ValueError as exc:raise ValueError('capture viewport differs from registered browser') from exc
            captures.append((path,width,height))
        if len(set(captures))!=len(captures):raise ValueError('duplicate capture path and viewport')
        return cls(files,tuple(sorted(captures)))

    @property
    def identity(self):return sha256(encode(('bw.page-capture-policy.v1',self.files.identity,self.captures))).hexdigest()

    def verify(self,registry,log,outcomes):
        import io
        from PIL import Image
        # Both policies examine the same current file state under one owner lock.
        with registry.executor._lock:
            result=self.files.verify(registry,log,outcomes);checked=[];expected=dict(self.files.files)
            for path,width,height in self.captures:
                witness=None
                for frame,value in outcomes:
                    if (value['tool']!='capture_page' or value['disposition']!='captured' or value['exit_code']!=0
                            or value['observation']!=(registry.world,path,expected[path]) or value['image'] is None):continue
                    details=value['details'];isolation=details.get('isolation',{})
                    if (details.get('runtime_errors') or details.get('served_sha256')!=expected[path] or details.get('viewport')!=(width,height)
                            or isolation.get('kind')!='bubblewrap-browser-v1' or isolation.get('chromium_sandbox') is not True
                            or isolation.get('worker_exited') is not True or isolation.get('namespace_members_after')!=[]):continue
                    bundle=_capture_bundle(registry,log,frame,value,path)
                    if bundle is None:continue
                    image=Artifact(*value['image']);body=log.read_artifact(image)
                    with Image.open(io.BytesIO(body)) as png:
                        png.load()
                        if png.format!='PNG' or png.size!=(width,height):continue
                    witness=dict(path=path,source_sha256=expected[path],image_sha256=image.sha256,image_bytes=image.size_bytes,
                        width=width,height=height,capture_frame=frame['id'],**bundle)
                checked.append(witness)
            passed=result['status']=='pass' and all(row is not None for row in checked)
            result.update(status='pass' if passed else 'fail',policy='page-capture-and-finish',policy_identity=self.identity,captures=tuple(checked),
                reason='current source, actual read and sandboxed PNG capture matched' if passed else 'expected source/read or completed matching capture missing')
            return result


def inspect_captured_page(source,browser,inspection,*,assets=(),document_path="index.html"):
    """Host-only check inside the existing browser sandbox, never a model tool."""
    from .browser_capture import BrowserConfig,render_snapshot
    return render_snapshot(source,BrowserConfig(browser.executable,browser.width,
        browser.height,browser.timeout,inspection=inspection),assets=assets,document_path=document_path)


@dataclass(frozen=True)
class InspectedPagePolicy:
    captures: tuple
    inspection: object

    @classmethod
    def admit(cls,spec,registry):
        from pathlib import Path
        from .browser_capture import PageInspection
        if type(spec) is not dict or set(spec)!={'schema','inspected_captures','inspection'}:
            raise ValueError('closed inspected-page policy required')
        descriptor=spec['inspection']
        if type(descriptor) is not dict or set(descriptor)!={'path','sha256','target'} or type(descriptor['path']) is not str:
            raise ValueError('host-selected checker path, digest and target required')
        path=Path(descriptor['path'])
        if not path.is_absolute() or path.is_symlink() or not path.is_file():
            raise ValueError('checker must be an existing absolute regular host file')
        path=path.resolve(strict=True)
        if any(path.is_relative_to(root.resolve()) for root in (registry.executor.source,registry.executor.workspace.parent)):
            raise ValueError('checker cannot belong to the candidate source or owned world')
        inspection=PageInspection(path,descriptor['sha256'],descriptor['target'])
        with path.open('rb') as stream:body=stream.read(1048577)
        if len(body)>1048576 or sha256(body).hexdigest()!=inspection.sha256:
            raise ValueError('host checker digest or byte bound differs')
        captures=spec['inspected_captures']
        # Reuse the supplied-page grant/viewport admission without knowing any
        # future candidate bytes. This does not relax its fixed-byte contract.
        if type(captures) is not list or not 1<=len(captures)<=16:
            raise ValueError('one to16 inspected capture paths required')
        if any(type(item) is not dict or set(item)!={'path','width','height'} for item in captures):
            raise ValueError('exact inspected capture paths and viewports required')
        binding=PageCapturePolicy.admit(dict(schema=spec['schema'],
            files=[dict(path=path,sha256='0'*64) for path in dict.fromkeys(item['path'] for item in captures)],captures=captures),registry)
        return cls(binding.captures,inspection)

    @property
    def identity(self):
        return sha256(encode(('bw.inspected-page-policy.v1',self.captures,
            str(self.inspection.path),self.inspection.sha256,self.inspection.target))).hexdigest()

    def verify(self,registry,log,outcomes):
        with registry.executor._lock:
            registry._world_check()
            expected=tuple((path,registry._snapshot(path)[1]) for path in dict.fromkeys(p for p,_,_ in self.captures))
            if any(digest is None for _,digest in expected):
                return dict(status='fail',policy='page-inspection-and-finish',policy_identity=self.identity,
                    reason='required current page is missing',captures=(),inspections=())
            # Require actual visible reads/captures of the current generated
            # bytes before a protected checker is allowed to execute.
            result=PageCapturePolicy(FileReadbackPolicy(expected),self.captures).verify(registry,log,outcomes)
            result.update(policy='page-inspection-and-finish',policy_identity=self.identity,inspections=())
            if result['status']!='pass':return result
            checked=[]
            for capture in result['captures']:
                path=capture['path'];source=registry.executor._read_private_bytes(path)
                assets=registry.executor._browser_assets(registry._grant)
                from .browser_capture import render_snapshot
                options=_render_options(assets,path)
                # Match the model's initial picture before an independent
                # checker changes UI state. Retain the checker's own image.
                browser=registry.executor._browser.at_size(capture['width'],capture['height'])
                replay=render_snapshot(source,browser,**options)
                rendered=inspect_captured_page(source,browser,self.inspection,**options)
                digest=sha256(replay.png).hexdigest();inspection=rendered.inspection or {}
                protected_image=log.put_artifact(rendered.png)
                same=(replay.png==log.read_artifact(Artifact(capture['image_sha256'],capture['image_bytes']))
                    and replay.served_sha256==rendered.served_sha256==capture['source_sha256']
                    and registry._snapshot(path)[1]==capture['source_sha256']
                    and list(replay.asset_manifest)==list(rendered.asset_manifest)==capture['asset_manifest']
                    and _settled_browser(replay.isolation)
                    and _same_assets(registry,capture['asset_manifest']))
                # Without checker actions the protected picture must still
                # match exactly; the original different-PNG negative remains.
                if not inspection.get('actions') and rendered.png!=replay.png:same=False
                isolation=rendered.isolation or {}
                settled=(isolation.get('kind')=='bubblewrap-browser-v1'
                    and isolation.get('chromium_sandbox') is True
                    and isolation.get('worker_exited') is True
                    and isolation.get('namespace_members_after')==[])
                passed=inspection.get('status')=='PASS' and same and settled
                checked.append(dict(path=path,width=capture['width'],height=capture['height'],viewport_name=capture['viewport_name'],status='PASS' if passed else 'FAIL',
                    image_sha256=digest,captured_image_sha256=capture['image_sha256'],
                    source_sha256=rendered.served_sha256,same_capture=same,
                    asset_manifest=list(rendered.asset_manifest),document_path=path,
                    protected_image=(protected_image.sha256,protected_image.size_bytes),
                    replay_isolation=replay.isolation,
                    inspector_sha256=self.inspection.sha256,target=self.inspection.target,
                    checker=inspection,isolation=rendered.isolation))
            passed=all(row['status']=='PASS' for row in checked)
            result.update(status='pass' if passed else 'fail',inspections=tuple(checked),
                reason='current readback, captured image and sandboxed protected checks matched' if passed
                    else 'protected page checks failed or checked rendering differs from current capture')
            return result


def _settled_browser(witness):
    return (type(witness) is dict and witness.get('kind') == 'bubblewrap-browser-v1'
        and witness.get('chromium_sandbox') is True and witness.get('worker_exited') is True
        and witness.get('namespace_members_after') == [])


def replay_interaction(payload, browser, actions, *, assets=(),document_path="index.html"):
    """Replay only the already recorded recipe in a fresh isolated context."""
    from dataclasses import replace
    from .browser_capture import page_action_recipe, render_snapshot
    return render_snapshot(payload, replace(browser, actions=page_action_recipe(actions)),assets=assets,document_path=document_path)


@dataclass(frozen=True)
class InteractivePagePolicy:
    """Same source/recipe pixels plus a separate protected behavioral check."""
    captures: tuple
    inspection: object

    @classmethod
    def admit(cls, spec, registry):
        if type(spec) is not dict or set(spec) != {'schema', 'interactive_captures', 'inspection'}:
            raise ValueError('closed interactive capture policy required')
        base = InspectedPagePolicy.admit(dict(schema=spec['schema'],
            inspected_captures=spec['interactive_captures'], inspection=spec['inspection']), registry)
        if any(path not in registry._grant.interact_paths for path, _, _ in base.captures):
            raise ValueError('interactive verification requires an explicit interaction grant')
        return cls(base.captures, base.inspection)

    @property
    def identity(self):
        return sha256(encode(('bw.interactive-page-policy.v1', self.captures,
            str(self.inspection.path), self.inspection.sha256, self.inspection.target))).hexdigest()

    def verify(self, registry, log, outcomes):
        import io
        from PIL import Image
        from .browser_capture import page_action_recipe
        with registry.executor._lock:
            registry._world_check()
            expected = tuple((path, registry._snapshot(path)[1]) for path in dict.fromkeys(p for p,_,_ in self.captures))
            result = FileReadbackPolicy(expected).verify(registry, log, outcomes)
            result.update(status='fail', policy='interactive-page-inspection-and-finish',
                policy_identity=self.identity, captures=(), inspections=())
            if any(digest is None for _, digest in expected) or any(row['read_frame'] is None for row in result['files']):
                result['reason'] = 'current source and actual readback required'
                return result
            chosen = []
            for path, width, height in self.captures:
                digest = dict(expected)[path];witness = None
                for frame, value in outcomes:
                    if (value['tool'] != 'interact_page' or value['disposition'] != 'captured'
                            or value['exit_code'] != 0 or value['image'] is None
                            or value['observation'] != (registry.world, path, digest)):
                        continue
                    details = value['details']
                    if (details.get('runtime_errors') or details.get('served_sha256') != digest or details.get('viewport') != (width, height)
                            or not _settled_browser(details.get('isolation'))):
                        continue
                    try:
                        actions = details['actions'];page_action_recipe(actions)
                    except (KeyError, ValueError, TypeError):
                        continue
                    plan = decode(log.read_artifact(Artifact(*frame['inputs'])))
                    expected_args=dict(path=path,source_sha256=digest,actions=actions)
                    if registry.executor._browser.viewports:
                        expected_args['viewport']=registry.executor._browser.name_for_size(width,height)
                    if (type(plan) is not tuple or len(plan) != 8
                            or plan[:4] != ('bw.tool-plan.v2', registry.identity, registry.world, 'interact_page')
                            or plan[4] != expected_args
                            or value['plan_sha256'] != frame['inputs'][0]
                            or log.read_artifact(Artifact(*value['stdout'])) != details.get('text', '').encode('utf8')):
                        continue
                    bundle=_capture_bundle(registry,log,frame,value,path)
                    if bundle is None:continue
                    image = Artifact(*value['image']);body = log.read_artifact(image)
                    with Image.open(io.BytesIO(body)) as png:
                        png.load()
                        if png.format != 'PNG' or png.size != (width, height):
                            continue
                    witness = dict(path=path, source_sha256=digest, image_sha256=image.sha256,
                        image_bytes=image.size_bytes, width=width, height=height,
                        capture_frame=frame['id'], actions=actions, text=details['text'],
                        plan_sha256=frame['inputs'][0],**bundle)
                if witness is None:
                    result['reason'] = 'current actual source-bound model interaction is missing'
                    return result
                chosen.append(witness)
            checked = []
            for capture in chosen:
                path = capture['path'];payload = registry.executor._read_private_bytes(path)
                assets=registry.executor._browser_assets(registry._grant)
                browser=registry.executor._browser.at_size(capture['width'],capture['height'])
                replay = replay_interaction(payload, browser, capture['actions'],
                    **_render_options(assets,path))
                same = (replay.png == log.read_artifact(Artifact(capture['image_sha256'], capture['image_bytes']))
                    and replay.served_sha256 == capture['source_sha256']
                    and list(replay.actions) == capture['actions'] and replay.text == capture['text']
                    and _settled_browser(replay.isolation)
                    and registry._snapshot(path)[1] == capture['source_sha256']
                    and list(replay.asset_manifest)==capture['asset_manifest']
                    and _same_assets(registry,capture['asset_manifest']))
                row = dict(path=path,width=capture['width'],height=capture['height'],viewport_name=capture['viewport_name'],status='FAIL', same_capture=same,
                    image_sha256=sha256(replay.png).hexdigest(), captured_image_sha256=capture['image_sha256'],
                    source_sha256=replay.served_sha256, actions=capture['actions'],
                    asset_manifest=list(replay.asset_manifest),document_path=path,
                    replay_isolation=replay.isolation, checker=None, protected_image=None)
                if same:
                    # The protected checker starts fresh and may perform its own
                    # actions. Its resulting PNG is evidence of that separate
                    # check, never substituted for the model recipe's picture.
                    protected = inspect_captured_page(payload, browser, self.inspection,
                        **_render_options(assets,path))
                    image = log.put_artifact(protected.png)
                    row.update(checker=protected.inspection, protected_image=(image.sha256, image.size_bytes),
                        protected_isolation=protected.isolation, inspector_sha256=self.inspection.sha256,
                        target=self.inspection.target)
                    if (protected.inspection and protected.inspection.get('status') == 'PASS'
                            and protected.served_sha256 == capture['source_sha256']
                            and _settled_browser(protected.isolation)
                            and registry._snapshot(path)[1] == capture['source_sha256']
                            and list(protected.asset_manifest)==capture['asset_manifest']
                            and _same_assets(registry,capture['asset_manifest'])):
                        row['status'] = 'PASS'
                checked.append(row)
            passed = len(checked) == len(chosen) and all(row['status'] == 'PASS' for row in checked)
            result.update(status='pass' if passed else 'fail', captures=tuple(chosen), inspections=tuple(checked),
                reason='same-source action replay and separate protected checks matched' if passed
                    else 'interaction replay or protected behavior failed')
            return result

@dataclass(frozen=True)
class CommandEvidencePolicy:
    """Host requirements checked against visible canonical command outcomes."""
    commands: tuple

    @classmethod
    def admit(cls,spec,registry):
        if (type(spec) is not dict or set(spec)!={'schema','commands'}
                or type(spec['schema']) is not int or spec['schema']!=1):
            raise ValueError('closed command evidence schema required')
        if not registry._grant.allow_shell or registry.executor._shell is None:
            raise ValueError('actual shell grant required')
        rows=spec['commands']
        if type(rows) is not list or not 1<=len(rows)<=32:
            raise ValueError('one to32 command requirements required')
        commands=[]
        for row in rows:
            if type(row) is not dict or set(row)!={'command','disposition','exit_code'}:
                raise ValueError('exact command,disposition,exit_code required')
            text=row['command'];kind=row['disposition'];code=row['exit_code']
            if type(text) is not str or not text.strip() or len(text.encode())>16384 or '\0' in text:
                raise ValueError('bounded literal shell command required')
            if kind not in ('exited','timeout','output_limit','spawn_error'):
                raise ValueError('known actual disposition required')
            if kind=='spawn_error':
                if code is not None:raise ValueError('spawn failure has no exit status')
            elif type(code) is not int or (kind!='exited' and code==0):
                raise ValueError('exact non-success status required for interrupted command')
            commands.append((text,kind,code))
        if len(set(commands))!=len(commands):raise ValueError('duplicate command requirement')
        return cls(tuple(commands))

    @property
    def identity(self):
        return sha256(encode(('bw.command-evidence-policy.v1',self.commands))).hexdigest()

    def verify(self,registry,log,outcomes):
        checked=[]
        with registry.executor._lock:
            registry._world_check()
            inventory=registry._inventory()
            for text,kind,code in self.commands:
                witness=None
                for frame,value in outcomes:
                    if (value.get('tool')!='run_shell' or value.get('disposition')!=kind
                            or value.get('exit_code')!=code or frame.get('state')!='Closed'):
                        continue
                    try:
                        plan=decode(log.read_artifact(Artifact(*frame['inputs'])))
                        if (type(plan) is not tuple or len(plan)!=8
                                or plan[:4]!=('bw.tool-plan.v2',registry.identity,registry.world,'run_shell')
                                or plan[4]!={'command':text}
                                or value['plan_sha256']!=frame['inputs'][0]):
                            continue
                        stored=decode(log.read_artifact(Artifact(*frame['result'])))
                        if stored[2]!=value:continue
                        details=value['details'];isolation=details.get('isolation',{})
                        if (details.get('workspace_after_sha256')!=inventory
                                or isolation.get('worker_exited') is not True
                                or isolation.get('namespace_members_after')!=[]
                                or isolation.get('kind')!='bubblewrap-terminal-v1'):
                            continue
                        for stream in ('stdout','stderr'):
                            log.read_artifact(Artifact(*value[stream]))
                        witness=frame['id']
                    except (KeyError,TypeError,ValueError,OSError):
                        continue
                checked.append(dict(command=text,disposition=kind,exit_code=code,command_frame=witness))
        passed=all(row['command_frame'] is not None for row in checked)
        return dict(status='pass' if passed else 'fail',policy='command-evidence-and-finish',
            policy_identity=self.identity,commands=tuple(checked),
            reason='current command evidence and retired namespaces matched' if passed else 'required current command evidence missing')


@dataclass(frozen=True)
class ProjectChecksPolicy:
    """Model-selected checks, verified by actual current execution receipts.

    This proves those checks ran successfully; it cannot prove the checks cover
    every requirement. Fixed host-selected policies remain available separately.
    Latest named results supersede older results without deleting their audit.
    """
    remote: bool = False

    @classmethod
    def admit(cls,spec,registry):
        if (type(spec) is not dict or set(spec)!={'schema','selected_checks'}
                or type(spec['schema']) is not int or spec['schema']!=1
                or spec['selected_checks'] is not True):
            raise ValueError('closed project check policy required')
        if not registry._grant.project_files or not registry._grant.allow_shell or registry.executor._shell is None:
            raise ValueError('project files and actual shell grant required')
        return cls(bool(registry._grant.remote_targets))

    @property
    def identity(self):return sha256(encode(('bw.project-checks-with-remote.v1',) if self.remote else ('bw.project-checks-policy.v1',))).hexdigest()

    def verify(self,registry,log,outcomes):
        outcomes=tuple(outcomes);latest={};invalid=False
        with registry.executor._lock:
            registry._world_check();inventory=registry._inventory()
            for frame,value in outcomes:
                if value.get('tool')!='run_check':continue
                try:
                    plan=decode(log.read_artifact(Artifact(*frame['inputs'])))
                    if (frame.get('state')!='Closed' or type(plan) is not tuple or len(plan)!=8
                            or plan[:4]!=('bw.tool-plan.v2',registry.identity,registry.world,'run_check')
                            or value['plan_sha256']!=frame['inputs'][0]):
                        raise ValueError('unbound check receipt')
                    args=registry._arguments('run_check',plan[4])
                    stored=decode(log.read_artifact(Artifact(*frame['result'])))
                    if stored[2]!=value:raise ValueError('changed outcome')
                    details=value['details'];isolation=details.get('isolation',{})
                    for stream in ('stdout','stderr'):log.read_artifact(Artifact(*value[stream]))
                    valid=(value.get('disposition')=='exited' and value.get('exit_code')==0
                        and details.get('workspace_after_sha256')==inventory
                        and isolation.get('worker_exited') is True
                        and isolation.get('namespace_members_after')==[]
                        and isolation.get('kind')=='bubblewrap-terminal-v1')
                    latest[args['name']]=dict(name=args['name'],command=args['command'],
                        command_frame=frame['id'],disposition=value.get('disposition'),
                        exit_code=value.get('exit_code'),status='pass' if valid else 'fail')
                except (ToolRejected,KeyError,TypeError,ValueError,OSError):invalid=True
        passed=bool(latest) and not invalid and all(row['status']=='pass' for row in latest.values())
        result=dict(status='pass' if passed else 'fail',policy='project-checks-and-finish',
            policy_identity=self.identity,checks=tuple(latest.values()),
            reason='selected checks passed on current files with retired namespaces' if passed
                else 'run meaningful named checks on the current files; rerun failed or stale checks before finishing')

        result=self._verify_remote(registry,log,outcomes,result,invalid) if self.remote else result
        from .pdf_tools import include_document_acceptance
        return include_document_acceptance(registry,log,outcomes,result)

    def _verify_remote(self,registry,log,outcomes,local,local_invalid):
        from .tool_registry import FrozenToolPlan
        from .remote_execution import RemoteIndeterminate
        needed={};latest={};invalid=local_invalid
        for frame,value in outcomes:
            tool=value.get('tool')
            if tool not in ('remote_command','check_remote','upload_file'):continue
            try:
                raw=log.read_artifact(Artifact(*frame['inputs']));plan=FrozenToolPlan(raw);row=decode(raw)
                if (frame['state']!='Closed' or type(row) is not tuple or len(row)!=8
                        or row[:4]!=('bw.tool-plan.v2',registry.identity,registry.world,tool)
                        or value['plan_sha256']!=frame['inputs'][0] or frame['dispatch'][0]!=value['operation_id']
                        or decode(log.read_artifact(Artifact(*frame['result'])))[2]!=value):raise ValueError('unbound remote evidence')
                args=registry._arguments(tool,row[4]);target=registry._remotes[args['target']];resource=target.resource_identity
                needed[resource]=args['target'];valid=False
                if value.get('disposition')!='rejected_before_execution':
                    registry._check_remote(args['target']);transport=registry._remote_transport(args['target'])
                    command,payload=registry._remote_arguments(plan,tool,args,value['operation_id'],retained=True)
                    native=transport.read_receipt(value['operation_id'],plan.sha256,command,stdin=payload)
                    expected=registry._remote_outcome(plan,value['operation_id'],tool,args,native)
                    if (type(value['exit_code']) is not type(native.exit_code) or value['exit_code']!=native.exit_code
                            or value['disposition']!=native.disposition or value['details']!=expected.metadata
                            or log.read_artifact(Artifact(*value['stdout']))!=native.stdout
                            or log.read_artifact(Artifact(*value['stderr']))!=native.stderr):raise ValueError('remote evidence differs from original outcome')
                    if tool=='check_remote':
                        try:valid=(native.disposition=='exited' and type(native.exit_code) is int and native.exit_code==0
                                   and registry.remote_check_current(plan,value['operation_id']))
                        except (ValueError,RemoteIndeterminate,OSError):valid=False
                if tool=='check_remote':
                    latest[resource]=dict(target=args['target'],resource_identity=resource,command=args['command'],command_frame=frame['id'],
                        disposition=value.get('disposition'),exit_code=value.get('exit_code'),status='pass' if valid else 'fail')
            except (KeyError,TypeError,ValueError,OSError,ToolRejected,RemoteIndeterminate):invalid=True
        local_changes=any(value.get('tool') in ('create_file','create_text_file','replace','replace_text_file','set_mode','build_pdf')
                          and value.get('disposition')!='rejected_before_execution' for _,value in outcomes)
        local_required=bool(local['checks']) or local_changes or bool(registry._grant.output_paths) or not needed
        remote_pass=all(resource in latest and latest[resource]['status']=='pass' for resource in needed)
        passed=(not invalid and (not local_required or local['status']=='pass') and remote_pass)
        return dict(status='pass' if passed else 'fail',policy='project-checks-and-finish',policy_identity=self.identity,
            checks=local['checks'],remote_checks=tuple(latest.values()),local_checks_required=local_required,
            remote_targets_requiring_checks=tuple(needed.values()),
            reason=('selected local and remote checks passed at their checked boundaries' if passed else
                'local edits need current local checks; each used remote target needs a passing final check with no later remote operation'))


@dataclass(frozen=True)
class ReadOnlyPolicy:
    """Read-only completion verifies containment, not the truth of model advice."""
    inventory: str
    @classmethod
    def admit(cls,spec,registry):
        if spec!={'schema':1,'read_only':True} or type(spec.get('schema')) is not int:
            raise ValueError('closed read-only policy required')
        grant=registry._grant
        if registry._cad is not None or registry._blender is not None or registry._pdf is not None:raise ValueError('read-only policy cannot admit CAD, Blender or PDF execution')
        if (grant.project_files or grant.edit_paths or grant.create_paths or grant.mode_paths
                or grant.allow_shell or grant.allow_tests or grant.output_paths or grant.command_names):
            raise ValueError('planning requires a read-only grant')
        return cls(registry._inventory())
    @property
    def identity(self):return sha256(encode(('bw.read-only-policy.v1',self.inventory))).hexdigest()
    def verify(self,registry,log,outcomes):
        with registry.executor._lock:
            registry._world_check();unchanged=registry._inventory()==self.inventory
        return dict(status='pass' if unchanged else 'fail',policy='read-only-and-finish',
            reason='Read-only inventory unchanged; advice is not independently verified' if unchanged else 'Read-only inventory changed',
            policy_identity=self.identity)
