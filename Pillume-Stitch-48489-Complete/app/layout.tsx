import type { Metadata } from "next";
import { headers } from "next/headers";
import "./globals.css";

export async function generateMetadata(): Promise<Metadata> {
  const requestHeaders = await headers();
  const host =
    requestHeaders.get("x-forwarded-host") ??
    requestHeaders.get("host") ??
    "localhost:3000";
  const protocol =
    requestHeaders.get("x-forwarded-proto") ??
    (host.startsWith("localhost") ? "http" : "https");
  const origin = `${protocol}://${host}`;
  const title = "Pillume | 스마트 복약 케어";
  const description =
    "ESP_SZ 블루투스 스마트 알약 디스펜서와 모션 무드등 통합 대시보드";

  return {
    metadataBase: new URL(origin),
    title,
    description,
    openGraph: {
      type: "website",
      title,
      description,
      url: origin,
      images: [{ url: `${origin}/og.png`, width: 1760, height: 917 }],
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: [`${origin}/og.png`],
    },
  };
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
