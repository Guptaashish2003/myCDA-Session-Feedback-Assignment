/**
 * File: frontend/src/app/page.tsx
 * Purpose: Home route '/'.
 * Contents:
 *   - Home: once auth has loaded, redirects to /dashboard if logged in, else /login.
 */
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading) {
      router.replace(user ? "/dashboard" : "/login");
    }
  }, [user, loading, router]);

  return (
    <div className="flex h-screen items-center justify-center">
      <p className="text-gray-400">Loading...</p>
    </div>
  );
}
