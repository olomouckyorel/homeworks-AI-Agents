"""Simulace odpovědí LLM. Skutečný SDK klient i výpočet, žádné síťové spojení."""

import json

import httpx
from openai import OpenAI

from main import DEFAULT_QUESTION, run_assistant


def response_json(output: list, number: int) -> dict:
    return {
        "id": f"resp_offline_{number}", "object": "response", "created_at": 0,
        "status": "completed", "model": "offline-demo", "output": output,
    }


def main() -> None:
    count = 0

    def handle(request: httpx.Request) -> httpx.Response:
        nonlocal count
        count += 1
        if count == 1:
            output = [{
                "id": "fc_offline", "type": "function_call", "status": "completed",
                "call_id": "call_offline", "name": "spocitej_cenu",
                "arguments": json.dumps({"jednotkova_cena": 850, "pocet_kusu": 12, "sleva_procent": 8}),
            }]
        else:
            sent = json.loads(request.content)
            tool_output = next(item for item in sent["input"] if item.get("type") == "function_call_output")
            result = json.loads(tool_output["output"])
            # Tato věta je naprogramovaná simulace, nikoli výstup skutečného modelu.
            text = (
                f"Cena před slevou: {result['cena_pred_slevou_kc']} Kč.\n"
                f"Sleva: {result['sleva_kc']} Kč.\n"
                f"Celkem zaplatíš {result['celkem_kc']} Kč."
            )
            output = [{
                "id": "msg_offline", "type": "message", "role": "assistant", "status": "completed",
                "content": [{"type": "output_text", "text": text, "annotations": []}],
            }]
        return httpx.Response(200, json=response_json(output, count))

    print("OFFLINE DEMO: odpovědi LLM jsou simulované. Výpočet ceny je skutečný.")
    print("Žádný API klíč, žádné volání poskytovatele.\nDotaz: " + DEFAULT_QUESTION)
    with OpenAI(
        api_key="offline-placeholder", base_url="https://offline.example/v1",
        http_client=httpx.Client(transport=httpx.MockTransport(handle)), max_retries=0,
    ) as client:
        answer = run_assistant(client, "offline-demo", DEFAULT_QUESTION)
    print("\nOdpověď (simulovaná):\n" + answer)


if __name__ == "__main__":
    main()
