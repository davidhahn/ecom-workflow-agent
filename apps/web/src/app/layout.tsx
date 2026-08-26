import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { IntroBanner } from "@/components/IntroBanner";
import { NavHeader } from "@/components/NavHeader";
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
  title: "Ops Intelligence Agent",
  description: "Enterprise Operations Intelligence Agent",
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
          <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-8">{children}</main>
        </RoleProvider>
      </body>
    </html>
  );
}
