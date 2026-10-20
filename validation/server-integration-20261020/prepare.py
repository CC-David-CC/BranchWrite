"""Prepare an isolated serving profile; no GPU job or service mutation."""
from pathlib import Path
import copy,hashlib,json,os,subprocess,sys,shutil,time
out=Path(__file__).parent;live=Path('/home/dflanag3/spatial-artifacts/branchwrite-dev29-live-q4-20261020')
oldroot=Path('/home/dflanag3/src/context-cow-client-setup-20261020');newroot=Path('/home/dflanag3/src/context-cow-consumed-pause-20261020')
assert not subprocess.check_output(['git','status','--porcelain'],cwd=newroot),'candidate source must be clean'
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=newroot,text=True).strip();assert commit.startswith('780e824a')
profile=json.loads((live/'profile.json').read_text());prior=copy.deepcopy(profile)
tracked=subprocess.check_output(['git','ls-files','-z'],cwd=newroot).decode().split('\0')
prefixes=('serve/','tools/','experimental/branching_context/src/','experimental/branching_context/scripts/')
files={name:hashlib.sha256((newroot/name).read_bytes()).hexdigest() for name in tracked if name.endswith('.py') and name.startswith(prefixes)}
assert 0<len(files)<=4096
for declared in prior['native_build']['selected_runtime_source_closure']['files_sha256']:
 parts=Path(declared.replace('\\','/')).parts
 positions=[parts.index(m) for m in ('serve','experimental','tools') if m in parts];assert positions
 suffix=Path(*parts[min(positions):]).as_posix();assert suffix in files,('dropped previously declared source',suffix)
profile['native_build']['selected_runtime_source_closure']=dict(source_commit=commit,files_sha256=files)
sha={}
for name,digest in profile['native_build']['sha256'].items():
 path=Path(name)
 if path.is_relative_to(oldroot):path=newroot/path.relative_to(oldroot)
 actual=hashlib.sha256(path.read_bytes()).hexdigest()
 if not path.is_relative_to(newroot):assert actual==digest,('native/external helper changed',str(path))
 sha[str(path)]=actual
profile['native_build']['sha256']=sha
profile['gguf_reader']=str(newroot/'tools/gguf_reader.py')
profile['calibration_status']='CLI_CANDIDATE_PENDING_COMPLETE_WORKFLOW_VALIDATION'
for key in list(os.environ):
 if key.startswith(('STRATA_','CUDA_','NVIDIA_','GGML_')):os.environ.pop(key)
os.environ.update(profile['execution']['environment'])
sys.path[:0]=[str(newroot/'experimental/branching_context/src'),str(newroot/'experimental/branching_context/scripts'),str(newroot/'tools'),str(newroot),'/home/dflanag3/spatial-artifacts/grammar-first-20261016-v1/deps']
from context_time_travel.strata_backend import _digest,_validate_execution,_validate_model,verify_runtime_source_closure
profile['execution_profile_id']=_digest(dict(build=profile['native_build'],execution=profile['execution'],hardware=profile['hardware']))
assert profile['execution_profile_id']!=prior['execution_profile_id']
assert profile['execution']==prior['execution'];assert profile['model_contract']==prior['model_contract'];assert profile['model_contract_id']==prior['model_contract_id']
_validate_execution(profile);model=_validate_model(profile);closure=verify_runtime_source_closure(profile)
trial=out/'server';trial.mkdir(mode=0o700)
(trial/'profile.json').write_text(json.dumps(profile,indent=2)+'\n');(trial/'profile.json').chmod(0o600)
for name in ['vision-config.json','api-key.txt']:shutil.copy2(live/name,trial/name);(trial/name).chmod(0o600)
report=dict(status='PREFLIGHT_PASS_NO_GPU_STARTED',source_root=str(newroot),source_commit=commit,profile_id=profile['execution_profile_id'],prior_profile_id=prior['execution_profile_id'],model_contract_id=profile['model_contract_id'],source_closure=closure,model_validation=model,native_executable_sha256=hashlib.sha256(Path(profile['execution']['sut_command'][0]).read_bytes()).hexdigest(),native_options_unchanged=True,vision_config_sha256=hashlib.sha256((trial/'vision-config.json').read_bytes()).hexdigest(),store_exists=(trial/'store').exists(),timestamp=time.time())
(out/'preflight.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
