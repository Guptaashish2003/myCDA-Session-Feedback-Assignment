"use client";

import { useState } from "react";
import { Star } from "lucide-react";
import { cn } from "@/lib/utils";
import { MAX_RATING } from "@/lib/feedback";

interface StarRatingProps {
  /** 0 means "not rated yet". Read-only values may be fractional (e.g. 3.6). */
  value: number;
  /** Omit for a read-only display. */
  onChange?: (value: number) => void;
  label?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const SIZES = { sm: "h-3.5 w-3.5", md: "h-5 w-5", lg: "h-7 w-7" };

/**
 * Star rating used everywhere ratings appear.
 *  - interactive: hovering previews the rating, clicking fills the stars in.
 *  - read-only: renders `value`, including partial stars for averages.
 */
export function StarRating({
  value,
  onChange,
  label,
  size = "md",
  className,
}: StarRatingProps) {
  const [hover, setHover] = useState<number | null>(null);
  const interactive = Boolean(onChange);
  const shown = hover ?? value;

  return (
    <div
      role={interactive ? "radiogroup" : "img"}
      aria-label={label ? `${label}: ${value} of ${MAX_RATING}` : `${value} of ${MAX_RATING}`}
      className={cn("inline-flex items-center gap-0.5", className)}
      onMouseLeave={() => setHover(null)}
    >
      {Array.from({ length: MAX_RATING }, (_, index) => {
        const star = index + 1;
        const fill = Math.min(1, Math.max(0, shown - index));
        const icon = (
          <span className="relative block">
            <Star className={cn(SIZES[size], "text-gray-300")} />
            <span
              className="absolute inset-0 overflow-hidden"
              style={{ width: `${fill * 100}%` }}
            >
              <Star className={cn(SIZES[size], "fill-amber-400 text-amber-400")} />
            </span>
          </span>
        );

        if (!interactive) return <span key={star}>{icon}</span>;

        return (
          <button
            key={star}
            type="button"
            role="radio"
            aria-checked={value === star}
            aria-label={`${star} star${star > 1 ? "s" : ""}`}
            onMouseEnter={() => setHover(star)}
            onFocus={() => setHover(star)}
            onBlur={() => setHover(null)}
            onClick={() => onChange?.(star)}
            className={cn(
              "rounded-sm p-0.5 transition-transform hover:scale-125 focus-visible:scale-125",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            )}
          >
            {icon}
          </button>
        );
      })}
    </div>
  );
}
