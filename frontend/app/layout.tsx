import type { Metadata } from "next";
import { EB_Garamond, Open_Sans } from "next/font/google";
import "./globals.css";
import SiteHeader from "./components/SiteHeader";

const garamond = EB_Garamond({
  subsets: ["latin"],
  variable: "--font-garamond",
  display: "swap",
});

const openSans = Open_Sans({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Fourth Estate Index",
  description: "Journalists scored against the SPJ Code of Ethics.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${garamond.variable} ${openSans.variable}`}>
      <body className="min-h-screen" style={{ fontFamily: "var(--font-sans)" }}>
        <SiteHeader />
        {children}
      </body>
    </html>
  );
}
