import type { Metadata } from "next";
import { Geist_Mono } from "next/font/google";
import "./globals.css";
import EsportsBanner from "./components/EsportsBanner";
import { ModalProvider } from "./context/ModalContext";
import PageTransition from "./components/PageTransition";

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "QuantRift - AI-Powered League of Legends Analysis",
  description: "Advanced AI agent analysis for League of Legends players. Track performance, compare statistics, and gain insights powered by intelligent analysis.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistMono.variable} antialiased`}
        suppressHydrationWarning
      >
        <ModalProvider>
          <div className="fixed top-0 left-0 right-0 z-[9999]">
            <EsportsBanner />
          </div>
          <div className="pt-[44px]">
            <PageTransition>
              {children}
            </PageTransition>
          </div>
        </ModalProvider>
      </body>
    </html>
  );
}
