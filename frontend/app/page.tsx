"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ResearchProvider, ResearchIntro, ResearchArticle, ResearchGuide, ResearchHelp } from "./research";

type Group = "eligible" | "needs_verification" | "excluded" | "insufficient_data";
type Phase = "monofaz" | "trifaz" | "belirsiz";
type Home = { faz: Phase; sozlesme_gucu_kw: number | null; donem_tuketimi_kwh: number | null; gunluk_ortalama_kwh: number | null; tarife: string | null };
type HomeFields = { [K in keyof Home]: string };
type Vehicle = { vehicle_id: string; marka: string; model: string; ac_tek_faz_azami_guc_kw: number | null; ac_uc_faz_azami_guc_kw: number | null; wltp_tuketim_kwh_100km: number | null };
type Candidate = {
  charger_id: string;
  hard_rule: { status: string; reasons: string[]; rules: { rule_id: string; status: string; reason: string }[] };
  warnings: string[];
  product: { marka: string; model: string; versiyon: string; nominal_azami_guc_kw: number | null; fiyat_tl: number | null; fiyat_tarihi: string | null; kurulum_dahil_mi: string | null; kaynak_url: string | null };
  metrics?: Record<string, number | null>;
};
type Decision = { candidates: Record<Group, Candidate[]>; counts: Record<Group, number>; home: Home; vehicle: Vehicle; notice: string };
type Analysis = { home: Home; analysis_token: string; manuel_dogrulama_alanlari: string[]; uyari: string };
const GROUPS: { key: Group; label: string; description: string }[] = [
  { key: "eligible", label: "Değerlendirilebilir", description: "Mevcut bilgilerle teknik değerlendirmeye devam edilebilen adaylar. Liste bir sıralama değildir." },
  { key: "needs_verification", label: "Doğrulama gerekli", description: "Ürün davranışı, faz yolu veya kurulum yeri için ek bilgi gerekiyor." },
  { key: "excluded", label: "Teknik olarak elenen", description: "Açık teknik uyumsuzluğu bulunan ürünler ve eleme gerekçeleri." },
  { key: "insufficient_data", label: "Veri yetersiz", description: "Katalog kanıtı değerlendirme için yetersiz olan kayıtlar." },
];
const FIELD_NAMES: Record<string, string> = { faz: "Ev fazı", sozlesme_gucu_kw: "Sözleşme gücü", donem_tuketimi_kwh: "Dönem tüketimi", gunluk_ortalama_kwh: "Günlük ev tüketimi", tarife: "Tarife", gunluk_ortalama_km: "Günlük kilometre", evde_sarj_icin_uygun_sure_saat: "Şarja uygun süre", butce_tl: "Bütçe", vehicle_id: "Araç", home_confirmed: "Ev bilgisi onayı" };
const number = (value: number | null | undefined, suffix = "") => value == null ? "Bilgi yok" : `${new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 2 }).format(value)}${suffix}`;
const optionalNumber = (value: string) => value.trim() === "" ? null : Number(value);

async function readResponse<T>(response: Response): Promise<T> {
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    if (typeof data?.detail === "string") throw new Error(data.detail);
    if (Array.isArray(data?.detail)) {
      const fields = data.detail.map((item: { loc?: string[] }) => FIELD_NAMES[item.loc?.at(-1) || ""] || "Girdi");
      throw new Error(`Şu alanları kontrol edin: ${[...new Set(fields)].join(", ")}.`);
    }
    throw new Error("İşlem tamamlanamadı. Sunucunun çalıştığını kontrol edip yeniden deneyin.");
  }
  return data as T;
}

function Bolt() {
  return <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M13.5 2 5 13h6l-.5 9L19 11h-6l.5-9Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" /></svg>;
}

