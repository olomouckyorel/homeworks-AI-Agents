"""Úkol 1: dotaz → LLM → nástroj → výsledek nástroje → LLM → odpověď."""

import argparse
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv
from openai import APIConnectionError, APIStatusError, OpenAI

from pricing import spocitej_cenu

DEFAULT_QUESTION = "Kolik zaplatím za 12 kusů po 850 Kč se slevou 8 %?"
MAX_API_CALLS = 4
INSTRUCTIONS = """
Jsi český asistent pro výpočet ceny objednávky v Kč.
Při výpočtu vždy použij nástroj spocitej_cenu. Neodhaduj výsledek sám.
Pokud chybí jednotková cena nebo počet kusů, požádej o doplnění; nevymýšlej je.
Není-li sleva uvedena, použij 0 procent. DPH, dopravu ani jiné položky nepřidávej.
Po úspěšném výpočtu napiš cenu před slevou, slevu v Kč a konečnou cenu v Kč.
Pokud nástroj vrátí chybu, oprav argumenty podle dotazu, nebo požádej uživatele
o opravu zadání. Nikdy neprezentuj neúspěšný výpočet jako hotový výsledek.
""".strip()

# Responses API má definici funkce přímo v objektu nástroje.
TOOLS = [{
    "type": "function",
    "name": "spocitej_cenu",
    "description": "Spočítá cenu objednávky v Kč po procentní slevě.",
    "strict": True,
    "parameters": {
        "type": "object",
        "properties": {
            "jednotkova_cena": {"type": "number", "description": "Cena jednoho kusu v Kč."},
            "pocet_kusu": {"type": "integer", "description": "Počet objednaných kusů."},
            "sleva_procent": {"type": "number", "description": "Sleva v procentech, bez slevy 0."},
        },
        "required": ["jednotkova_cena", "pocet_kusu", "sleva_procent"],
        "additionalProperties": False,
    },
}]


def execute_tool(name: str, arguments: str) -> dict:
    """Povolena je jediná funkce. Argumenty od modelu znovu ověřuje Python."""
    if name != "spocitej_cenu":
        return {"ok": False, "chyba": "Neznámý nástroj. Povoleno je pouze spocitej_cenu."}
    try:
        values = json.loads(arguments, parse_float=Decimal)
        if not isinstance(values, dict) or set(values) != {
            "jednotkova_cena", "pocet_kusu", "sleva_procent"
        }:
            raise ValueError("Očekávám jednotkova_cena, pocet_kusu a sleva_procent.")
        return spocitej_cenu(**values)
    except (ValueError, TypeError) as error:
        return {"ok": False, "chyba": str(error)}


def run_assistant(client: OpenAI, model: str, question: str) -> str:
    """Historii spravuje klient; každý výsledek nástroje nese původní call_id."""
    history = [{"role": "user", "content": question}]
    for step in range(1, MAX_API_CALLS + 1):
        print(f"\n[{step}] Volám LLM…")
        response = client.responses.create(
            model=model,
            instructions=INSTRUCTIONS,
            input=history,
            tools=TOOLS,
            tool_choice="auto",
            parallel_tool_calls=False,
            max_output_tokens=2048,
            store=False,
            # Uvažující modely potřebují svůj stav také při store=False.
            include=["reasoning.encrypted_content"],
        )
        if response.status != "completed":
            raise RuntimeError("LLM nedokončilo odpověď. Zkontroluj limit výstupu a nastavení modelu.")

        # Zachováme všechny položky, včetně uvažování a požadavků na nástroje.
        history.extend(item.model_dump(mode="json", exclude_none=True) for item in response.output)
        calls = [item for item in response.output if item.type == "function_call"]
        if not calls:
            answer = response.output_text.strip()
            if not answer:
                raise RuntimeError("LLM nevrátilo text ani požadavek na nástroj.")
            return answer

        for call in calls:
            print(f"    Nástroj: {call.name}; argumenty: {call.arguments}")
            result = execute_tool(call.name, call.arguments)
            print("    Výsledek: " + json.dumps(result, ensure_ascii=False))
            # Model sám funkci nevykonává. Výsledek mu posílá náš program.
            history.append({
                "type": "function_call_output",
                "call_id": call.call_id,
                "output": json.dumps(result, ensure_ascii=False),
            })
    raise RuntimeError(f"Dosažen limit {MAX_API_CALLS} volání API bez konečné odpovědi.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Výpočet ceny objednávky pomocí LLM a nástroje.")
    parser.add_argument("dotaz", nargs="?", default=DEFAULT_QUESTION)
    args = parser.parse_args()
    if not args.dotaz.strip():
        parser.error("Dotaz nesmí být prázdný.")

    load_dotenv(Path(__file__).with_name(".env"), override=False)
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "gpt-5.6-terra").strip()
    if not api_key or not model:
        print("Chybí OPENAI_API_KEY nebo OPENAI_MODEL. Viz .env.example a README.md.", file=sys.stderr)
        return 1

    print(f"Dotaz: {args.dotaz}\nModel: {model}")
    try:
        # Bez automatických opakování: nejvýše čtyři požadavky, timeout 30 s na požadavek.
        with OpenAI(api_key=api_key, timeout=30, max_retries=0) as client:
            answer = run_assistant(client, model, args.dotaz)
        print("\nOdpověď:\n" + answer)
        return 0
    except APIConnectionError:
        print("Nelze se spojit s API nebo vypršel čas spojení.", file=sys.stderr)
    except APIStatusError as error:
        print(f"API odmítlo požadavek (HTTP {error.status_code}). Ověř klíč, model a dostupný kredit.", file=sys.stderr)
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
