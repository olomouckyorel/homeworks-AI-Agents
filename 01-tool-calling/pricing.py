"""Výpočetní nástroj: konečná cena objednávky v Kč, bez práce s LLM."""

from decimal import Decimal, ROUND_HALF_UP


def _decimal(value: object, label: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError(f"{label} musí být číslo.")
    number = Decimal(str(value))
    if not number.is_finite():
        raise ValueError(f"{label} musí být konečné číslo.")
    return number


def spocitej_cenu(
    jednotkova_cena: object, pocet_kusu: object, sleva_procent: object
) -> dict:
    """Zaokrouhli slevu na haléře a odečti ji od celkové ceny před slevou."""
    price = _decimal(jednotkova_cena, "Jednotková cena")
    discount = _decimal(sleva_procent, "Sleva")
    if not Decimal("0") <= price <= Decimal("1000000000"):
        raise ValueError("Jednotková cena musí být mezi 0 a 1 000 000 000 Kč.")
    if price != price.quantize(Decimal("0.01")):
        raise ValueError("Jednotková cena smí mít nejvýše dvě desetinná místa.")
    if type(pocet_kusu) is not int or not 1 <= pocet_kusu <= 1000000:
        raise ValueError("Počet kusů musí být celé číslo od 1 do 1 000 000.")
    if not Decimal("0") <= discount <= Decimal("100"):
        raise ValueError("Sleva musí být mezi 0 a 100 procenty.")

    subtotal = price * pocet_kusu
    discount_amount = (subtotal * discount / 100).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    total = subtotal - discount_amount
    # Peníze vracíme jako řetězce: JSON tak neztratí přesnost ani koncové nuly.
    return {
        "ok": True,
        "pocet_kusu": pocet_kusu,
        "jednotkova_cena_kc": f"{price:.2f}",
        "sleva_procent": str(discount),
        "cena_pred_slevou_kc": f"{subtotal:.2f}",
        "sleva_kc": f"{discount_amount:.2f}",
        "celkem_kc": f"{total:.2f}",
        "mena": "CZK",
    }
