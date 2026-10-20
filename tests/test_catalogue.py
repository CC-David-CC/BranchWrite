import ast, csv, hashlib, unittest, tomllib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(p):return tomllib.loads((ROOT/p).read_text())
class CatalogueTests(unittest.TestCase):
    def setUp(self):
        self.cases=load('acceptance/cases.toml')['case'];self.tickets=load('acceptance/tickets.toml')['ticket']
    def test_original_211_retained(self):self.assertEqual(sum(c['id'].startswith('BW-') for c in self.cases),211)
    def test_new_128_present(self):self.assertEqual(sum(c['id'].startswith('BW3-') for c in self.cases),128)
    def test_ids_unique(self):self.assertEqual(len({c['id'] for c in self.cases}),len(self.cases))
    def test_no_product_pass_claim(self):self.assertEqual({c['status'] for c in self.cases},{'not_run'})
    def test_tickets_unstarted(self):self.assertEqual({t['status'] for t in self.tickets},{'not_started'})
    def test_tickets_acyclic(self):
        deps={t['id']:set(t['depends_on']) for t in self.tickets};done=set()
        while len(done)<len(deps):
            ready={k for k,v in deps.items() if k not in done and v<=done}
            self.assertTrue(ready);done.update(ready)
    def test_case_ownership_exact(self):
        for t in self.tickets:self.assertEqual(set(t['case_ids']),{c['id'] for c in self.cases if c['ticket']==t['id']})
    def test_migration_covers_source_ids(self):
        with (ROOT/'acceptance/migration.tsv').open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
        self.assertEqual({r['case_id'] for r in rows},{c['id'] for c in self.cases if c['id'].startswith('BW-')})
    def test_spec_digest_bound(self):self.assertEqual(load('acceptance/cases.toml')['spec_sha256'],hashlib.sha256((ROOT/'spec/BW_FIRST_PRINCIPLES_v0.6.md').read_bytes()).hexdigest())
    def test_source_zip_digest_bound(self):self.assertEqual(load('validation/source-audit.toml')['source_zip_sha256'],hashlib.sha256((ROOT/'provenance/branchwrite-codex-handoff-v0.2.0.zip').read_bytes()).hexdigest())
    def test_mirostat_and_adaptive_have_no_algorithm_dependency(self):
        byid={t['id']:t for t in self.tickets}
        self.assertNotIn('R20',byid['R21']['depends_on']);self.assertEqual(byid['R20']['depends_on'],byid['R21']['depends_on'])
    def test_single_selector_profiles(self):
        for p in load('configs/profiles.toml')['profile']:
            self.assertEqual(sum(x in {'greedy','dist','mirostat2','adaptive_p'} for x in p['stages']),1)
            self.assertEqual(p['stages'][-1],p['selector'])
    def test_minimal_explore_not_redundantly_filtered(self):
        p=next(p for p in load('configs/profiles.toml')['profile'] if p['name']=='explore')
        self.assertNotIn('top_k',p['stages']);self.assertNotIn('top_p',p['stages'])
    def test_unbound_native_profile(self):self.assertEqual(load('configs/native.unbound.toml')['status'],'UNBOUND')
    def test_active_python_has_no_pickle(self):
        # JSON import/file bans retired by the owner on 2026-10-17. Keep the
        # pre-existing pickle assertion independently; it is unrelated to JSON.
        for p in ROOT.rglob('*.py'):
            for node in ast.walk(ast.parse(p.read_text())):
                if isinstance(node,ast.Import):self.assertNotIn('pickle',{a.name.split('.')[0] for a in node.names})
                elif isinstance(node,ast.ImportFrom):self.assertNotEqual((node.module or '').split('.')[0],'pickle')
