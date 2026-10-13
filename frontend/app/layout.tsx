import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "EVCSDS — AC Wallbox Karar Destek Araştırması",
  description: "2209-A araştırma bağlamında ev tipi AC şarj seçimi: gerçek kataloglar, açıklanabilir teknik kurallar, kontrollü deneyler ve etkileşimli karar destek prototipi.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="tr"><body>{children}</body></html>;
}
