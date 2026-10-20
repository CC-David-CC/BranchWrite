"""New client connection + code/resume against COW's actual CPU HTTP stack.

No language model or GPU is used. This covers setup/admission/receipt wiring.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest


class ClientSetupCowTests(unittest.TestCase):
    def test_connect_then_code_and_resume_use_saved_key_and_frozen_profile(self):
        from test_thinking_grammar import ThinkingTokenizer
        from serve.test_cow_grammar_canonical_flow import GrammarCPUBackend, _render, _encode, _initial_root_mode
        from context_time_travel.real import BranchingModel
        from context_time_travel.coordinator import ContextCoordinator
        from context_time_travel.pools import PoolConfig
        from serve.cow_adapter import CowAdapter
        from serve.cow_text_adapter import CowTextAdapter
        from serve.cow_grammar_disk import DurableGrammarCatalog
        from serve.cow_http import make_server
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        base = Path(temp.name)
        tokenizer = ThinkingTokenizer()
        profile = dict(model_contract_id="a"*64, execution_profile_id="b"*64, model_weights_sha256="c"*64,
                       execution=dict(GPU=[0], resume_contract="identical-native-operators-v1",
                                      generated_operator="normal-verifier-decode", selected_token_protocol="consumed-selected-receipt-v1",
                                      native_request_protocol="consumed-greedy-ack-v1", prefill_chunk=16, capacity=131072, eos_tokens=[256]))
        def factory(gpu):
            return BranchingModel(base / "store", GrammarCPUBackend(profile, tokenizer), profile)
        coordinator = ContextCoordinator(base / "store", PoolConfig(gpus=(0,), ram_bytes=64*1024**2,
            disk_bytes=256*1024**2, min_available_bytes=0), factory)
        self.addCleanup(coordinator.close)
        coordinator.ready(5)
        adapter = CowAdapter(coordinator)
        text = CowTextAdapter(adapter, tokenizer, _render,
            lambda messages, rendered, add_generation_prompt:_encode(tokenizer, messages, rendered, add_generation_prompt),
            initial_root_mode=_initial_root_mode, renderer_id="d"*64)
        catalog = DurableGrammarCatalog(base / "grammars", tokenizer, [256])
        self.addCleanup(catalog.close)
        server = make_server(adapter, api_key="integration-secret", text_adapter=text, grammar_catalog=catalog,
                             connection_info=dict(model_contract_id=profile["model_contract_id"],
                                                  execution_profile_id=profile["execution_profile_id"], eos_tokens=[256]))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 5)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        env = dict(os.environ, HOME=str(base), XDG_CONFIG_HOME=str(base / "config"))
        env.pop("BW_COW_CONNECTION", None)
        env.pop("BW_COW_API_KEY", None)
        def cli(*args, key=None):
            selected = dict(env)
            if key: selected["BW_COW_API_KEY"] = key
            return subprocess.run([sys.executable, "-m", "branchwrite", *map(str,args)], env=selected,
                                  capture_output=True, text=True, timeout=45)
        connected = cli("connect", "http://127.0.0.1:" + str(server.server_port), "--save-api", key="integration-secret")
        self.assertEqual(connected.returncode, 0, connected.stdout + connected.stderr)
        self.assertEqual(coordinator.store.branches(), ())
        project = base / "project"
        project.mkdir()
        (project / "app.py").write_text('print("unchanged")\n')
        state = base / "run"
        config_path = base / "config" / "branchwrite" / "connection.json"
        admitted = cli("code", project, "--task", "Inspect the project and check it.", "--connection", config_path,
                       "--state", state, "--branch", "setup-client", "--read", "app.py",
                       "--test-command", "python3 -m unittest", "--max-steps", "1")
        self.assertEqual(admitted.returncode, 3, admitted.stdout + admitted.stderr)
        before = (state / "coding-launch.json").read_bytes()
        self.assertNotIn(b"integration-secret", before)
        self.assertEqual(coordinator.store.head("setup-client").revision, 1)
        resumed = cli("resume", state, "--max-steps", "1")
        self.assertEqual(resumed.returncode, 3, resumed.stdout + resumed.stderr)
        self.assertEqual((state / "coding-launch.json").read_bytes(), before)
        self.assertEqual((project / "app.py").read_text(), 'print("unchanged")\n')
        records = [json.loads(p.read_text()) for p in (state / "cow-operations").glob("*.json")]
        self.assertTrue(any(r["path"] == "/cow/grammars" and r["state"] == "complete" for r in records))
        self.assertTrue(any(r["path"] == "/cow/text/context" and r["state"] == "complete" for r in records))
        self.assertFalse(json.loads(admitted.stdout)["verified"])
        self.assertFalse(json.loads(resumed.stdout)["verified"])


if __name__ == "__main__":
    unittest.main()
