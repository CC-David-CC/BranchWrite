"""Opt-in real native CPU PCC jobs driven by BW's actual lesson CLI.

BW owns the client journal; PCC owns lessons, updates, moments and models.
"""
from pathlib import Path
import argparse,json,os,subprocess,sys,threading,time

def run(pcc, executable, output):
    pcc=Path(pcc).resolve();sys.path[:0]=[str(pcc),str(pcc/'experimental/branching_context/src')]
    from experimental.native_training.make_llama_fixture import make_fixture
    from tools.pcc_lessons import LessonService,NativeRunner
    from tools.pcc_native_training import sha256
    from tools.pcc_optimizer_profiles import identity
    from serve.cow_http import make_server
    root=Path(output);root.mkdir(mode=0o700,parents=True,exist_ok=False)
    model=make_fixture(root/'base.gguf');base=sha256(model)
    cases=[]
    for optimizer in ('adamw','muon'):
        directory=root/optimizer;directory.mkdir()
        profile=dict(schema=1,title='Owned BW '+optimizer+' CPU workflow fixture',
            optimizer=optimizer,learning_rate=.001,optimizer_settings=dict(schema=1),
            state_policy='fresh',training_budget_seconds=1e-12)
        profile_id=identity(profile)
        config=dict(model=str(model),base_sha256=base,executable=str(executable),
            devices=['CPU'],device_budget_bytes={'CPU':4<<30},reserve_bytes=128<<20,
            host_reserve_bytes=128<<20,gpu_uuids=[],sequence_profile='dense-llama-short-v1',
            memory_profile='allocator-v1',timeout_seconds=60,optimizer_profiles={profile_id:profile})
        service=LessonService(directory/'store','a'*64,lambda text:[int(c) for c in text],
            NativeRunner(config),max_tokens=512,max_steps=8,sequence_profile='dense-llama-short-v1')
        server=make_server(object(),api_key='owned-tiny-fixture',training_service=service)
        thread=threading.Thread(target=server.serve_forever);thread.start()
        try:
            connection=directory/'connection.json'
            connection.write_text(json.dumps(dict(endpoint_url='http://127.0.0.1:'+str(server.server_port),
                endpoint_pin='owned-bw-fixture',model_contract_id='a'*64,
                execution_profile_id='c'*64,eos_tokens=[7])))
            env=dict(os.environ,BW_COW_API_KEY='owned-tiny-fixture')
            command=[sys.executable,'-m','branchwrite','lesson','--connection',str(connection),
                '--state-dir',str(directory/'journal')]
            def cli(*args,expect=0):
                result=subprocess.run([*command,*args],capture_output=True,text=True,env=env,timeout=30)
                assert result.returncode==expect,(args,result.stdout,result.stderr)
                return json.loads(result.stdout) if expect==0 else result.stdout
            profiles=cli('optimizers');assert profiles['profiles'][0]['id']==profile_id
            docs=[];ids=[]
            for index,(prompt,completion) in enumerate([('01','234'),('12','345')]):
                lesson=dict(schema=1,title='Owned BW CPU example '+str(index),model_contract_id='a'*64,
                    prompt=prompt,completion=completion,rationale='Synthetic mechanics fixture',
                    scope='owned-training',evidence=dict(method='host-verified-correction-v1',
                    failed_result_sha256='b'*64,corrected_result_sha256='c'*64,verification_sha256='d'*64))
                path=directory/('lesson-'+str(index)+'.json');path.write_text(json.dumps(lesson));docs.append(path)
            first=cli('submit',str(docs[0]),'--operation-id','single','--train-now','--mode','full',
                '--steps','4','--learning-rate','.001','--optimizer-profile-id',profile_id)
            ids.append(first['lesson']['lesson_id'])
            ids.append(cli('submit',str(docs[1]),'--operation-id','second')['lesson_id'])
            def wait(job):
                end=time.monotonic()+60
                while time.monotonic()<end:
                    value=service.job(job)
                    if value['state'] not in ('running','queued'):
                        assert value['state']=='complete',value
                        return value
                    time.sleep(.02)
                raise TimeoutError('Original PCC job unresolved; no second request')
            a=wait('single-train')
            assert a['optimizer']==optimizer and a['optimizer_completed_steps']==1
            assert a['selected_lessons']==1
            first_candidate=service._read(service.root/'operations/single-train.json')['candidate']
            train=['train',*ids,'--operation-id','batch','--mode','full','--batch-size','1','--steps','4',
                '--learning-rate','.001','--parent-job-id','single-train','--optimizer-profile-id',profile_id]
            receipt=cli(*train);b=wait('batch')
            assert cli(*train)==receipt
            assert b['selected_lessons']==2 and b['consumed_example_presentations']==1
            assert b['unconsumed_lesson_ids_this_job']==ids[1:]
            candidate=service._read(service.root/'operations/batch.json')['candidate']
            assert candidate['base_sha256']==first_candidate['candidate_sha256']
            assert b['optimizer_completed_steps']==1 and b['optimizer_state_policy']=='fresh'
            notes=directory/'notes.txt';notes.write_text('Tiny CPU workflow proof, not model quality.\n')
            save=['preserve','batch','--operation-id','preserve','--name','Owned-'+optimizer,
                '--expected-sha256',candidate['candidate_sha256'],'--notes-file',str(notes),
                '--report-sha256','e'*64]
            saved=cli(*save);assert cli(*save)==saved
            exports=cli('exports')['exports'];assert len(exports)==1 and exports[0]['weights_published'] is False
            target=service.root/'exports'/('Owned-'+optimizer+'.gguf')
            assert sha256(target)==candidate['candidate_sha256']
            assert target.stat().st_ino==Path(candidate['candidate_path']).stat().st_ino
            assert 'full-weight' in cli('train',ids[0],'--operation-id','bad-mode','--optimizer-profile-id',profile_id,expect=2)
            assert 'legacy skill guard' in cli('train',ids[0],'--operation-id','bad-guard','--mode','full',
                '--skill-guard','--optimizer-profile-id',profile_id,expect=2)
            assert '--train-now' in cli('submit',str(docs[0]),'--operation-id','bad-submit',
                '--mode','full','--optimizer-profile-id',profile_id,expect=2)
            cases.append(dict(optimizer=optimizer,status='PASS',actual_native_cpu_jobs=2,
                single_example_and_batched_selection=True,parent_weights_kept_with_fresh_moments=True,
                actual_consumption_exposed=True,duplicate_job_not_retrained=True,
                private_named_export_idempotent=True,no_model_upload=True))
        finally:
            server.shutdown();server.server_close();thread.join();service.close()
    assert sha256(model)==base
    result=dict(schema=1,status='PASS',scope='Real tiny CPU native PCC execution through BW CLI, not full-model learning',
        cases=cases,cli_refusal_cases=6,weights_published=False,promoted=False)
    (root/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pcc-root',required=True,type=Path)
    parser.add_argument('--native-executable',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();print(json.dumps(run(args.pcc_root,args.native_executable,args.output)))
