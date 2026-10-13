from __future__ import annotations

import io
import uuid
import warnings
from dataclasses import asdict, dataclass
from pathlib import Path

from fastapi import UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError


MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_IMAGE_PIXELS = 80_000_000
MAX_IMAGE_SIDE = 6000
READ_CHUNK_SIZE = 1024 * 1024
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


class GorselDogrulamaHatasi(ValueError):
    pass


@dataclass(frozen=True)
class GorselBilgisi:
    dosya_boyutu: int
    orijinal_genislik: int
    orijinal_yukseklik: int
    islenen_genislik: int
    islenen_yukseklik: int
    yeniden_boyutlandirildi: bool
    kaynak_format: str

    def dict(self) -> dict:
        return asdict(self)


async def upload_verisini_oku(upload: UploadFile) -> bytes:
    parcalar: list[bytes] = []
    toplam = 0
    while True:
        parca = await upload.read(READ_CHUNK_SIZE)
        if not parca:
            break
        toplam += len(parca)
        if toplam > MAX_UPLOAD_BYTES:
            raise GorselDogrulamaHatasi("Görsel dosyası en fazla 25 MB olabilir.")
        parcalar.append(parca)

    if not parcalar:
        raise GorselDogrulamaHatasi("Yüklenen dosya boş.")
    return b"".join(parcalar)


def gorseli_hazirla(veri: bytes, hedef_klasor: Path) -> tuple[Path, GorselBilgisi]:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(veri)) as kaynak:
                kaynak_format = (kaynak.format or "").upper()
                if kaynak_format not in ALLOWED_FORMATS:
                    raise GorselDogrulamaHatasi(
                        "Dosyanın gerçek formatı JPEG, PNG veya WebP değil."
                    )

                orijinal_genislik, orijinal_yukseklik = kaynak.size
                piksel_sayisi = orijinal_genislik * orijinal_yukseklik
                if piksel_sayisi > MAX_IMAGE_PIXELS:
                    raise GorselDogrulamaHatasi(
                        "Görsel çözünürlüğü en fazla 80 megapiksel olabilir."
                    )

                kaynak.load()
                islenen = ImageOps.exif_transpose(kaynak).convert("RGB")
                onceki_boyut = islenen.size
                if max(islenen.size) > MAX_IMAGE_SIDE:
                    islenen.thumbnail(
                        (MAX_IMAGE_SIDE, MAX_IMAGE_SIDE), Image.Resampling.LANCZOS
                    )

                hedef_klasor.mkdir(parents=True, exist_ok=True)
                hedef = hedef_klasor / f"{uuid.uuid4().hex}.jpg"
                islenen.save(hedef, "JPEG", quality=90, optimize=True)

                bilgi = GorselBilgisi(
                    dosya_boyutu=len(veri),
                    orijinal_genislik=orijinal_genislik,
                    orijinal_yukseklik=orijinal_yukseklik,
                    islenen_genislik=islenen.width,
                    islenen_yukseklik=islenen.height,
                    yeniden_boyutlandirildi=islenen.size != onceki_boyut,
                    kaynak_format=kaynak_format,
                )
                return hedef, bilgi
    except GorselDogrulamaHatasi:
        raise
    except (
        Image.DecompressionBombWarning,
        Image.DecompressionBombError,
        UnidentifiedImageError,
        OSError,
        ValueError,
    ) as exc:
        raise GorselDogrulamaHatasi("Görsel okunamadı veya bozuk.") from exc
