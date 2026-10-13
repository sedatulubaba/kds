import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "EVCSDS — Eviniz için şarj adayları",
  description: "Ev, araç ve kullanım bilgileriyle gerekçeli AC wallbox ön değerlendirmesi.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="tr"><body>{children}</body></html>;
}
