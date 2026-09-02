import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { IntroBanner } from "@/components/IntroBanner";
import { NavHeader } from "@/components/NavHeader";
import { SiteFooter } from "@/components/SiteFooter";
import { RoleProvider } from "@/lib/role-context";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    template: "%s · Ops Intelligence Agent",
    default: "Reliable AI Systems Case Study | Ops Intelligence Agent",
  },
  description:
    "A full-stack AI engineering case study exploring RAG, tool orchestration, evals, deterministic guardrails, permissions, observability, latency, and cost through a working e-commerce agent.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <RoleProvider>
          <IntroBanner />
          <NavHeader />
          <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-12 sm:py-16">{children}</main>
          <SiteFooter />
        </RoleProvider>
      </body>
    </html>
  );
}
