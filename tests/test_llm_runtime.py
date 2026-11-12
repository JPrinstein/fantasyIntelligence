import os
import unittest
from unittest.mock import patch

from llm import runtime


class RuntimeTests(unittest.TestCase):
    def test_default_backend(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(runtime.backend(), 'gguf')

    def test_legacy_fallback(self):
        with patch.dict(os.environ, {'FANTASY_LLM_BACKEND': 'transformers'}):
            self.assertEqual(runtime.backend(), 'transformers')

    def test_json_only_for_planner(self):
        messages = [{'role': 'user', 'content': 'hello'}]
        with patch.dict(os.environ, {'FANTASY_LLM_BACKEND': 'gguf'}):
            with patch.object(runtime, '_gguf_chat', return_value='ok') as fake:
                self.assertEqual(runtime.generate_chat(messages, json_mode=True), 'ok')
                self.assertTrue(fake.call_args.kwargs['json_mode'])
                runtime.generate_chat(messages)
                self.assertFalse(fake.call_args.kwargs['json_mode'])

    def test_schema(self):
        schema = runtime.planner_schema()
        self.assertIn('tools', schema['required'])
        self.assertEqual(schema['properties']['tools']['type'], 'array')

    def test_absent_model_error_before_server(self):
        with patch.dict(os.environ, {'FANTASY_GGUF_PATH': '/not/a/model.gguf'}):
            with self.assertRaises(FileNotFoundError):
                runtime._start_server()

    def test_planner_uses_constrained_and_answer_uses_normal(self):
        from agent import planner
        from llm import generator
        with patch('agent.planner.generate_chat', return_value='{"tools": []}') as fake_plan:
            self.assertEqual(planner.create_plan('hello'), {'tools': []})
            self.assertTrue(fake_plan.call_args.kwargs['json_mode'])
        with patch('llm.generator.generate_chat', return_value='Hello') as fake_answer:
            self.assertEqual(generator.generate_answer('hi', ''), 'Hello')
            self.assertFalse(fake_answer.call_args.kwargs['json_mode'])

    def test_league_rule_our_league(self):
        from agent.planner import enforce_required_tools
        plan = {'tools': [{'tool': 'rag_search', 'args': {'query': 'QB'}}]}
        result = enforce_required_tools('Why does rushing matter in our league?', plan)
        self.assertEqual({x['tool'] for x in result['tools']}, {'league_context', 'rag_search'})

    def test_bad_plan_not_auto_executed(self):
        from agent.planner import enforce_required_tools
        plan = {'tools': [], 'error': 'Planner returned invalid JSON'}
        self.assertEqual(enforce_required_tools('hello', plan), plan)


if __name__ == '__main__':
    unittest.main()
