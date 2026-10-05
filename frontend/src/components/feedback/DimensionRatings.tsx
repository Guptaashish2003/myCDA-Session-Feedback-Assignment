"use client";

import { Progress } from "@/components/ui/progress";
import { StarRating } from "@/components/ui/star-rating";
import { MAX_RATING, RATING_DIMENSIONS } from "@/lib/feedback";
import type { RatingKey } from "@/lib/types";

interface DimensionRatingsProps {
  /** `null` = no data (rendered as an em dash). */
  values: Record<RatingKey, number | null>;
  /** Provide to make the stars clickable (the submission form). */
  onChange?: (key: RatingKey, value: number) => void;
  size?: "sm" | "md" | "lg";
  /** Show the numeric value next to the stars (summaries). */
  showValue?: boolean;
  /** Show a progress bar under each row (summaries). */
  showBar?: boolean;
  /** Show the hint text under each label (the form). */
  showHints?: boolean;
}

/**
 * One row per rating dimension. The form, the history list and the
 * instructor summary all render ratings through this component.
 */
export default function DimensionRatings({
  values,
  onChange,
  size = "md",
  showValue = false,
  showBar = false,
  showHints = false,
}: DimensionRatingsProps) {
  return (
    <div className="space-y-3">
      {RATING_DIMENSIONS.map(({ key, label, hint }) => {
        const value = values[key];
        return (
          <div key={key}>
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-gray-800">{label}</p>
                {showHints && <p className="text-xs text-gray-500">{hint}</p>}
              </div>
              <div className="flex items-center gap-2">
                <StarRating
                  value={value ?? 0}
                  onChange={onChange ? (next) => onChange(key, next) : undefined}
                  label={label}
                  size={size}
                />
                {showValue && (
                  <span className="w-8 text-right text-sm font-semibold tabular-nums text-gray-900">
                    {value === null ? "—" : value.toFixed(1)}
                  </span>
                )}
              </div>
            </div>
            {showBar && (
              <Progress value={((value ?? 0) / MAX_RATING) * 100} className="mt-1.5 h-1.5" />
            )}
          </div>
        );
      })}
    </div>
  );
}
