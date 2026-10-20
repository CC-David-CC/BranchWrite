"""COW CLI/HTTP must load the same actual canonical structured prompt."""
import unittest

import test_cow_client_flow as fixture


class StructuredClientTests(unittest.TestCase):
    def setUp(self):
        self.case = fixture.CowClientFlowTests()
        self.addCleanup(self.case.doCleanups)
        self.case.setUp()

    def test_actual_cli_and_http_load_equal_canonical_tokens_and_message_roles(self):
        from serve.test_cow_presentation_flow import render
        messages = [dict(role='system', content='The current goal is verified work.'),
                    dict(role='user', content='Observed hash abc.\nSnowman \u2603'),
                    dict(role='assistant', content='A proposal has no grant.')]
        histories = []
        for transport in ('http', 'cli'):
            client = self.case._client(transport, 'structured-' + transport)
            namespace = client.create_namespace('Structured', 'structured-ns-' + transport)['namespace_id']
            result = client.load_context('structured-' + transport, namespace, messages,
                                         'structured-load-' + transport)
            tokens = self.case.coordinator.store.lineage(result.receipt.snapshot)[1]
            histories.append(tokens)
            self.assertEqual(tuple(tokens), tuple(render(messages, add_generation_prompt=False).encode()))
            projected = client.history('structured-' + transport).messages
            self.assertEqual([(item['role'], item['text']) for item in projected],
                             [(item['role'], item['content']) for item in messages])
        self.assertEqual(histories[0], histories[1])


if __name__ == '__main__':
    unittest.main()
