/**
 * File: frontend/src/lib/utils.ts
 * Purpose: shadcn helper.
 * Contents:
 *   - cn(...): merges class names with clsx and resolves Tailwind conflicts with tailwind-merge.
 */
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
