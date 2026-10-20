"""Prepare a pack-backed COW root and publish a derived immutable catalog.

The setup file freezes admission arguments; OperationJournal retains original
HTTP intents/receipts. Neither file is a second model or workflow history.
"""
import hashlib,json,os,stat,tempfile
from pathlib import Path
from .client_setup import key_for_connection
from .coding_cli import _state,_bytes
from .cow_client import CowClient,HTTPTransport,OperationJournal,OperationIndeterminate,_OP_ID
from .golden_path import ProjectBase
from .base_choice import _revision,_hex64,_count

def _publish(state,name,value):
    raw=_bytes(value)+b'\n'
    if len(raw)>1024*1024:raise ValueError('base setup/catalog exceeds limit')
    path=state/name
    if path.exists() or path.is_symlink():
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd,'rb') as stream:
            info=os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid()
                    or info.st_nlink!=1 or stat.S_IMODE(info.st_mode)!=0o600):
                raise ValueError('base setup/catalog must be a private owned regular file')
            if stream.read(1024*1024+1)!=raw:raise ValueError('base setup/catalog changed; use a new state and operation ID')
        return
    fd,name=tempfile.mkstemp(prefix='.base-publish-',dir=state);temporary=Path(name)
    try:
        with os.fdopen(fd,'wb') as stream:
            os.fchmod(stream.fileno(),0o600);stream.write(raw);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
        directory=os.open(state,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(directory)
        finally:os.close(directory)
    finally:temporary.unlink(missing_ok=True)

def prepare(args):
    from datetime import datetime,timezone
    from .__main__ import _source
    from .run_cli import _pairs
    from .context_pack import load_verified_prefix
    from .project_context import (append_event,capture_context_pack,
                                  read_stable_branch,resume_context_pack)
    import fcntl
    connection=json.loads(_source(args.connection),object_pairs_hook=_pairs)
    if type(connection) is not dict or set(connection)!={'endpoint_url','endpoint_pin','model_contract_id','execution_profile_id','eos_tokens'}:
        raise ValueError('use the exact pinned connection fields; credentials belong in BW_COW_API_KEY')
    HTTPTransport(connection['endpoint_url'])
    for key in ['model_contract_id','execution_profile_id']:_hex64(connection[key],key)
    if type(connection['endpoint_pin']) is not str or not connection['endpoint_pin']:raise ValueError('endpoint identity pin required')
    _revision(args.source_revision,'source_revision');_count(args.capacity,'capacity',minimum=1)
    eos=connection['eos_tokens']
    if type(eos) is not list or not eos or any(type(t) is not int or t<0 for t in eos):raise ValueError('actual pinned EOS token IDs required')
    if not args.branch or len(args.branch.encode())>128:raise ValueError('bounded nonempty branch name required')
    if type(args.operation_id) is not str or not _OP_ID.fullmatch(args.operation_id):raise ValueError('explicit valid original operation ID required')
    if type(args.purpose) is not str or not args.purpose or len(args.purpose.encode())>8192:raise ValueError('bounded nonempty purpose required')
    project_mode=getattr(args,'project',None) is not None
    if project_mode:
        if args.context_pack is not None or args.context_pack_id is not None:raise ValueError('choose a project source or an existing pack')
        read_files=tuple(getattr(args,'read',()) or ());read_dirs=tuple(getattr(args,'read_dir',()) or ())
        source_branches=tuple(getattr(args,'source_branch',()) or ())
        request_source=dict(kind='project-and-cow-branches',project=str(Path(args.project).absolute()),
                            read_files=list(read_files),read_dirs=list(read_dirs),source_branches=list(source_branches))
    else:
        if getattr(args,'context_pack',None) is None or not args.context_pack.is_absolute():raise ValueError('reference pack requires an absolute path')
        if type(args.context_pack_id) is not str:_hex64(args.context_pack_id,'context_pack_id')
        _hex64(args.context_pack_id,'context_pack_id')
        load_verified_prefix(args.context_pack,expected_id=args.context_pack_id)
        request_source=dict(kind='existing-pack',pack_path=str(args.context_pack),pack_id=args.context_pack_id)
    api_key=key_for_connection(connection)
    if not api_key:raise ValueError('Connect to this server with branchwrite connect, or set BW_COW_API_KEY')
    state=_state(args.state,create=True)
    if (state/'coding-launch.json').exists():raise ValueError('use a separate base preparation state')
    fd=os.open(state/'.base-preparation.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'r+b') as lock:
        info=os.fstat(lock.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or info.st_uid!=os.getuid()
                or stat.S_IMODE(info.st_mode)!=0o600):raise ValueError('invalid base preparation lock')
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        base_request=dict(schema=1,connection=connection,branch=args.branch,purpose=args.purpose,
            source_revision=args.source_revision,capacity=args.capacity,operation_id=args.operation_id,
            source=request_source)
        _publish(state,'base-request.json',base_request)
        client=CowClient.http(connection['endpoint_url'],journal=OperationJournal(state/'cow-operations'),api_key=api_key,endpoint_pin=connection['endpoint_pin'])
        if project_mode:
            pack_info=resume_context_pack(args.project,state,read_files=read_files,read_dirs=read_dirs,
                                          branch_names=source_branches,output=state/'packs')
            if pack_info is None:
                if source_branches:
                    append_event(state,'SOURCE_BRANCH_READ_STARTED',branch_names=list(source_branches))
                branch_rows=tuple(read_stable_branch(client,name) for name in source_branches)
                as_of=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
                pack_info=capture_context_pack(args.project,state,read_files=read_files,read_dirs=read_dirs,
                    branches=branch_rows,as_of=as_of,output=state/'packs')
            context_pack=Path(pack_info['pack_path']);context_pack_id=pack_info['pack_id']
            source_receipt=_read_private_json(state/'context-source-receipt.json')
            source_receipt_sha256=hashlib.sha256(_bytes(source_receipt)).hexdigest()
        else:
            context_pack=args.context_pack;context_pack_id=args.context_pack_id
            source_receipt_sha256=None
        if project_mode:
            setup=dict(schema=2,connection=connection,branch=args.branch,purpose=args.purpose,
                reference_pack_path=str(context_pack),reference_pack_id=context_pack_id,
                source_revision=args.source_revision,capacity=args.capacity,operation_id=args.operation_id,
                source=request_source,source_receipt_sha256=source_receipt_sha256)
        else:
            # Keep the original schema byte-compatible so existing prepared states
            # can retry with their pinned pack and OperationJournal receipts.
            setup=dict(schema=1,connection=connection,branch=args.branch,purpose=args.purpose,
                reference_pack_path=str(context_pack),reference_pack_id=context_pack_id,
                source_revision=args.source_revision,capacity=args.capacity,operation_id=args.operation_id)
        _publish(state,'base-setup.json',setup)
        append_event(state,'SETUP_FROZEN',operation_id=args.operation_id)
        digest=hashlib.sha256(args.operation_id.encode()).hexdigest()[:40]
        namespace_operation='bw-base-namespace-'+digest;context_operation='bw-base-context-'+digest
        try:
            try:namespace=client.create_namespace('Project Base: '+args.branch,namespace_operation)
            except OperationIndeterminate:
                if not args.reconcile:raise
                client.replay_original(namespace_operation)
                namespace=client.create_namespace('Project Base: '+args.branch,namespace_operation)
            append_event(state,'NAMESPACE_DURABLE',operation_id=namespace_operation)
            ns=namespace['namespace_id']
            base=ProjectBase(client,ns,eos_tokens=tuple(connection['eos_tokens']))
            options=dict(branch=args.branch,purpose=args.purpose,pack_path=context_pack,
                         expected_pack_id=context_pack_id,operation_id=context_operation)
            try:version=base.prepare_pack(**options)
            except OperationIndeterminate:
                if not args.reconcile:raise
                client.reconcile_generation(context_operation)
                version=base.prepare_pack(**options)
            receipt=client.journal.read(context_operation).get('receipt',{})
            if receipt.get('model_contract_id')!=connection['model_contract_id']:
                raise ValueError('prepared root receipt differs from the pinned model contract')
            append_event(state,'COW_ROOT_DURABLE',operation_id=context_operation,snapshot=version.snapshot)
            offer=base.catalog_entry(version,pack_path=context_pack,source_revision=args.source_revision,
                                     execution_profile_id=connection['execution_profile_id'],capacity=args.capacity)
            _publish(state,'base-catalog.json',[offer])
            append_event(state,'CATALOG_DURABLE',base_id=offer['base_id'],snapshot=version.snapshot)
            return 0,dict(status='PREPARED',catalog=str(state/'base-catalog.json'),base_id=offer['base_id'],snapshot=version.snapshot,
                          canonical_input_cells=offer['prefix_tokens'],operation_id=args.operation_id,
                          context_operation=context_operation,source_receipt_sha256=source_receipt_sha256,
                          scope='Prepared reference root; no generated answer or residency guarantee')
        except OperationIndeterminate as exc:
            append_event(state,'UNRESOLVED',namespace_operation=namespace_operation,context_operation=context_operation)
            return 4,dict(status='UNRESOLVED',operation_id=args.operation_id,namespace_operation=namespace_operation,context_operation=context_operation,
                          error=str(exc),next_action='Keep this state and original arguments; inspect branchwrite context-status STATE. --reconcile recovers only a proven durable context result. Never use a new ID to retry unknown work.')

def _read_private_json(path):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
    with os.fdopen(fd,'rb') as stream:
        info=os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)!=0o600:
            raise ValueError('context receipt must be private and owned')
        raw=stream.read(8*1024*1024+1)
    if len(raw)>8*1024*1024:raise ValueError('context receipt exceeds size limit')
    return json.loads(raw)

def status_command(state,*,as_json=False):
    from .project_context import context_status
    result=context_status(state)
    state=Path(state).absolute()
    for filename,key in (('base-request.json','request'),('base-setup.json','setup')):
        path=state/filename
        if path.exists():result[key]=_read_private_json(path)
    setup=result.get('setup')
    request=result.get('request')
    operation_id=(setup or request or {}).get('operation_id')
    if operation_id:
        digest=hashlib.sha256(operation_id.encode()).hexdigest()[:40]
        journal=OperationJournal(state/'cow-operations')
        ops={}
        for label,suffix in (('namespace','namespace'),('context','context')):
            op='bw-base-'+suffix+'-'+digest
            record=journal.read(op)
            ops[label]={"operation_id":op,"state":None if record is None else record.get('state'),
                        "receipt":None if record is None else record.get('receipt')}
        result['cow_operations']=ops
    if as_json:
        print(json.dumps(result,sort_keys=True))
    else:
        print('Context build: '+result['phase'])
        print('State: '+str(result['state']))
        if result.get('project_file_count') is not None:print('Frozen project files: '+str(result['project_file_count']))
        if result.get('pack_id'):print('Pack: '+result['pack_id'])
        if result.get('catalog'):print('Catalog: '+result['catalog'])
        if result.get('last_events'):
            print('Last durable steps:')
            for event in result['last_events']:
                print('  '+event.get('phase','?')+' '+event.get('at',''))
        orphaned=result.get('orphaned_source_snapshots',[])
        if orphaned:
            if result['phase']=='SOURCE_SNAPSHOT_RECOVERY_CANDIDATE':
                print('A frozen project-context snapshot survived before its outer receipt was published.')
                print('Re-run the original code command with the same state and source selections; BranchWrite will verify and reuse the frozen inputs.')
            else:
                print('Several orphaned project-context snapshots need inspection; automatic recovery is ambiguous.')
        if result.get('cow_operations'):
            print('COW operations:')
            for label,record in result['cow_operations'].items():
                print('  '+label+': '+str(record['state'] or 'not started')+' ('+record['operation_id']+')')
    return 0
