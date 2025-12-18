import type { Metadata } from "next";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";
import StoreProvider from "@/redux/StoreProvider";
import { AuthProvider } from "@/components/utils/AuthProvider";

export const metadata: Metadata = {
  title: "AlgoCreator(Beta)",
  description: "Created with v0",
  generator: "v0.dev",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" href="images/AlgoCreator_Logo_v3.png" />
      </head>
      <body>
        <StoreProvider>
          <AuthProvider>{children}</AuthProvider>
        </StoreProvider>
        <Toaster />
      </body>
    </html>
  );
}
