"""General model tool proposals -> frozen host plans -> existing Executor.

The registry is not a workflow loop or grant issuer. A caller must durably bind
plans/operation IDs through FrameKernel before executing. Unknown effects require
reconciliation; calling execute twice is never an automatic retry contract.
"""
from dataclasses import dataclass
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import stat
import time
from .execution import Executor,Grant,ToolRejected,BrowserExecutionError,_relative_path,_operation_id
from .records import Artifact,encode,decode
from . import execution as execution_module

from . import text_file_codec
from .text_file_codec import MAX_TEXT_BYTES
_HEX=re.compile(r'[0-9a-f]{64}\Z')
# One definition table drives model schema, parsing and host dispatch admission.
# path permissions are selected from the host Grant, never model output.
_TOOLS={
 'read_file':('observe','read_paths',{'path':'path'}),
 'create_file':('change','create_paths',{'path':'path','content':'text'}),
 # Emit small control fields before the potentially long payload. New grammar
 # identities carry this ordering; previously saved grammar definitions stay immutable.
 'create_text_file':('change','create_paths',{'path':'path','line_ending':'line_ending','final_newline':'boolean','lines':'lines'}),
 'replace_text_file':('change','edit_paths',{'path':'path','line_ending':'line_ending','final_newline':'boolean','lines':'lines'}),
 'replace':('change','edit_paths',{'path':'path','before':'nonempty','after':'text'}),
 'set_mode':('change','mode_paths',{'path':'path','mode':'mode'}),
 'run_tests':('execute',None,{'suite':'unit'}),
 'run_shell':('execute',None,{'command':'shell'}),
 'run_check':('execute',None,{'name':'check_name','command':'shell'}),
 'capture_page':('execute', 'capture_paths',{'path':'path'}),
 'interact_page':('execute', 'interact_paths',{'path':'path','actions':'actions'}),
 'remote_command':('execute',None,{'target':'remote_target','command':'remote_shell'}),
 'check_remote':('execute',None,{'target':'remote_target','command':'remote_shell'}),
 'upload_file':('execute','read_paths',{'target':'remote_target','path':'path'}),
 'build_pdf':('execute','read_paths',{'path':'path','output':'path'}),
 'render_pdf':('execute','read_paths',{'path':'path','page':'pdf_page'}),
 'inspect_scene':('execute','read_paths',{'path':'path'}),
 'inspect_cad':('execute','read_paths',{'path':'path'}),
 'finish':('pure',None,{'answer':'text'}),
}


_OBSERVED_TOOLS=frozenset(('replace','replace_text_file','set_mode','capture_page','interact_page'))


class EffectIndeterminate(RuntimeError):
    def __init__(self,operation_id,plan_sha256):
        self.operation_id=operation_id;self.plan_sha256=plan_sha256
        super().__init__('tool outcome is unresolved for operation '+operation_id+' (plan '+plan_sha256+'); reconcile the original operation instead of resending')


@dataclass(frozen=True)
class FileObservation:
    world: str
    path: str
    sha256: str
    def __post_init__(self):
        _relative_path(self.path)
        if any(type(v) is not str or not _HEX.fullmatch(v) for v in (self.world,self.sha256)):
            raise ToolRejected('invalid host file observation')
    @property
    def wire(self):return (self.world,self.path,self.sha256)


@dataclass(frozen=True)
class FrozenToolPlan:
    data: bytes
    @property
    def sha256(self):return sha256(self.data).hexdigest()


@dataclass(frozen=True)
class ToolOutcome:
    disposition: str
    exit_code: int|None
    elapsed_seconds: float
    stdout: bytes
    stderr: bytes
    operation_id: str
    plan_sha256: str
    tool: str
    details: bytes=b''
    observation: FileObservation|None=None
    image: object=None
    requested_finish: bool=False
    assets: tuple=()
    @property
    def metadata(self):return {} if not self.details else decode(self.details)

    def publish(self,log):
        """Retain exact outputs once; return metadata + roots for Kernel delivery."""
        stdout=log.put_artifact(self.stdout);stderr=log.put_artifact(self.stderr);refs=[stdout,stderr]
        image=None
        if self.image is not None:
            captured=log.put_artifact(self.image.read_bytes());refs.append(captured)
            image=(captured.sha256,captured.size_bytes)
        for resource in self.assets:
            ref=log.put_artifact(resource.read_bytes())
            refs.append(ref)
        value=dict(schema=1,operation_id=self.operation_id,plan_sha256=self.plan_sha256,tool=self.tool,
            details=self.metadata,disposition=self.disposition,exit_code=self.exit_code,
            elapsed_seconds=self.elapsed_seconds,stdout=(stdout.sha256,stdout.size_bytes),
            stderr=(stderr.sha256,stderr.size_bytes),image=image,
            observation=None if self.observation is None else self.observation.wire,
            requested_finish=self.requested_finish)
        return value,tuple(dict.fromkeys(refs))


