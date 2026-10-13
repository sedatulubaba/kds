import json
import os
import secrets

KEYS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys.json")


def keys_yukle() -> dict:
    """keys.json dosyasını okur. Dosya yoksa boş dict döner."""
    if not os.path.exists(KEYS_FILE):
        return {}
    with open(KEYS_FILE, "r") as f:
        return json.load(f)


def keys_kaydet(keys: dict) -> None:
    """keys.json dosyasına yazar."""
    with open(KEYS_FILE, "w") as f:
        json.dump(keys, f, indent=2, ensure_ascii=False)


def key_uret(kullanici_adi: str) -> str:
    """
    Yeni bir API key üretir ve keys.json'a kaydeder.

    secrets.token_hex(32) → 64 karakterlik rastgele bir string üretir.
    random yerine secrets kullanıyoruz çünkü secrets
    kriptografik olarak güvenli rastgele sayı üretir.
    """
    keys = keys_yukle()

    yeni_key = secrets.token_hex(32)
    keys[yeni_key] = kullanici_adi
    keys_kaydet(keys)

    return yeni_key


def key_gecerli_mi(api_key: str) -> bool:
    """Gelen key keys.json'da var mı kontrol eder."""
    configured_key = os.getenv("EVCSDS_VISION_API_KEY")
    if configured_key and secrets.compare_digest(api_key, configured_key):
        return True
    keys = keys_yukle()
    return api_key in keys


def key_sahibi(api_key: str) -> str | None:
    """Key'in sahibini döndürür. Key yoksa None döner."""
    configured_key = os.getenv("EVCSDS_VISION_API_KEY")
    if configured_key and secrets.compare_digest(api_key, configured_key):
        return "kds-backend"
    keys = keys_yukle()
    return keys.get(api_key)
