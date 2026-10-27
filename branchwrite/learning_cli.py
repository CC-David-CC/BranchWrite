"""Human/agent controls for PCC-owned learning rounds; no local loop runtime."""
from pathlib import Path
import argparse,json
from .lesson_cli import _client


def main(argv=None,*,output=print,connection_override=None):
    parser=argparse.ArgumentParser(prog='branchwrite learning',description=__doc__)
    parser.add_argument('--connection',type=Path);parser.add_argument('--state-dir',type=Path)
    sub=parser.add_subparsers(dest='action',required=True)
    sub.add_parser('policies');sub.add_parser('list')
    p=sub.add_parser('status');p.add_argument('run_id')
    p=sub.add_parser('round');p.add_argument('run_id');p.add_argument('round_index',type=int)
    p=sub.add_parser('drive',help='Follow advertised actions until one round settles or owner input is needed')
    p.add_argument('run_id');p.add_argument('--operation-prefix',required=True)
    p.add_argument('--lesson-id',action='append',default=[])
    p.add_argument('--maximum-transitions',type=int,default=16)
    p.add_argument('--maximum-seconds',type=int,default=300)
    p=sub.add_parser('start');p.add_argument('--operation-id',required=True);p.add_argument('--policy-id',required=True)
    p.add_argument('--parent-job-id');p.add_argument('--expected-parent-sha256')
    for action in ('advance','reconcile','stop','preserve'):
        p=sub.add_parser(action);p.add_argument('run_id');p.add_argument('--operation-id',required=True)
        p.add_argument('--revision',type=int,help='Default: current revision; retries retain the original request revision')
        if action=='advance':p.add_argument('lesson_ids',nargs='*')
        if action=='preserve':p.add_argument('--name',required=True);p.add_argument('--notes-file',type=Path)
    args=parser.parse_args(argv)
    from .cow_client import CowClientError
    try:
        connection,client=_client(args,connection_override)
        if args.action=='policies':value=client.training_read('learning-policies')
        elif args.action=='list':value=client.training_read('learning-runs')
        elif args.action=='status':value=client.training_read('learning-runs',args.run_id)
        elif args.action=='round':value=client.training_read('learning-runs',args.run_id,round_index=args.round_index)
        elif args.action=='drive':
            from .learning_drive import drive
            value=drive(client,args.run_id,connection['model_contract_id'],operation_prefix=args.operation_prefix,
                lesson_ids=args.lesson_id,maximum_transitions=args.maximum_transitions,maximum_seconds=args.maximum_seconds)
        elif args.action=='start':
            value=client.training_submit('learning-runs',dict(policy_id=args.policy_id,parent_job_id=args.parent_job_id,
                expected_parent_sha256=args.expected_parent_sha256),args.operation_id)
        else:
            prior=client.journal.read(args.operation_id)
            if prior is not None and prior['path']!='/cow/training/learning-steps':raise ValueError('Operation belongs to another request')
            frozen=json.loads(client.journal.decode_body(prior)) if prior is not None else None
            revision=(args.revision if args.revision is not None else frozen['expected_revision'] if frozen is not None
                else client.training_read('learning-runs',args.run_id)['revision'])
            body=dict(run_id=args.run_id,expected_revision=revision,action=args.action)
            if args.action=='advance' and args.lesson_ids:body['lesson_ids']=args.lesson_ids
            if args.action=='preserve':body.update(name=args.name,notes='' if args.notes_file is None else args.notes_file.read_text())
            value=client.training_submit('learning-steps',body,args.operation_id)
        if 'model_contract_id' in value and value['model_contract_id']!=connection['model_contract_id']:
            raise ValueError('Learning response belongs to another model contract')
        output(json.dumps(value,sort_keys=True));return 0
    except (ValueError,OSError,RuntimeError,KeyError,CowClientError) as error:
        output('branchwrite learning: '+str(error));return 2


if __name__=='__main__':raise SystemExit(main())