class ToolRegistry:
    def __init__(self,executor,grant,*,test_timeout=30.0,remote_targets=(),cad=None,blender=None,pdf=None):
        if not isinstance(executor,Executor) or not isinstance(grant,Grant):raise ToolRejected('host executor/grant required')
        if type(test_timeout) not in (int,float) or not math.isfinite(test_timeout) or not 0<test_timeout<=120:
            raise ToolRejected('invalid registered test timeout')
        self.executor=executor;self._grant=grant;self._test_timeout=float(test_timeout)
        self.world=sha256(encode(('bw.world.v1',str(executor.workspace),*executor._workspace_identity))).hexdigest()
        self._browser=executor._browser
        self._shell=executor._shell
        if grant.allow_shell and self._shell is None:raise ToolRejected("shell grant requires host ShellConfig")
        if self._browser is not None and (self._browser.inspection is not None or self._browser.actions):
            raise ToolRejected('protected inspections or hidden action recipes are not model tools')
        self._browser_binding=None
        if self._browser is not None:
            path=self._browser.executable.resolve(strict=True);info=path.stat()
            with path.open('rb') as stream:
                import hashlib
                binary_sha=hashlib.file_digest(stream,'sha256').hexdigest()
            from . import browser_capture, browser_isolation, browser_worker, browser_assets
            browser_sources=tuple(sha256(Path(m.__file__).read_bytes()).hexdigest() for m in
                (browser_capture,browser_isolation,browser_worker,browser_assets))
            self._browser_binding=(str(path),self._stat_key(info),binary_sha,self._browser.width,self._browser.height,self._browser.timeout,browser_sources,self._browser.viewports)
        from .remote_execution import RemoteTarget
        if type(remote_targets) is not tuple or any(not isinstance(v,RemoteTarget) for v in remote_targets) or len({v.name for v in remote_targets})!=len(remote_targets):
            raise ToolRejected('immutable host remote target definitions required')
        available={v.name:v for v in remote_targets}
        if any(name not in available for name in grant.remote_targets):raise ToolRejected('granted remote target has no host configuration')
        self._remotes={name:available[name] for name in sorted(grant.remote_targets)};self._remote_cache={};self._remote_sources=()
        if self._remotes:
            from . import remote_execution,remote_guest,remote_ownership,remote_upload
            self._remote_sources=tuple((Path(m.__file__),sha256(Path(m.__file__).read_bytes()).hexdigest()) for m in (remote_execution,remote_guest,remote_ownership,remote_upload))
        from .cad_tools import CadCapability
        if cad is not None and type(cad) is not CadCapability:raise ToolRejected('host CAD capability required')
        from .blender_tools import BlenderCapability
        if blender is not None and type(blender) is not BlenderCapability:raise ToolRejected('host Blender capability required')
        from .pdf_tools import PdfCapability
        if pdf is not None and type(pdf) is not PdfCapability:raise ToolRejected('host PDF capability required')
        self._pdf=pdf
        self._blender=blender
        self._cad=cad
        self._definitions={}
        for name,(effect,permission,fields) in _TOOLS.items():
            if name in ('build_pdf','render_pdf') and pdf is None:continue
            if name=='build_pdf' and not grant.project_files:continue
            if name=='inspect_scene' and blender is None:continue
            if name=='inspect_cad' and cad is None:continue
            if permission is not None and not grant.has_file_scope(permission):continue
            if name in ('remote_command','check_remote','upload_file') and not self._remotes:continue
            if name=='run_tests' and not grant.allow_tests:continue
            if name=='run_shell' and not grant.allow_shell:continue
            if name=='run_check' and not (grant.allow_shell and grant.project_files):continue
            if name in ('capture_page','interact_page') and self._browser is None:continue
            if name in ('capture_page','interact_page') and self._browser.viewports:
                fields=dict(fields,viewport='viewport')
            self._definitions[name]=(effect,permission,fields)
        capability=(grant.edit_paths,grant.create_paths,grant.read_paths,grant.capture_paths,grant.interact_paths,grant.asset_paths,grant.allow_tests,grant.mode_paths,grant.mode_mask,grant.output_paths,grant.project_files,grant.remote_targets)
        from . import terminal,terminal_worker
        shell_binding=None if self._shell is None else (self._shell.wire,
            sha256(Path(terminal.__file__).read_bytes()).hexdigest(),sha256(Path(terminal_worker.__file__).read_bytes()).hexdigest())
        if grant.output_paths:
            from . import command_outputs
            shell_binding=(shell_binding,sha256(Path(command_outputs.__file__).read_bytes()).hexdigest())
        self.identity=sha256(encode(('bw.tool-registry.v1',self.world,capability,self._test_timeout,
            self._browser_binding,(grant.allow_shell,shell_binding),None if cad is None else cad.identity,None if blender is None else blender.identity,None if pdf is None else pdf.identity,sha256(Path(__file__).read_bytes()).hexdigest(),
            sha256(Path(execution_module.__file__).read_bytes()).hexdigest(),
            sha256(Path(text_file_codec.__file__).read_bytes()).hexdigest(),
            tuple((k,v) for k,v in sorted(self._definitions.items())),
            tuple((name,target.identity,target.resource_identity) for name,target in self._remotes.items()),
            tuple((path.name,digest) for path,digest in self._remote_sources)))).hexdigest()

    @staticmethod
    def _stat_key(info):return (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns,stat.S_IMODE(info.st_mode))

    def _world_check(self):
        info=self.executor.workspace.lstat()
        if not stat.S_ISDIR(info.st_mode) or (info.st_dev,info.st_ino)!=self.executor._workspace_identity:
            raise ToolRejected('owned world is stale/replaced')
        if self.executor._browser is not self._browser:raise ToolRejected('registered browser configuration changed')
        if self.executor._shell is not self._shell:raise ToolRejected('registered shell configuration changed')
        if self._shell is not None:self._shell.check_host()
        if self._cad is not None:self._cad.runtime.check()
        if self._blender is not None:self._blender.check()
        if self._pdf is not None:self._pdf.check()
        if self._browser_binding is not None:
            path,key,*_=self._browser_binding
            if self._stat_key(Path(path).stat())!=key:raise ToolRejected('registered browser executable changed')

    def operation_kind(self,tool):
        if tool not in self._definitions:raise ToolRejected('unregistered tool')
        effect=self._definitions[tool][0]
        return {'observe':'OBSERVE','change':'ACT','execute':'ACT','pure':'TRANSFORM'}[effect]

    def definition_bytes(self,tool):
        if tool not in self._definitions:raise ToolRejected('unregistered tool')
        return encode(('bw.registered-tool.v1',self.identity,tool,self._definitions[tool]))

    def model_schema(self):
        variants=[]
        for name,(_,permission,fields) in self._definitions.items():
            properties={}
            for key,kind in fields.items():
                if kind=='path':
                    rule=(dict(type='string',minLength=1,maxLength=4096,description='Any project-relative file, including files created later. The host rejects absolute paths, traversal, links and Git administration.')
                          if self._grant.project_files and permission in ('read_paths','edit_paths','create_paths')
                          else dict(type='string',enum=list(getattr(self._grant,permission))))
                elif kind=='pdf_page':rule=dict(type='integer',minimum=1,maximum=256,description='One actual PDF page, numbered from 1.')
                elif kind=='remote_target':rule=dict(type='string',enum=list(self._remotes),description='Host-authorized remote admin scope. Credentials stay on this client.')
                elif kind=='remote_shell':rule=dict(type='string',minLength=1,maxLength=16384,description='Bash on the selected remote target, not the local project sandbox. Use remote_command to change it. Use check_remote for one composite final check for that target; all assertions must pass. Any later remote operation makes that check stale.')
                elif kind=='lines':
                    rule=dict(type='array',maxItems=text_file_codec.MAX_TEXT_LINES,items=dict(type='string',maxLength=MAX_TEXT_BYTES,description='One physical line. Host rejects decoded CR or LF inside an element.'))
                elif kind=='line_ending':rule=dict(type='string',enum=['LF','CRLF'])
                elif kind=='boolean':rule=dict(type='boolean')
                elif kind=='viewport':
                    rule=dict(type='string',enum=[name for name,_,_ in self._browser.viewports],
                        description='Host viewports: '+', '.join(name+'='+str(w)+'x'+str(h) for name,w,h in self._browser.viewports))
                elif kind=='mode':rule=dict(type='string',pattern='^0[0-7]{3}$',minLength=4,maxLength=4,description='Only host-authorized permission bits may change')
                elif kind=='digest':rule=dict(type='string',pattern='^[0-9a-f]{64}$',minLength=64,maxLength=64)
                elif kind=='unit':rule=dict(type='string',enum=['unit'])
                elif kind=='check_name':rule=dict(type='string',pattern='^[A-Za-z][A-Za-z0-9_-]{0,63}$',minLength=1,maxLength=64,description='Stable check name. Rerun the same name after fixing a failed check or changing files.')
                elif kind=='shell':rule=dict(type='string',minLength=1,maxLength=16384,
                    description=('Bash with protected inputs and declared output paths: '+json.dumps(self._grant.output_paths)+'; separate stdout/stderr/status; no host home or network'
                    if self._grant.output_paths else 'Bash in a read-only file projection; separate stdout/stderr/status; no host home or network'))
                elif kind=='actions':
                    variants_actions=[]
                    for action in ('click','fill'):
                        props=dict(kind=dict(type='string',enum=[action]),
                            target=dict(type='string',pattern='^[A-Za-z][A-Za-z0-9_-]{0,63}$',minLength=1,maxLength=64),
                            value=(dict(type='string',enum=['']) if action=='click' else dict(type='string',maxLength=4096)))
                        variants_actions.append(dict(type='object',properties=props,required=['kind','target','value'],additionalProperties=False))
                    rule=dict(type='array',minItems=1,maxItems=16,items=dict(oneOf=variants_actions))
                else:rule=dict(type='string',minLength=1 if kind=='nonempty' else 0,maxLength=MAX_TEXT_BYTES)
                if kind=='shell':
                    if name=='run_shell':
                        rule['description']+='; Exploration only: this does not register a completion check. Use run_check for final verification when granted.'
                    elif name=='run_check':
                        rule['description']+='; Registers a named completion check. Its command must return zero when the assertion is satisfied; assert expected negative-case statuses instead of returning them as check failures.'
                    rule['description']+=(
                        '; The working directory is already the prepared project root: use project-relative paths, not guessed /project or host paths.'
                        ' Edit source through granted file tools, not sed -i, chmod or shell redirection.'
                        ' To test a readable shell script without execute permission, invoke sh script.sh with its arguments.'
                        ' Keep each command short and focused; wait for its result before choosing the next action.'
                    )
                    rule['description']+=(
                        '; Host enforces '+format(self.executor._shell.timeout,'g')+' seconds deadline and retires the invocation before returning.'
                        ' Each call has a new PID namespace; later calls cannot inspect earlier sandbox PIDs.'
                        ' /tmp is fresh for every call: temporary files from an earlier call are gone. Create and consume temporary files in the same command.'
                        ' Cleanup evidence is details.isolation.worker_exited and namespace_members_after.'
                        ' A timeout disposition is not success. The host already owns the deadline; nested cancellation wrappers are unnecessary unless the task explicitly requires them.')
                if key=='path' and name in ('inspect_cad','inspect_scene'):
                    rule['description']=('Python entry to build and independently inspect in the pinned CAD runtime. Exports and actual views are returned as immutable artifacts, not files in the project. Rerun after edits; finish after current checks pass.' if name=='inspect_cad' else 'Python entry to build and independently reopen in real Blender through MCP. Save scene.blend in /work. Returns controlled actual PNG views and MP4 as immutable artifacts, not project files. Rerun after edits; finish after current checks pass.')
                properties[key]=rule
            variants.append(dict(type='object',properties=dict(tool=dict(type='string',enum=[name]),
                arguments=dict(type='object',properties=properties,required=list(fields),additionalProperties=False)),
                required=['tool','arguments'],additionalProperties=False))
        return dict(oneOf=variants)

    def model_gbnf(self):
        """Tool-first JSON output from the same grant/field definition table.

        Select the tool discriminator before its arguments. JSON Schema's
        canonical property sorting otherwise puts arguments first. This is a
        distinct pinned grammar arrangement, never an in-place controller edit.
        Host admission still enforces byte limits and live file preconditions.
        Separator whitespace is bounded so a legal-token greedy model cannot
        loop on spaces outside JSON strings. Literal file contents are unchanged.
        Existing registered grammar definitions retain their original identity.
        """
        def literal(text):return json.dumps(text,ensure_ascii=True)
        def atom(value):return literal(json.dumps(value,ensure_ascii=True))
        rules=[];names=[]
        for index,(tool,(_,permission,fields)) in enumerate(self._definitions.items()):
            name='call-'+str(index);names.append(name)
            pieces=[literal('{'),'ws',literal('"tool"'),'ws',literal(':'),'ws',atom(tool),'ws',literal(','),'ws',literal('"arguments"'),'ws',literal(':'),'ws',literal('{'),'ws']
            for field_index,(key,kind) in enumerate(fields.items()):
                if field_index:pieces.extend([literal(','),'ws'])
                pieces.extend([literal(json.dumps(key)),'ws',literal(':'),'ws'])
                if kind=='path':
                    if self._grant.project_files and permission in ('read_paths','edit_paths','create_paths'):
                        value='project-path'
                    else:
                        path_rule='paths-'+str(index)+'-'+str(field_index)
                        rules.append(path_rule+' ::= '+' | '.join(atom(path) for path in getattr(self._grant,permission)))
                        value=path_rule
                elif kind=='pdf_page':value='pdf-page-number'
                elif kind=='remote_target':
                    target_rule='remote-targets-'+str(index)
                    rules.append(target_rule+' ::= '+' | '.join(atom(v) for v in self._remotes))
                    value=target_rule
                elif kind=='remote_shell':value='shell-command'
                elif kind=='lines':value='text-lines'
                elif kind=='line_ending':value='line-ending'
                elif kind=='boolean':value='boolean'
                elif kind=='viewport':
                    menu_rule='viewports-'+str(index)+'-'+str(field_index)
                    rules.append(menu_rule+' ::= '+' | '.join(atom(name) for name,_,_ in self._browser.viewports))
                    value=menu_rule
                elif kind=='mode':value='file-mode'
                elif kind=='digest':value='digest'
                elif kind=='unit':value=atom('unit')
                elif kind=='nonempty':value='nonempty'
                elif kind=='shell':value='shell-command'
                elif kind=='check_name':value='check-name'
                elif kind=='actions':value='browser-actions'
                else:value='string'
                pieces.extend([value,'ws'])
            pieces.extend([literal('}'),'ws',literal('}'),'ws'])
            rules.append(name+' ::= '+' '.join(pieces))
        rules[:0]=['root ::= '+' | '.join(names),r'ws ::= [ \t\n\r]?',
            r'string ::= "\"" char{0,32768} "\""',
            r'nonempty ::= "\"" char{1,32768} "\""',
            r'shell-command ::= "\"" char{1,16384} "\""',
            r'digest ::= "\"" [0-9a-f]{64} "\""',
            r'char ::= [^"\\\x00-\x1F] | "\\" (["\\/bfnrt] | "u" [0-9a-fA-F]{4})']
        if 'render_pdf' in self._definitions:
            rules.append('pdf-page-number ::= '+' | '.join(atom(n) for n in range(1,257)))
        if 'run_check' in self._definitions:
            rules.append('check-name ::= '+literal(chr(34))+' [A-Za-z] [A-Za-z0-9_-]{0,63} '+literal(chr(34)))
        if self._grant.project_files:
            rules.append('project-path ::= '+literal(chr(34))+' char{1,4096} '+literal(chr(34)))
        if 'set_mode' in self._definitions:
            rules.append(r'file-mode ::= "\"" "0" [0-7]{3} "\""')
        if any(name in self._definitions for name in ('create_text_file','replace_text_file')):
            rules.extend([
                'text-lines ::= "[" ws (line-string (ws "," ws line-string){0,4095})? ws "]"',
                'line-string ::= '+literal('"')+' line-char{0,32768} '+literal('"'),
                r'line-char ::= [^"\\\x00-\x1F] | "\\" (["\\/bft] | "u" [0-9a-fA-F]{4})',
                'line-ending ::= '+atom('LF')+' | '+atom('CRLF'),
                'boolean ::= "true" | "false"'])
        if 'interact_page' in self._definitions:
            rules.extend([r'browser-actions ::= "[" ws browser-action (ws "," ws browser-action){0,15} ws "]"',
                'browser-action ::= browser-click | browser-fill',
                'browser-target ::= '+literal('"')+' [A-Za-z] [A-Za-z0-9_-]{0,63} '+literal('"'),
                'browser-value ::= '+literal('"')+' char{0,4096} '+literal('"')])
            for action,value_rule in [('click',atom('')),('fill','browser-value')]:
                parts=[literal('{'),'ws',literal('"kind"'),'ws',literal(':'),'ws',atom(action),'ws',
                    literal(','),'ws',literal('"target"'),'ws',literal(':'),'ws','browser-target','ws',
                    literal(','),'ws',literal('"value"'),'ws',literal(':'),'ws',value_rule,'ws',literal('}')]
                rules.append('browser-'+action+' ::= '+' '.join(parts))
        return '\n'.join(rules)+'\n'

    def _arguments(self,tool,args):
        if type(tool) is not str or tool not in self._definitions:raise ToolRejected('tool is not granted/registered')
        _,permission,fields=self._definitions[tool]
        if type(args) is not dict or set(args)!=set(fields):raise ToolRejected('unknown or missing tool argument')
        for key,kind in fields.items():
            value=args[key]
            if kind=='pdf_page':
                if type(value) is not int or not 1<=value<=256:raise ToolRejected('PDF page must be an integer from 1 to 256')
                continue
            if kind=='actions':
                from .browser_capture import page_action_recipe
                try:page_action_recipe(value)
                except (ValueError,TypeError) as exc:raise ToolRejected('invalid browser actions: '+str(exc)) from exc
                continue
            if kind=='lines':
                if type(value) is not list:raise ToolRejected('lines must be an array')
                continue
            if kind=='boolean':
                if type(value) is not bool:raise ToolRejected('final_newline must have exact boolean type')
                continue
            if type(value) is not str:raise ToolRejected('tool argument must have the exact registered type')
            if kind=='path':
                if not self._grant.permits_file(permission,value):raise ToolRejected('path is not granted')
            elif kind=='viewport':
                if value not in {name for name,_,_ in self._browser.viewports}:raise ToolRejected('viewport is not granted')
            elif kind=='line_ending':
                if value not in ('LF','CRLF'):raise ToolRejected('line_ending must be LF or CRLF')
            elif kind=='mode':
                if re.fullmatch('0[0-7]{3}',value) is None:raise ToolRejected('four octal digits required')
            elif kind=='digest':
                if not _HEX.fullmatch(value):raise ToolRejected('exact source SHA256 required')
            elif kind=='remote_target':
                if value not in self._remotes:raise ToolRejected('remote target is not granted')
            elif kind=='remote_shell':
                if not value or '\0' in value or len(value.encode('utf8'))>16384:raise ToolRejected('bounded remote command required')
            elif kind=='shell':self._shell.validate(value)
            elif kind=='check_name':
                if re.fullmatch('[A-Za-z][A-Za-z0-9_-]{0,63}',value) is None:raise ToolRejected('bounded check name required')
            elif kind=='unit':
                if value!='unit':raise ToolRejected('only registered unit tests are available')
            elif len(value.encode('utf8'))>MAX_TEXT_BYTES or (kind=='nonempty' and not value):
                raise ToolRejected('tool argument byte bound/preimage violated')
        if tool in ('create_text_file','replace_text_file'):
            text_file_codec.encode_lines(args['lines'],args['line_ending'],args['final_newline'])
        return args

    def parse(self,text):
        if type(text) is not str or len(text.encode('utf8'))>131072:raise ToolRejected('bounded complete JSON proposal required')
        def pairs(items):
            value={}
            for key,item in items:
                if key in value:raise ToolRejected('duplicate proposal field')
                value[key]=item
            return value
        try:
            value=json.loads(text,object_pairs_hook=pairs)
            if type(value) is not dict or set(value)!={'tool','arguments'}:raise ToolRejected('invalid tool proposal envelope')
            return value['tool'],self._arguments(value['tool'],value['arguments'])
        except (ValueError,TypeError,RecursionError) as exc:raise ToolRejected('invalid tool proposal: '+str(exc)[:256]) from exc

    def _bound_arguments(self,tool,args):
        """Validate one canonical host-bound plan, not another model format."""
        if type(args) is not dict:raise ToolRejected('bound arguments must be a mapping')
        wire=dict(args)
        if tool in _OBSERVED_TOOLS:
            digest=wire.pop('source_sha256',None)
            if type(digest) is not str or not _HEX.fullmatch(digest):
                raise ToolRejected('bound plan requires an exact observed source SHA256')
        self._arguments(tool,wire)

    def _snapshot(self,path):
        try:
            with self.executor._parent_directory(path) as (parent,name):
                try:before=os.stat(name,dir_fd=parent,follow_symlinks=False)
                except FileNotFoundError:return (path,None,None)
                if not stat.S_ISREG(before.st_mode):raise ToolRejected('dependency is not a regular private file')
                body=self.executor._read_private_bytes(path)
                after=os.stat(name,dir_fd=parent,follow_symlinks=False)
                if self._stat_key(before)!=self._stat_key(after):raise ToolRejected('file changed while freezing dependency')
                return (path,sha256(body).hexdigest(),stat.S_IMODE(after.st_mode))
        except execution_module._MissingParent:
            return (path,None,None)

    def _inventory(self):
        items=[];count=0;total=0
        for directory,dirs,files,fd in os.fwalk(self.executor.workspace,follow_symlinks=False):
            relative=Path(directory).relative_to(self.executor.workspace)
            for name in dirs:
                info=os.stat(name,dir_fd=fd,follow_symlinks=False)
                if name=='.git' or not stat.S_ISDIR(info.st_mode):raise ToolRejected('unsupported workspace directory/link')
                items.append(('directory',(relative/name).as_posix(),stat.S_IMODE(info.st_mode)))
            for name in files:
                path=(relative/name).as_posix();snapshot=self._snapshot(path);items.append(('file',*snapshot))
                total+=os.stat(name,dir_fd=fd,follow_symlinks=False).st_size
            count+=len(dirs)+len(files)
            if count>20000 or total>64*1024**2:raise ToolRejected('workspace exceeds registered inventory limits')
        digest=sha256(b'bw.workspace-inventory.v1\0')
        for item in sorted(items):digest.update(encode(item))
        return digest.hexdigest()

    def _dependencies(self,tool,args):
        if tool=='finish':return (),None
        if tool=='build_pdf':
            if not args['path'].endswith('.py') or not args['output'].endswith('.pdf') or self._snapshot(args['path'])[1] is None:
                raise ToolRejected('existing Python entry and project PDF output required')
            permission='create_paths' if self._snapshot(args['output'])[1] is None else 'edit_paths'
            if not self._grant.permits_file(permission,args['output']):raise ToolRejected('PDF output mutation is not granted')
            return (),self._inventory()
        if tool=='render_pdf':
            if not args['path'].endswith('.pdf') or self._snapshot(args['path'])[1] is None:raise ToolRejected('existing project PDF required')
            return (),self._inventory()
        if tool in ('inspect_cad','inspect_scene'):

            if not args['path'].endswith('.py') or self._snapshot(args['path'])[1] is None:raise ToolRejected('existing captured CAD Python entry required')
            return (),self._inventory()
        if tool in ('remote_command','check_remote'):
            self._check_remote(args['target']);return (),None
        if tool=='upload_file':self._check_remote(args['target'])
        if tool in ('run_tests','run_shell','run_check'):return (),self._inventory()
        snapshot=self._snapshot(args['path'])
        if tool in ('create_file','create_text_file'):
            if snapshot[1] is not None:raise ToolRejected('creation target already exists/stale')
        elif snapshot[1] is None:raise ToolRejected('required source is absent/stale')
        if tool in _OBSERVED_TOOLS and snapshot[1]!=args['source_sha256']:
            raise ToolRejected('observed source revision is stale')
        if tool=='replace':
            # Validate the exact edit while it is still a pure precondition.
            # Rechecked at ACT as well as PLAN; do not catch a post-write
            # ToolRejected and relabel a possibly completed effect as harmless.
            original=self.executor._read_private_bytes(args['path'])
            if sha256(original).hexdigest()!=snapshot[1]:
                raise ToolRejected('observed source revision is stale')
            self.executor._replacement_bytes(original,args['before'].encode('utf8'),args['after'].encode('utf8'))
        if tool=='upload_file':
            from .remote_upload import MAX_UPLOAD
            if len(self.executor._read_private_bytes(args['path']))>MAX_UPLOAD:raise ToolRejected('upload exceeds4MiB bound')
        if tool=='set_mode' and (int(args['mode'],8)^snapshot[2])&~self._grant.mode_mask:
            raise ToolRejected('mode change exceeds the host bit mask')
        resources=()
        if tool in ('capture_page','interact_page'):
            if args['path'] in self._grant.asset_paths:raise ToolRejected('document aliases a resource')
            resources=tuple(self._snapshot(path) for path in self._grant.asset_paths)
            if any(row[1] is None for row in resources):raise ToolRejected('required browser asset is absent/stale')
            # Validate media/byte bounds while PLAN is still side-effect-free.
            self.executor._browser_assets(self._grant)
        return (snapshot,*resources),None

    def freeze(self,text,*,observations=()):
        tool,args=self.parse(text)
        if type(observations) is not tuple or any(not isinstance(v,FileObservation) for v in observations):
            raise ToolRejected('visible host observations required')
        witness=None
        if tool in _OBSERVED_TOOLS:
            observed=next((v for v in reversed(observations) if v.world==self.world and v.path==args['path']),None)
            if observed is None:raise ToolRejected('read the exact source in this visible world before editing/capturing')
            # Bind the latest visible observation, never a newly inferred live
            # hash or an older matching read. _dependencies checks it against
            # actual bytes while holding the world lock.
            witness=observed.wire
            args={**args,'source_sha256':observed.sha256}
        with self.executor._lock:
            self._world_check();preimages,inventory=self._dependencies(tool,args)
            return FrozenToolPlan(encode(('bw.tool-plan.v2',self.identity,self.world,tool,args,preimages,inventory,witness)))

    def execute(self,plan,operation_id):
        """Only after committed Kernel intent. Errors after entry remain unresolved."""
        operation_id=_operation_id(operation_id)
        if not isinstance(plan,FrozenToolPlan):raise ToolRejected('frozen host plan required')
        try:
            row=decode(plan.data)
            if type(row) is not tuple or len(row)!=8 or row[:3]!=('bw.tool-plan.v2',self.identity,self.world):
                raise ToolRejected('plan belongs to another registry/world')
            _,_,_,tool,args,preimages,inventory,witness=row
            self._bound_arguments(tool,args)
            if tool in _OBSERVED_TOOLS and witness!=(self.world,args['path'],args['source_sha256']):
                raise ToolRejected('plan lacks its admitted observation')
        except (ValueError,TypeError,KeyError) as exc:raise ToolRejected('invalid frozen tool plan: '+str(exc)[:256]) from exc
        with self.executor._lock:
            self._world_check()
            if self._dependencies(tool,args)!=(preimages,inventory):raise ToolRejected('plan dependency is stale')
            if tool=='finish':
                return ToolOutcome('completion_requested',None,0.0,args['answer'].encode('utf8'),b'',
                    operation_id,plan.sha256,tool,requested_finish=True)
            if tool in ('remote_command','check_remote','upload_file'):
                from .remote_execution import RemoteIndeterminate
                from .remote_ownership import RemoteTargetBusy
                try:
                    command,payload=self._remote_arguments(plan,tool,args,operation_id)
                    result=self._remote_transport(args['target']).run(operation_id,plan.sha256,command,stdin=payload)
                except (RemoteTargetBusy,ValueError) as error:raise ToolRejected(str(error)) from error
                except Exception as error:raise EffectIndeterminate(operation_id,plan.sha256) from error
                try:return self._remote_outcome(plan,operation_id,tool,args,result)
                except Exception as error:raise EffectIndeterminate(operation_id,plan.sha256) from error
            # From this point an external operation may have happened even if
            # receipt/artifact publication fails. Never call that an untouched
            # rejection or let an adapter invent a retry with a new identity.
            try:
                if tool in ('build_pdf','render_pdf'):
                    from .pdf_tools import execute_pdf
                    return execute_pdf(self,plan,operation_id,args,inventory,tool)
                if tool=='inspect_scene':
                    from .blender_tools import execute_blender
                    return execute_blender(self,plan,operation_id,args,inventory)
                if tool=='inspect_cad':
                    from .cad_tools import execute_cad
                    return execute_cad(self,plan,operation_id,args,inventory)
                expected=None
                if tool=='set_mode':original=self.executor._read_private_bytes(args['path'])
                if tool=='replace':
                    original=self.executor._read_private_bytes(args['path'])
                    expected=original.replace(args['before'].encode('utf8'),args['after'].encode('utf8'),1)
                elif tool=='create_file':expected=args['content'].encode('utf8')
                elif tool in ('create_text_file','replace_text_file'):
                    expected=text_file_codec.encode_lines(args['lines'],args['line_ending'],args['final_newline'])
                if tool=='read_file':result=self.executor.read_file(operation_id,self._grant,args['path'])
                elif tool in ('create_file','create_text_file'):result=self.executor.create_file(operation_id,self._grant,args['path'],expected)
                elif tool=='replace_text_file':result=self.executor.replace_file(operation_id,self._grant,args['path'],args['source_sha256'],expected)
                elif tool=='replace':result=self.executor.replace(operation_id,self._grant,args['path'],args['source_sha256'],args['before'].encode('utf8'),args['after'].encode('utf8'))
                elif tool=='set_mode':result=self.executor.set_mode(operation_id,self._grant,args['path'],args['source_sha256'],args['mode'])
                elif tool=='run_tests':result=self.executor.run_tests(operation_id,self._grant,self._test_timeout)
                elif tool in ('run_shell','run_check'):result=self.executor.run_shell(operation_id,self._grant,args['command'])
                else:
                    viewport_options={} if 'viewport' not in args else dict(viewport=args['viewport'])
                    try:
                        result=(self.executor.interact_page(operation_id,self._grant,args['path'],args['source_sha256'],args['actions'],**viewport_options)
                            if tool=='interact_page' else self.executor.capture_page(operation_id,self._grant,args['path'],args['source_sha256'],**viewport_options))
                    except BrowserExecutionError as error:
                        result=self.executor._publish_browser_error(error,operation_id,args['path'],**viewport_options)
                    if result.operation_id!=operation_id:raise ValueError('capture operation binding mismatch')
                    details=dict(viewport=result.viewport,viewport_name=result.viewport_name,browser_version=result.browser_version,
                        served_sha256=result.served_sha256,isolation=result.isolation,
                        asset_manifest=list(result.asset_manifest),served_assets=list(result.served_assets),
                        document_path=result.document_path,runtime_errors=list(result.runtime_errors))
                    if tool=='interact_page':details.update(actions=list(result.actions),text=result.text)
                    # An actual page exception is settled only after the isolated
                    # worker returned a complete, validated retirement receipt.
                    # Publication failures below still remain indeterminate.
                    errors=result.runtime_errors
                    return ToolOutcome('browser_error' if errors else 'captured',1 if errors else 0,result.elapsed_seconds,
                        result.text.encode('utf8') if tool=='interact_page' else b'actual PNG captured',
                        chr(10).join(errors).encode('utf8'),
                        operation_id,plan.sha256,tool,details=encode(details),
                        observation=FileObservation(self.world,args['path'],result.source.sha256),image=result.image,assets=result.assets)
                if result.operation_id!=operation_id:raise ValueError('tool operation binding mismatch')
                stdout=result.stdout.read_bytes();stderr=result.stderr.read_bytes();observation=None
                if tool not in ('run_tests','run_shell','run_check'):
                    if tool=='set_mode':
                        receipt=json.loads(stdout)
                        if (receipt.get('path')!=args['path'] or receipt.get('after_mode')!=args['mode']
                                or receipt.get('content_sha256')!=args['source_sha256']):
                            raise ValueError('mode receipt differs from bound operation')
                        actual=original
                    else:actual=stdout if tool=='read_file' else self.executor._read_private_bytes(args['path'])
                    if expected is not None and actual!=expected:raise ValueError('actual file does not match the completed mutation')
                    observation=FileObservation(self.world,args['path'],sha256(actual).hexdigest())
                if tool in ('run_shell','run_check'):
                    result.details['workspace_after_sha256']=self._inventory()
                return ToolOutcome(result.disposition,result.exit_code,result.elapsed_seconds,stdout,stderr,
                                   operation_id,plan.sha256,tool,observation=observation,
                                    details=encode(result.details) if tool in ('run_shell','run_check') else b'',
                                    assets=result.assets if tool in ('run_shell','run_check') else ())
            except Exception as exc:raise EffectIndeterminate(operation_id,plan.sha256) from exc


    def _check_remote(self,name):
        try:
            for path,digest in self._remote_sources:
                if sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('registered remote implementation changed')
            self._remotes[name].check()
        except (KeyError,ValueError,OSError) as error:raise ToolRejected('remote target/definition is stale or unavailable') from error

    def _remote_transport(self,name):
        if name not in self._remotes:raise ToolRejected('remote target is not granted')
        if name not in self._remote_cache:
            from .remote_execution import RemoteTransport,_directory
            root=_directory(self.executor.run_dir/'remote-operations')
            self._remote_cache[name]=RemoteTransport(root/name,self._remotes[name])
        return self._remote_cache[name]

    def _remote_arguments(self,plan,tool,args,operation_id,*,retained=False):
        if tool!='upload_file':return args['command'],b''
        from . import remote_upload
        import shlex
        row=decode(plan.data);preimages=row[5]
        if len(preimages)!=1 or preimages[0][0]!=args['path'] or not _HEX.fullmatch(preimages[0][1]):raise ValueError('missing bound upload source')
        digest=preimages[0][1]
        command=shlex.join(['/usr/bin/python3','-c',Path(remote_upload.__file__).read_text(),Path(args['path']).name,digest])
        if retained:
            from .remote_execution import _private
            transport=self._remote_transport(args['target'])
            intent=json.loads(_private(transport.root/operation_id/'intent.json'));payload=transport._stdin(intent)
        else:payload=self.executor._read_private_bytes(args['path'])
        if len(payload)>remote_upload.MAX_UPLOAD or sha256(payload).hexdigest()!=digest:raise ValueError('upload bytes differ from frozen source')
        return command,payload

    def _remote_outcome(self,plan,operation_id,tool,args,result):
        from .remote_execution import _json
        transport=self._remote_transport(args['target']);target=self._remotes[args['target']]
        command,payload=self._remote_arguments(plan,tool,args,operation_id,retained=True)
        intent=transport.intent(operation_id,plan.sha256,command,stdin=payload)
        details=dict(schema=1,target=args['target'],target_identity=target.identity,resource_identity=target.resource_identity,
            remote_intent_sha256=sha256(_json(intent)).hexdigest(),remote_receipt_sha256=result.receipt_sha256,
            command=command,scope='remote command outcome; administrative services may persist')
        if tool=='upload_file':
            details.update(source_path=args['path'],source_sha256=sha256(payload).hexdigest(),source_bytes=len(payload))
            if result.disposition=='exited' and result.exit_code==0:
                info=json.loads(result.stdout)
                from pathlib import PurePosixPath
                suffix=('.branchwrite-uploads',details['source_sha256'],Path(args['path']).name)
                if (type(info) is not dict or set(info)!={'schema','remote_path','sha256','bytes'} or type(info['schema']) is not int or info['schema']!=1
                    or info['sha256']!=details['source_sha256'] or type(info['bytes']) is not int or info['bytes']!=len(payload)
                    or type(info['remote_path']) is not str or not PurePosixPath(info['remote_path']).is_absolute()
                    or str(PurePosixPath(info['remote_path']))!=info['remote_path'] or '..' in PurePosixPath(info['remote_path']).parts
                    or PurePosixPath(info['remote_path']).parts[-3:]!=suffix):raise ValueError('uploaded file receipt differs from frozen source')
                details['remote_path']=info['remote_path']
        return ToolOutcome(result.disposition,result.exit_code,result.elapsed_seconds,result.stdout,result.stderr,
            operation_id,plan.sha256,tool,details=encode(details))

    def reconcile(self,plan,operation_id):
        """Read a known ORIGINAL remote receipt; never dispatch or recheck a new world."""
        try:
            row=decode(plan.data)
            if type(row) is not tuple or len(row)!=8 or row[:3]!=('bw.tool-plan.v2',self.identity,self.world) or row[3] not in ('remote_command','check_remote','upload_file'):
                raise ValueError('no retained remote reconciliation for this tool')
            tool,args=row[3],row[4];self._bound_arguments(tool,args);self._check_remote(args['target'])
            transport=self._remote_transport(args['target'])
            command,payload=self._remote_arguments(plan,tool,args,operation_id,retained=True)
            result=transport.read_receipt(operation_id,plan.sha256,command,stdin=payload)
            owner=transport._ownership()
            with owner.hold() as held:
                if owner.marker.exists():
                    from .remote_execution import _private
                    marker=json.loads(_private(owner.marker))
                    if marker.get('intent_path')==str(transport.root/operation_id/'intent.json'):
                        held.complete(transport._validate_durable_outcome)
            return self._remote_outcome(plan,operation_id,tool,args,result)
        except Exception as error:raise EffectIndeterminate(operation_id,plan.sha256) from error

    def remote_check_current(self,plan,operation_id):
        """Only the latest settled call on the target can qualify its final check."""
        row=decode(plan.data)
        if row[3]!='check_remote':return False
        args=row[4];self._check_remote(args['target']);transport=self._remote_transport(args['target'])
        from .remote_execution import _json
        expected=sha256(_json(transport.intent(operation_id,plan.sha256,args['command']))).hexdigest()
        return transport._ownership().latest_intent()==expected
