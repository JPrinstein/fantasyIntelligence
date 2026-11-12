import json
import io
import os
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from benchmarks.gguf_backend import (find_server, launch_with_offload_fallback,
                                     request_body, server_command, tool_json_schema)
from benchmarks.run import check_registry


class GGUFBackendTests(unittest.TestCase):
    def test_model_command_is_local_only(self):
        config = {"ctx_size": 2048, "gpu_layers": 8,
                  "thinking": False, "thinking_template": True}
        command = server_command(config, "llama-server", "model.gguf", 53217)
        self.assertEqual(command[command.index("--host") + 1], "127.0.0.1")
        self.assertEqual(command[command.index("--n-gpu-layers") + 1], "8")
        self.assertEqual(json.loads(command[command.index("--chat-template-kwargs") + 1]),
                         {"enable_thinking": False})

    def test_constrained_json_is_explicit_profile(self):
        messages = [{"role": "user", "content": "test"}]
        case = {"kind": "planner"}
        self.assertNotIn("response_format", request_body({}, case, messages))
        constrained = request_body({"json_mode": True}, case, messages)
        self.assertEqual(constrained["response_format"]["type"], "json_schema")
        self.assertEqual(constrained["response_format"]["schema"], tool_json_schema())
        self.assertNotIn("response_format", request_body({"json_mode": True}, {"kind": "answer"}, messages))

    def test_missing_binary_has_clear_error(self):
        with patch.dict(os.environ, {"LLAMA_SERVER_BIN": "/nonexistent/llama-server"}):
            with self.assertRaisesRegex(RuntimeError, "does not exist"):
                find_server()

    def test_failed_full_offload_retries_partial(self):
        failed = Mock()
        failed.poll.return_value = None
        working = Mock()
        with patch("benchmarks.gguf_backend.reserve_port", side_effect=[11000, 12000]), \
             patch("benchmarks.gguf_backend.subprocess.Popen", side_effect=[failed, working]), \
             patch("benchmarks.gguf_backend.wait_for_server", side_effect=[RuntimeError("GPU OOM"), None]):
            server, url, layers = launch_with_offload_fallback(
                {"gpu_layers": 99}, "llama-server", "model.gguf", io.StringIO())
        self.assertIs(server, working)
        self.assertEqual(layers, 24)
        self.assertEqual(url, "http://127.0.0.1:12000")
        failed.terminate.assert_called_once()

    def test_registry_has_overnight_selection_and_verified_filenames(self):
        models = json.loads((Path(__file__).parent / "models.json").read_text(encoding="utf-8"))
        check_registry(models)
        overnight = [m for m in models["models"] if m.get("overnight")]
        self.assertGreaterEqual(len(overnight), 10)
        self.assertTrue(any("moonlight" in m["name"] for m in overnight))
        self.assertTrue(all(m["backend"] != "gguf" or m["filename"].endswith(".gguf")
                            for m in overnight))


if __name__ == "__main__":
    unittest.main()
