"""Özgün, sürümü sabitlenmiş iki YOLO ağırlığını indirir; API anahtarı Git'e girmez."""

import hashlib
import json
import secrets
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHA = "ddae1f6ad19ffe9835e479a01bf1133180153b2d"
MODEL_PATHS = ["runs/detect/runs/electric_meter_detection3/weights/best.pt",
               "runs/detect/electricity_bill_detection_v2/weights/best.pt"]


def setup():
    request = urllib.request.Request(
        f"https://api.github.com/repos/RounenRais/evcsds-app/git/trees/{SHA}?recursive=1",
        headers={"User-Agent": "evcsds-setup"})
    with urllib.request.urlopen(request, timeout=60) as response:
        tree = {item["path"]: item for item in json.load(response)["tree"]}
    for relative in MODEL_PATHS:
        destination = ROOT / "vision_service" / relative
        expected = tree[relative]["sha"]
        if destination.is_file():
            data = destination.read_bytes()
        else:
            with urllib.request.urlopen(f"https://raw.githubusercontent.com/RounenRais/evcsds-app/{SHA}/{relative}", timeout=120) as response:
                data = response.read()
        digest = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if digest != expected:
            raise ValueError(f"Model hash uyuşmazlığı: {relative}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        print(f"Doğrulandı: {relative}")
    env = ROOT / ".env"
    text = env.read_text(encoding="utf-8") if env.exists() else ""
    for key in ("EVCSDS_VISION_API_KEY", "EVCSDS_CONFIRMATION_SECRET"):
        if not any(line.startswith(key + "=") and line.split("=",1)[1].strip() for line in text.splitlines()):
            text = "\n".join(line for line in text.splitlines() if not line.startswith(key + "="))
            text += f"\n{key}={secrets.token_hex(32)}\n"
    if "EVCSDS_VISION_URL=" not in text:
        text += "EVCSDS_VISION_URL=http://127.0.0.1:8001\n"
    env.write_text(text, encoding="utf-8")
    print("Yerel .env hazır; anahtarlar ekrana yazılmadı. Servisleri yeniden başlatın.")


if __name__ == "__main__":
    setup()
