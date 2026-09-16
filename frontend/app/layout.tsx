import type { Metadata } from "next";
import { Geist } from "next/font/google";

import { RelationshipWorkspace } from "@/features/relationships/components/relationship-workspace";

import "./globals.css";
import { SiteHeader } from "./site-header";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Customer Pulse",
  description:
    "Prospects and customers, with their contacts and interaction history.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geistSans.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col bg-white text-neutral-900">
        <SiteHeader />
        <main className="flex flex-1 flex-col">
          <RelationshipWorkspace>{children}</RelationshipWorkspace>
        </main>
      </body>
    </html>
  );
}
