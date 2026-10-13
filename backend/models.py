"""HTTP girdileri: katalog teknik değerleri istemciden kabul edilmez."""

from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

PositiveNumber = Annotated[float, Field(strict=True, gt=0, allow_inf_nan=False)]
NonnegativeNumber = Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)]


class HomeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    faz: Literal["monofaz", "trifaz", "belirsiz"]
    sozlesme_gucu_kw: PositiveNumber | None = None
    donem_tuketimi_kwh: NonnegativeNumber | None = None
    gunluk_ortalama_kwh: NonnegativeNumber | None = None
    tarife: Annotated[str, Field(min_length=1, max_length=120)] | None = None


class UserInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    gunluk_ortalama_km: PositiveNumber
    evde_sarj_icin_uygun_sure_saat: Annotated[float, Field(strict=True, gt=0, le=24, allow_inf_nan=False)]
    butce_tl: PositiveNumber | None = None
    kurulum_yeri: Literal["İç mekan", "Dış mekan"]


class RecommendationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    home: HomeInput
    user: UserInput
    vehicle_id: Annotated[str, Field(min_length=1, max_length=160)]
    home_confirmed: StrictBool
    input_source: Literal["manual", "ocr"] = "manual"
    analysis_token: Annotated[str, Field(max_length=4096)] | None = None

    @model_validator(mode="after")
    def require_confirmation(self):
        if not self.home_confirmed:
            raise ValueError("Ev bilgileri kullanıcı tarafından doğrulanmalıdır.")
        if self.input_source == "ocr" and not self.analysis_token:
            raise ValueError("Görsel analizinin doğrulama kaydı eksik; yeniden analiz edin.")
        return self
