import type { Metadata } from "next";
import { Toaster } from "sonner";
import "./globals.css";

export const metadata: Metadata = {
  title: "Arad Quality Intelligence Platform",
  description: "AI-native manufacturing quality control — GR&R analysis, SPC monitoring, predictive analytics, and intelligent alerting for industrial quality teams.",
  keywords: ["quality control", "GR&R", "SPC", "manufacturing", "AI", "statistical process control"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        {children}
        <Toaster
          theme="dark"
          richColors
          position="bottom-right"
          toastOptions={{
            style: {
              fontFamily: "Inter, ui-sans-serif, system-ui",
              borderRadius: "12px",
              border: "1px solid rgba(148,163,184,0.18)",
              background: "rgba(13, 18, 29, 0.92)",
              backdropFilter: "blur(20px) saturate(1.5)",
              boxShadow: "0 4px 12px rgba(2,6,18,0.55), 0 24px 64px -16px rgba(2,6,18,0.8)",
            },
          }}
        />
      </body>
    </html>
  );
}
