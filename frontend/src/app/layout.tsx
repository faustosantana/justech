import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import { BRAND } from "@/lib/brand";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: `${BRAND.product} — ${BRAND.company} AI Operating System`,
  description: `${BRAND.product} es el centro de mando empresarial de ${BRAND.company}. ${BRAND.tagline}.`,
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    title: BRAND.product,
    statusBarStyle: "default",
  },
  icons: {
    icon: "/icons/jaios-192.svg",
    apple: "/icons/jaios-192.svg",
  },
};

export const viewport: Viewport = {
  themeColor: BRAND.themeColor,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} h-full min-h-screen bg-background font-sans text-foreground antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
