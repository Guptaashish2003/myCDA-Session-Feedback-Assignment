/**
 * File: frontend/src/app/layout.tsx
 * Purpose: Root layout.
 * Contents:
 *   - RootLayout: sets page metadata and wraps every page in AuthProvider and the shadcn/sonner
 *     Toaster used for notifications.
 */
import type { Metadata } from "next";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from "@/contexts/AuthContext";
import "./globals.css";

export const metadata: Metadata = {
  title: "myCDA",
  description: "CDA Student & Parent Portal",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-gray-50 text-gray-900 antialiased">
        <AuthProvider>{children}</AuthProvider>
        <Toaster richColors position="top-right" />
      </body>
    </html>
  );
}
