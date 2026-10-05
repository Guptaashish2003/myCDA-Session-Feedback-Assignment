/**
 * File: frontend/src/components/CardStatus.tsx
 * Purpose: Shared loading / error / empty states for cards (DRY).
 * Contents:
 *   - CardStatus: renders skeletons while loading, the error text, the empty message, or its
 *     children, in that priority.
 */
"use client";

import type { ReactNode } from "react";
import { Skeleton } from "@/components/ui/skeleton";

interface CardStatusProps {
  loading: boolean;
  error?: string;
  /** When true, `emptyMessage` is shown instead of the children. */
  empty?: boolean;
  emptyMessage?: string;
  children: ReactNode;
}

/**
 * The loading / error / empty states every dashboard card needs, in one
 * place. Render it inside a <DashboardCard>.
 */
export default function CardStatus({
  loading,
  error,
  empty = false,
  emptyMessage = "Nothing to show yet.",
  children,
}: CardStatusProps) {
  if (loading) {
    return (
      <div className="space-y-3" aria-busy="true" aria-label="Loading">
        <Skeleton className="h-4 w-2/3" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-1/2" />
      </div>
    );
  }
  if (error) return <p className="text-sm text-red-500">{error}</p>;
  if (empty) return <p className="text-sm text-gray-500">{emptyMessage}</p>;
  return <>{children}</>;
}
