"""Directory-first interactive launcher using the existing saved COW connection."""
import asyncio
import getpass
from hashlib import sha256
import json
import os
from pathlib import Path
import socket
import sys
from .client_setup import connection_path, read_connection, saved_api_key, command as connect_command, connect
from .guided_cli import _temporary_api_key
from .interactive_session import SessionService
from .interactive_terminal import Terminal


def run(*, project=None, state=None, save_api=False, sampler="greedy",cad_config=None,blender_config=None):
    if cad_config is not None and blender_config is not None:raise ValueError('choose one fixed domain per session')
    if not sys.stdin.isatty():
        print('Open a terminal inside your project folder, then run branchwrite session.')
        return 2
    project=Path.cwd() if project is None else Path(project)
    project=project.resolve(strict=True)
    if not project.is_dir():raise ValueError('Choose a project directory')
    # A normal first terminal opens in HOME. Refuse before asking for a key or
    # collecting files: default saved sessions must live outside the project.
    proposed=(Path(state).absolute() if state is not None else
        Path(os.environ.get('XDG_STATE_HOME',str(Path.home()/'.local/state')))/'branchwrite/sessions')
    if proposed.resolve().is_relative_to(project):
        print('Choose a project folder inside your home folder, then run BW there.')
        print('For a new project, type: mkdir -p ~/my-project && cd ~/my-project')
        print('Then type: ~/.local/bin/bw')
        return 2
    print('BranchWrite')
    print('Client: '+socket.gethostname()+' | Project: '+str(project))
    print('Project files stay on this client. Model requests go to your configured COW server.')
    saved=connection_path(Path.home(),os.environ);keys=[]
    if not saved.exists():
        if os.environ.get('BW_COW_CONNECTION'):raise ValueError('The selected connection file is missing')
        code=connect_command(home=Path.home(),environ=os.environ,input_fn=input,
            secret_fn=getpass.getpass,output_fn=print,save_api=save_api,on_key=keys.append)
        if code:return code
    connection=read_connection(saved)
    key=os.environ.get('BW_COW_API_KEY') or (keys[0] if keys else None) or saved_api_key(saved)
    if not key:key=getpass.getpass('COW API key (kept in memory): ').strip()
    if not key:raise ValueError('A server API key is required')
    if save_api and not keys:connect(connection['endpoint_url'],key,save_api=True)
    if state is None:
        root=Path(os.environ.get('XDG_STATE_HOME',str(Path.home()/'.local/state')))/'branchwrite/sessions'
        root.mkdir(mode=0o700,parents=True,exist_ok=True)
        identity=sha256((str(project)+json.dumps(connection,sort_keys=True)).encode()).hexdigest()[:24]
        state=root/('project-'+identity)
    print('Saved session: '+str(state))
    print('New requests use '+sampler+' sampling; admitted work keeps its saved settings.')
    from .remote_config import client_targets
    remotes=client_targets()
    if remotes:print('Remote administration available in Work mode: '+', '.join(sorted(remotes)))
    options={}
    from .run_cli import _pairs
    for kind,path in (('cad',cad_config),('blender',blender_config)):
        if path is not None:options[kind]=json.loads(Path(path).read_text(),object_pairs_hook=_pairs)
    if options:print('New Work requests use '+next(iter(options))+' inspection. Plan, Chat and Aside stay read-only. Saved workflows retain their admitted configuration.')
    with _temporary_api_key(key):
        return asyncio.run(Terminal(SessionService(project,state,connection,remotes=remotes,sampler=sampler,**options),state).run())
