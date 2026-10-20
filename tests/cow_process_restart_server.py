from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import threading

base = Path(sys.argv[1])
port = int(sys.argv[2])
ready_path = Path(sys.argv[3])
counter_path = Path(sys.argv[4])

from context_time_travel.coordinator import ContextCoordinator
from context_time_travel.pools import PoolConfig
from serve.cow_adapter import CowAdapter
from serve.cow_http import make_server
from serve.cow_text_adapter import CowTextAdapter
from serve.cow_workspace import CowWorkspace
from serve.test_cow_presentation_flow import (
    ByteTokenizer, FlowModel, append_initial_user_suffix, append_user_suffix,
    encode, initial_root_mode, render,
)

def persist(delta):
    try:
        state = json.loads(counter_path.read_text())
    except FileNotFoundError:
        state = {"forward_tokens": 0}
    state["forward_tokens"] += delta
    tmp = counter_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, sort_keys=True))
    os.replace(tmp, counter_path)

tokens = ByteTokenizer()
gate = threading.Event()
gate.set()
config = PoolConfig(gpus=(0,), ram_bytes=1024 * 1024, disk_bytes=8 * 1024 * 1024,
                    min_available_bytes=0)

def factory(gpu):
    model = FlowModel(base / "store", gpu, (0,), [], gate)
    model.plans["process-answer"] = (257, 299)
    model.plans["post-restart-user"] = (260, 299)
    original_create = model.create
    def create(ids):
        before = model.stats["forward_tokens"]
        result = original_create(ids)
        persist(model.stats["forward_tokens"] - before)
        return result
    model.create = create
    original_run = model.run_greedy_request
    def run(*args, **kwargs):
        before = model.stats["forward_tokens"]
        result = original_run(*args, **kwargs)
        persist(model.stats["forward_tokens"] - before)
        return result
    model.run_greedy_request = run
    return model

coordinator = ContextCoordinator(base / "store",
    config, factory)
coordinator.ready(5)
adapter = CowAdapter(coordinator)
text = CowTextAdapter(adapter, tokens, render, encode,
    append_user_suffix=append_user_suffix,
    append_initial_user_suffix=append_initial_user_suffix,
    initial_root_mode=initial_root_mode, renderer_id="c" * 64)
workspace = CowWorkspace(coordinator.store, tokens,
                          root_mode_resolver=text.root_mode_for_projection)
server = make_server(adapter, host="127.0.0.1", port=port, api_key="process-restart-key",
                     text_adapter=text, workspace=workspace)
ready_path.write_text(json.dumps({"port": server.server_port, "pid": os.getpid()}))
try:
    server.serve_forever()
finally:
    server.server_close()
    coordinator.close()

