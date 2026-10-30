"""Výpočet i celý HTTP průchod SDK se testují bez spojení s poskytovatelem."""

import json
import io
import unittest
from contextlib import redirect_stdout
from decimal import Decimal
from unittest.mock import patch

import httpx
from openai import OpenAI

from main import DEFAULT_QUESTION, MAX_API_CALLS, execute_tool, run_assistant
from pricing import spocitej_cenu
from demo import main as run_demo


def tool_call(arguments: dict, call_id: str = "call_test") -> dict:
    return {
        "id": "fc_" + call_id, "type": "function_call", "status": "completed",
        "call_id": call_id, "name": "spocitej_cenu", "arguments": json.dumps(arguments),
    }


def message(text: str) -> dict:
    return {
        "id": "msg_test", "type": "message", "role": "assistant", "status": "completed",
        "content": [{"type": "output_text", "text": text, "annotations": []}],
    }


class PricingTests(unittest.TestCase):
    def test_example(self):
        result = spocitej_cenu(850, 12, 8)
        self.assertEqual(result["cena_pred_slevou_kc"], "10200.00")
        self.assertEqual(result["sleva_kc"], "816.00")
        self.assertEqual(result["celkem_kc"], "9384.00")

    def test_halere_and_commercial_rounding(self):
        self.assertEqual(spocitej_cenu(0.1, 3, 0)["celkem_kc"], "0.30")
        self.assertEqual(spocitej_cenu(Decimal("0.05"), 1, 10)["sleva_kc"], "0.01")
        self.assertEqual(spocitej_cenu(Decimal("0.05"), 1, 10)["celkem_kc"], "0.04")

    def test_full_discount(self):
        self.assertEqual(spocitej_cenu(850, 12, 100)["celkem_kc"], "0.00")

    def test_reject_invalid_values(self):
        for args in [(-1, 12, 8), (850, 0, 8), (850, 1.5, 8), (850, True, 8),
                     (850, 12, 101), (850, 12, -1), (True, 12, 8),
                     (float("nan"), 12, 8), (float("inf"), 12, 8),
                     (850.001, 12, 8), ("850", 12, 8)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                spocitej_cenu(*args)

    def test_tool_rejects_unknown_name_and_malformed_arguments(self):
        self.assertFalse(execute_tool("eval", "{}")["ok"])
        for data in ["not json", "[]", "{}", '{"jednotkova_cena": NaN, "pocet_kusu": 1, "sleva_procent": 0}']:
            with self.subTest(data=data):
                self.assertFalse(execute_tool("spocitej_cenu", data)["ok"])


class ResponsesFlowTests(unittest.TestCase):
    def test_offline_demo_completes_and_marks_simulation(self):
        output = io.StringIO()
        with redirect_stdout(output):
            run_demo()
        self.assertIn("OFFLINE DEMO", output.getvalue())
        self.assertIn("Odpověď (simulovaná):", output.getvalue())
        self.assertIn("9384.00 Kč", output.getvalue())

    def make_client(self, replies: list) -> tuple:
        requests = []

        def handle(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.method, "POST")
            self.assertEqual(request.url.path, "/v1/responses")
            requests.append(json.loads(request.content))
            payload = replies[len(requests) - 1]
            return httpx.Response(200, json={
                "id": f"resp_{len(requests)}", "object": "response", "created_at": 0,
                "model": "offline-test", "status": "completed", **payload,
            })

        client = OpenAI(
            api_key="offline-placeholder", base_url="https://offline.example/v1",
            http_client=httpx.Client(transport=httpx.MockTransport(handle)), max_retries=0,
        )
        self.addCleanup(client.close)
        return client, requests

    @patch("builtins.print")
    def test_full_round_trip_preserves_history_reasoning_and_call_id(self, _print):
        reasoning = {"id": "rs_test", "type": "reasoning", "summary": [], "encrypted_content": "opaque-offline"}
        call = tool_call({"jednotkova_cena": 850, "pocet_kusu": 12, "sleva_procent": 8})
        client, requests = self.make_client([
            {"output": [reasoning, call]},
            {"output": [message("Zaplatíš 9384.00 Kč.")]},
        ])
        self.assertEqual(run_assistant(client, "offline-test", DEFAULT_QUESTION), "Zaplatíš 9384.00 Kč.")
        self.assertEqual(len(requests), 2)
        history = requests[1]["input"]
        self.assertEqual(history[0], {"role": "user", "content": DEFAULT_QUESTION})
        self.assertEqual(history[1]["encrypted_content"], "opaque-offline")
        self.assertEqual(history[2]["call_id"], "call_test")
        self.assertEqual(history[3]["type"], "function_call_output")
        self.assertEqual(history[3]["call_id"], "call_test")
        self.assertEqual(json.loads(history[3]["output"])["celkem_kc"], "9384.00")
        self.assertFalse(requests[1]["store"])
        self.assertNotIn("previous_response_id", requests[1])

    @patch("builtins.print")
    def test_tool_error_goes_back_to_model_and_can_be_corrected(self, _print):
        client, requests = self.make_client([
            {"output": [tool_call({"jednotkova_cena": -850, "pocet_kusu": 12, "sleva_procent": 8}, "bad")]},
            {"output": [tool_call({"jednotkova_cena": 850, "pocet_kusu": 12, "sleva_procent": 8}, "good")]},
            {"output": [message("Celkem 9384.00 Kč.")]},
        ])
        run_assistant(client, "offline-test", DEFAULT_QUESTION)
        outputs = [x for x in requests[2]["input"] if x.get("type") == "function_call_output"]
        self.assertEqual([x["call_id"] for x in outputs], ["bad", "good"])
        self.assertFalse(json.loads(outputs[0]["output"])["ok"])
        self.assertTrue(json.loads(outputs[1]["output"])["ok"])

    @patch("builtins.print")
    def test_missing_data_can_produce_clarifying_question(self, _print):
        client, requests = self.make_client([{"output": [message("Kolik kusů objednáváš?")]}])
        self.assertEqual(run_assistant(client, "offline-test", "Cena je 850 Kč."), "Kolik kusů objednáváš?")
        self.assertEqual(len(requests), 1)

    @patch("builtins.print")
    def test_incomplete_and_empty_responses_fail_clearly(self, _print):
        for payload in [{"status": "incomplete", "output": []}, {"output": []}]:
            with self.subTest(payload=payload):
                client, _ = self.make_client([payload])
                with self.assertRaises(RuntimeError):
                    run_assistant(client, "offline-test", DEFAULT_QUESTION)

    @patch("builtins.print")
    def test_loop_stops_at_api_call_limit(self, _print):
        client, requests = self.make_client([
            {"output": [tool_call({"jednotkova_cena": 850, "pocet_kusu": 12, "sleva_procent": 8}, f"call_{i}")]}
            for i in range(MAX_API_CALLS)
        ])
        with self.assertRaisesRegex(RuntimeError, "limit"):
            run_assistant(client, "offline-test", DEFAULT_QUESTION)
        self.assertEqual(len(requests), MAX_API_CALLS)


if __name__ == "__main__":
    unittest.main()