export default function Page() {
  const [step, setStep] = useState(1);
  const [mode, setMode] = useState<"manual" | "photo">("manual");
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [catalogError, setCatalogError] = useState("");
  const [visionConfigured, setVisionConfigured] = useState(false);
  const [home, setHome] = useState<HomeFields>({ faz: "belirsiz", sozlesme_gucu_kw: "", donem_tuketimi_kwh: "", gunluk_ortalama_kwh: "", tarife: "" });
  const [confirmed, setConfirmed] = useState(false);
  const [meter, setMeter] = useState<File | null>(null);
  const [bill, setBill] = useState<File | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [vehicleId, setVehicleId] = useState("");
  const [search, setSearch] = useState("");
  const [usage, setUsage] = useState({ km: "", hours: "", budget: "", location: "İç mekan" });
  const [decision, setDecision] = useState<Decision | null>(null);
  const [group, setGroup] = useState<Group>("eligible");

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      fetch("/api/catalog", { signal: controller.signal }).then(readResponse<{ vehicles: Vehicle[] }>),
      fetch("/api/health", { signal: controller.signal }).then(readResponse<{ vision_configured: boolean }>),
    ]).then(([catalog, health]) => { setVehicles(catalog.vehicles); setVisionConfigured(health.vision_configured); })
      .catch((failure: Error) => { if (failure.name !== "AbortError") setCatalogError("Araç kataloğuna ulaşılamadı. KDS sunucusunu başlatıp sayfayı yenileyin."); });
    return () => controller.abort();
  }, []);

  function updateHome(key: keyof Home, value: string) {
    setHome((previous) => ({ ...previous, [key]: value }));
    setConfirmed(false); setDecision(null); setError("");
  }

  function changeMode(next: "manual" | "photo") {
    setMode(next); setAnalysis(null); setConfirmed(false); setDecision(null); setError("");
  }

  function choosePhoto(file: File | null, kind: "meter" | "bill") {
    setAnalysis(null); setConfirmed(false); setDecision(null); setError("");
    if (file && (!/^image\/(jpeg|png|webp)$/.test(file.type) || file.size > 25 * 1024 * 1024)) {
      setError("JPEG, PNG veya WebP kullanın. Her fotoğraf en fazla 25 MB olabilir.");
      if (kind === "meter") setMeter(null); else setBill(null);
      return;
    }
    if (kind === "meter") setMeter(file); else setBill(file);
  }

  async function analyze() {
    if (!meter || !bill) return;
    setAnalyzing(true); setAnalysis(null); setConfirmed(false); setDecision(null); setError("");
    const form = new FormData(); form.append("meter_file", meter); form.append("bill_file", bill);
    try {
      const result = await readResponse<Analysis>(await fetch("/api/analyze-home", { method: "POST", body: form }));
      setAnalysis(result);
      setHome(Object.fromEntries(Object.entries(result.home).map(([key, value]) => [key, value == null ? "" : String(value)])) as HomeFields);
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Görsel analizi tamamlanamadı."); }
    finally { setAnalyzing(false); }
  }

  async function recommend(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    if (!confirmed || (mode === "photo" && !analysis)) { setError("Ev bilgilerini kontrol edip onaylayın."); setStep(1); return; }
    setSubmitting(true);
    try {
      const result = await readResponse<Decision>(await fetch("/api/recommend", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ home: { faz: home.faz, sozlesme_gucu_kw: optionalNumber(home.sozlesme_gucu_kw),
          donem_tuketimi_kwh: optionalNumber(home.donem_tuketimi_kwh), gunluk_ortalama_kwh: optionalNumber(home.gunluk_ortalama_kwh), tarife: home.tarife.trim() || null },
          user: { gunluk_ortalama_km: Number(usage.km), evde_sarj_icin_uygun_sure_saat: Number(usage.hours), butce_tl: optionalNumber(usage.budget), kurulum_yeri: usage.location },
          vehicle_id: vehicleId, home_confirmed: confirmed, input_source: mode === "photo" ? "ocr" : "manual", analysis_token: mode === "photo" ? analysis?.analysis_token : null }),
      }));
      setDecision(result); setGroup("eligible"); setStep(3); window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Değerlendirme tamamlanamadı."); }
    finally { setSubmitting(false); }
  }

  function exportResults() {
    if (!decision) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(decision, null, 2)], { type: "application/json" }));
    const link = document.createElement("a"); link.href = url; link.download = "evcsds-sonuclar.json"; link.click(); URL.revokeObjectURL(url);
  }

  const selectedVehicle = vehicles.find((vehicle) => vehicle.vehicle_id === vehicleId);
  const matchingVehicles = vehicles.filter((vehicle) => `${vehicle.marka} ${vehicle.model}`.toLocaleLowerCase("tr").includes(search.toLocaleLowerCase("tr")) || vehicle.vehicle_id === vehicleId);

  return <ResearchProvider>
    <a className="skip-link" href="#uygulama">Uygulamaya geç</a>
    <header className="header"><div className="shell header-inner"><Link className="brand" href="/"><span className="brand-mark"><Bolt /></span>EV Şarj Karar Destek Sistemi</Link><nav className="header-nav" aria-label="Ana menü"><a href="#uygulama" className="current">Ana Sayfa</a><a href="#yontem">Sistem</a><a href="#deney">Araştırma</a></nav><span className="header-tag"><span />2209-A PROTOTİPİ</span></div></header>
    <main className="shell">
      <ResearchIntro />
      <div className="application-layout"><aside className="workflow-sidebar"><p className="eyebrow">DEĞERLENDİRME AKIŞI</p><nav className="steps" aria-label="Değerlendirme adımları">{["Ev bilgileri", "Araç ve kullanım", "Aday sonuçları"].map((label, index) => <button type="button" key={label} className={step === index + 1 ? "active" : step > index + 1 ? "complete" : ""} aria-current={step === index + 1 ? "step" : undefined} disabled={index === 1 && !confirmed || index === 2 && !decision} onClick={() => { setStep(index + 1); setError(""); }}><span>{step > index + 1 ? "✓" : `0${index + 1}`}</span><div><strong>{label}</strong><small>{["Ev bilgilerini gir ve doğrula", "Aracını ve kullanımını tanımla", "Teknik adayları ve gerekçeleri incele"][index]}</small></div></button>)}</nav><div className="workflow-note"><span className="workflow-badge">ARAŞTIRMA NOTU</span><p>Her sonuç, kullanılan veriye ve teknik kurala kadar izlenebilir.</p><ResearchHelp topic="rules" label="Karar yöntemi" /><ResearchHelp topic="limits" label="Kapsam ve sınırlılıklar" /></div></aside><div className="application-body">
      {catalogError && <div className="error" role="alert">{catalogError}<button type="button" onClick={() => window.location.reload()}>Yenile</button></div>}
      {error && <div className="error" role="alert">{error}</div>}

      {step === 1 && <section className="workspace"><div className="panel"><div className="section-head"><div><p className="eyebrow">ADIM 01</p><h2>Evinizi tanıyalım.</h2><p>Bilgileri girin veya sayaç ve fatura fotoğraflarından okuyun.</p></div><span className="pill">Önce kontrol, sonra onay</span></div>
        <ResearchGuide topics={["phase", "contract", "bill", "approval", "vision"]} />
        <div className="mode-switch" role="group" aria-label="Bilgi giriş yöntemi"><button type="button" className={mode === "manual" ? "selected" : ""} onClick={() => changeMode("manual")}>Manuel giriş</button><button type="button" className={mode === "photo" ? "selected" : ""} onClick={() => changeMode("photo")}>Fotoğraftan oku</button></div>
        {mode === "photo" && <div className="photo-section">{!visionConfigured && <p className="info">Görsel servis bağlantısı henüz yapılandırılmamış. Manuel girişle devam edebilirsiniz.</p>}<div className="photo-grid">{[{ kind: "meter" as const, title: "Sayaç fotoğrafı", file: meter }, { kind: "bill" as const, title: "Elektrik faturası", file: bill }].map((photo) => <label className={photo.file ? "upload chosen" : "upload"} key={photo.kind}><span className="upload-icon">{photo.file ? "✓" : "+"}</span><strong>{photo.title}</strong><span>{photo.file ? photo.file.name : "Fotoğraf seçin"}</span><small>JPEG, PNG, WebP · en fazla 25 MB</small><input type="file" accept="image/jpeg,image/png,image/webp" disabled={analyzing} onChange={(event) => choosePhoto(event.target.files?.[0] || null, photo.kind)} aria-label={photo.title} /></label>)}</div><button className="button secondary" type="button" disabled={!meter || !bill || analyzing || !visionConfigured} onClick={analyze}>{analyzing ? "Fotoğraflar okunuyor…" : "Fotoğrafları analiz et →"}</button>{analyzing && <p className="info" role="status">Fotoğraftaki alanlar okunuyor. Görüntüye bağlı olarak birkaç dakika sürebilir.</p>}{analysis && <div className="info" role="status">{analysis.uyari}{analysis.manuel_dogrulama_alanlari.length > 0 && <p>Kontrol gereken alanlar: {analysis.manuel_dogrulama_alanlari.map((field) => FIELD_NAMES[field] || field).join(", ")}.</p>}</div>}</div>}
        <form onSubmit={(event) => { event.preventDefault(); if (confirmed && (mode === "manual" || analysis)) { setStep(2); setError(""); } }}>
          <div className="form-grid"><label>Ev fazı<select value={home.faz} onChange={(event) => updateHome("faz", event.target.value)}><option value="belirsiz">Bilmiyorum / doğrulama gerekli</option><option value="monofaz">Monofaz (tek faz)</option><option value="trifaz">Trifaz (üç faz)</option></select><small>Emin değilseniz bilinmiyor olarak bırakın.</small></label><label>Sözleşme gücü <span className="optional">opsiyonel</span><div className="input-unit"><input type="number" min="0.01" step="any" placeholder="Örn. 6,75" value={home.sozlesme_gucu_kw} onChange={(event) => updateHome("sozlesme_gucu_kw", event.target.value)} /><span>kW</span></div><small>Faturadaki değer; güvenli şarj gücü değildir.</small></label></div>
          <details className="additional"><summary>Ek fatura bilgileri <span>opsiyonel</span></summary><div className="form-grid"><label>Dönem tüketimi<div className="input-unit"><input type="number" min="0" step="any" value={home.donem_tuketimi_kwh} onChange={(event) => updateHome("donem_tuketimi_kwh", event.target.value)} /><span>kWh</span></div></label><label>Günlük ev tüketimi<div className="input-unit"><input type="number" min="0" step="any" value={home.gunluk_ortalama_kwh} onChange={(event) => updateHome("gunluk_ortalama_kwh", event.target.value)} /><span>kWh</span></div></label><label className="span-two">Tarife<input maxLength={120} placeholder="Faturada yazan tarife, biliniyorsa" value={home.tarife} onChange={(event) => updateHome("tarife", event.target.value)} /></label></div></details>
          <label className="confirmation"><input type="checkbox" checked={confirmed} disabled={mode === "photo" && !analysis || analyzing} onChange={(event) => { setConfirmed(event.target.checked); setDecision(null); }} /><span>Ev bilgilerini kontrol ettim. Bilmediğim alanları boş veya belirsiz bıraktım.<small>Bir değeri değiştirirseniz yeniden onaylamanız gerekir.</small></span></label>
          <div className="actions"><span>Eksik bilgiler tahmin edilmez.</span><button className="button" type="submit" disabled={!confirmed || mode === "photo" && !analysis || analyzing}>Araç bilgilerine geç →</button></div>
        </form></div><aside className="aside-card"><span className="aside-icon"><Bolt /></span><h3>Yüksek güç her zaman<br />daha hızlı şarj değildir.</h3><p>Araç, wallbox ve seçilen faz yolu birlikte değerlendirilir. 22 kW bir ürün, 11 kW kabul eden araca 22 kW sağlayamaz.</p><div className="aside-divider" /><h4>Ne elde edeceksiniz?</h4><ul><li>Teknik olarak değerlendirilebilir adaylar</li><li>Günlük ihtiyacınıza ait teorik metrikler</li><li>Eleme ve doğrulama gerekçeleri</li></ul><p className="aside-small">Sonuçlar ürün ön değerlendirmesidir. Kurulum koşulları ayrıca kontrol edilmelidir.</p></aside></section>}

      {step === 2 && <section className="workspace"><div className="panel"><div className="section-head"><div><p className="eyebrow">ADIM 02</p><h2>Aracınız ve günlük rutininiz.</h2><p>Kullanım bilgileriyle günlük şarj ihtiyacını hesaplayalım.</p></div></div><ResearchGuide topics={["vehicle", "wltp", "usage", "budget", "location"]} /><form onSubmit={recommend}><label>Araç ara<input placeholder="Marka veya model yazın" value={search} onChange={(event) => setSearch(event.target.value)} /></label><label className="vehicle-select">Katalogdan aracınızı seçin<select required disabled={!vehicles.length} value={vehicleId} onChange={(event) => { setVehicleId(event.target.value); setDecision(null); }}><option value="">Araç seçin</option>{matchingVehicles.map((vehicle) => <option key={vehicle.vehicle_id} value={vehicle.vehicle_id}>{vehicle.marka} — {vehicle.model}</option>)}</select></label>
        {selectedVehicle && <div className="vehicle-info"><strong>{selectedVehicle.marka} {selectedVehicle.model}</strong><div><span>Tek faz: {number(selectedVehicle.ac_tek_faz_azami_guc_kw, " kW")}</span><span>Üç faz: {number(selectedVehicle.ac_uc_faz_azami_guc_kw, " kW")}</span><span>Tüketim: {number(selectedVehicle.wltp_tuketim_kwh_100km, " kWh/100 km")}</span></div>{selectedVehicle.wltp_tuketim_kwh_100km == null && <p>Bu aracın tüketim bilgisi eksik. Teknik adaylar değerlendirilecek; enerji ve süre tahmin edilmeyecek.</p>}</div>}
        <div className="form-grid usage-grid"><label>Günlük ortalama mesafe<div className="input-unit"><input required type="number" min="0.01" step="any" placeholder="Örn. 40" value={usage.km} onChange={(event) => { setUsage({ ...usage, km: event.target.value }); setDecision(null); }} /><span>km</span></div></label><label>Evde şarja uygun süre<div className="input-unit"><input required type="number" min="0.01" max="24" step="any" placeholder="Örn. 8" value={usage.hours} onChange={(event) => { setUsage({ ...usage, hours: event.target.value }); setDecision(null); }} /><span>saat/gün</span></div></label><label>Ürün bütçesi <span className="optional">opsiyonel</span><div className="input-unit"><input type="number" min="0.01" step="any" placeholder="Belirlemediyseniz boş bırakın" value={usage.budget} onChange={(event) => { setUsage({ ...usage, budget: event.target.value }); setDecision(null); }} /><span>TL</span></div><small>Kurulum ve ek ekipman maliyetleri ayrıca değerlendirilir.</small></label><label>Kurulum yeri<select value={usage.location} onChange={(event) => { setUsage({ ...usage, location: event.target.value }); setDecision(null); }}><option>İç mekan</option><option>Dış mekan</option></select></label></div><div className="actions"><button className="text-button" type="button" onClick={() => setStep(1)}>← Ev bilgilerine dön</button><button className="button" type="submit" disabled={!vehicleId || submitting || !confirmed}>{submitting ? "Adaylar değerlendiriliyor…" : "Şarj adaylarını değerlendir →"}</button></div></form></div><aside className="aside-card light"><p className="eyebrow">ONAYLANAN EV BİLGİLERİ</p><h3>{home.faz === "trifaz" ? "Üç faz" : home.faz === "monofaz" ? "Tek faz" : "Faz belirsiz"}</h3><p>Sözleşme gücü: {home.sozlesme_gucu_kw ? `${home.sozlesme_gucu_kw} kW` : "Bilgi yok"}</p><p className="aside-small">Güç hesabında sözleşme gücü sınır olarak kullanılmaz. Belirsiz faz için ürünler doğrulama listesine ayrılır.</p><button className="text-button" type="button" onClick={() => setStep(1)}>Bilgileri düzenle ↗</button></aside></section>}

      {step === 3 && decision && <section className="results"><div className="results-heading"><div><p className="eyebrow">ADIM 03 · ÖN DEĞERLENDİRME</p><h2>Şarj adaylarınız.</h2><p>{decision.vehicle.marka} {decision.vehicle.model} · {decision.home.faz === "belirsiz" ? "Faz doğrulaması gerekli" : decision.home.faz === "monofaz" ? "Monofaz ev" : "Trifaz ev"}</p></div><div className="result-actions"><button className="button secondary" type="button" onClick={exportResults}>Sonuçları indir ↓</button><button className="text-button" type="button" onClick={() => { setStep(1); setError(""); }}>Bilgileri düzenle</button></div></div><div className="info result-notice">{decision.notice}</div><ResearchGuide topics={["groups", "rules", "power", "wltp", "time", "coverage", "utilisation", "budget"]} /><div className="result-tabs" role="tablist" aria-label="Aday grupları">{GROUPS.map((entry) => <button type="button" role="tab" aria-selected={group === entry.key} key={entry.key} onClick={() => setGroup(entry.key)} className={group === entry.key ? `selected ${entry.key}` : entry.key}><strong>{decision.counts[entry.key]}</strong><span>{entry.label}</span></button>)}</div><p className="group-description">{GROUPS.find((entry) => entry.key === group)?.description}</p><div role="tabpanel" aria-label={GROUPS.find((entry) => entry.key === group)?.label}>
        {decision.candidates[group].length === 0 ? <div className="empty-state"><span>◎</span><h3>Bu grupta ürün yok.</h3><p>{group === "eligible" ? "Diğer sekmelerde doğrulama gereken veya elenen adayların gerekçelerini inceleyin." : "Diğer aday gruplarını inceleyebilirsiniz."}</p></div> : <div className="candidate-grid">{decision.candidates[group].map((item) => <article className="candidate" key={item.charger_id}><div className="candidate-top"><span className="product-brand">{item.product.marka}</span><span className={`status ${group}`}>{GROUPS.find((entry) => entry.key === group)?.label}</span></div><h3>{item.product.model}</h3><p className="variant">{item.product.versiyon}</p><div className="product-facts"><span>Nominal güç <strong>{number(item.product.nominal_azami_guc_kw, " kW")}</strong></span><span>Ürün fiyatı <strong>{number(item.product.fiyat_tl, " TL")}</strong></span></div>{item.product.fiyat_tl != null && <p className="price-note">Fiyat tarihi: {item.product.fiyat_tarihi || "Bilgi yok"} · Kurulum dahil: {item.product.kurulum_dahil_mi || "Bilinmiyor"}</p>}
          {item.metrics && <div className="metric-grid"><div><small>Teorik etkin güç</small><strong>{number(item.metrics.arac_wallbox_teorik_etkin_guc_kw, " kW")}</strong></div><div><small>Günlük enerji ihtiyacı</small><strong>{number(item.metrics.gunluk_arac_enerji_ihtiyaci_kwh, " kWh")}</strong></div><div><small>Teorik ihtiyaç süresi</small><strong>{number(item.metrics.teorik_gunluk_ihtiyac_karsilama_suresi_saat, " saat")}</strong></div><div><small>İhtiyaç karşılama oranı</small><strong>{item.metrics.gunluk_ihtiyac_karsilama_orani == null ? "Bilgi yok" : number(item.metrics.gunluk_ihtiyac_karsilama_orani * 100, "%")}</strong></div></div>}
          {group !== "eligible" && <ul className="reasons">{item.hard_rule.reasons.filter((reason) => !reason.startsWith("Sözleşme gücü/")).map((reason, index) => <li key={index}>{reason}</li>)}</ul>}
          <details className="explanation"><summary>Gerekçeler ve tüm metrikler</summary><div className="candidate-help"><ResearchHelp topic="rules" label="Bu kurallar neyi kontrol ediyor?" /></div><ul>{item.hard_rule.rules.map((rule) => <li key={rule.rule_id}><strong>{rule.rule_id}</strong> {rule.reason}</li>)}</ul>{item.metrics && <div className="extra-metrics"><p>Nominal kapasite kullanım oranı: {number(item.metrics.nominal_kapasite_kullanim_orani)}</p><p>Fiyat / bütçe oranı: {number(item.metrics.fiyat_butce_orani)}</p></div>}{item.warnings.length > 0 && <><h4>Veri uyarıları</h4><ul>{item.warnings.map((warning, index) => <li key={index}>{warning.includes(":") ? warning.slice(warning.indexOf(":") + 1).trim() : warning}</li>)}</ul></>}{item.product.kaynak_url && <a href={item.product.kaynak_url} target="_blank" rel="noreferrer">Ürün kaynağını incele ↗</a>}</details></article>)}</div>}
      </div></section>}
      </div></div>
      <ResearchArticle />
    </main><footer className="shell footer"><span>EVCSDS · 2209-A araştırma prototipi</span><span>Eksik veri tahmin edilmez. Kurulum uygunluğu ayrıca doğrulanır.</span></footer>
  </ResearchProvider>;
}
