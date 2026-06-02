import type { ReactNode } from "react";

export const FIT_TOOLTIP = "How closely this bid matches your capabilities and project history. 70+ is worth reviewing. 85+ is a strong match.";
export const PORTAL_GATED_TOOLTIP = "This source requires a separate login we can't automate. You'll need to check it manually using the link provided.";
export const VALUE_MATCH_TOOLTIP = "Confirmed = dollar value was stated in the posting. Likely = estimated from scope indicators and comparable bids.";
export const COVERED_BY_SOURCE_TOOLTIP = "This agency's bids are included via another connected source. No duplicate data.";

type InfoTooltipProps = {
  children: ReactNode;
  tooltip: string;
};

export function InfoTooltip({ children, tooltip }: InfoTooltipProps) {
  return (
    <span className="tooltip-wrap">
      <span className="tooltip-label">{children}</span>
      <span className="tooltip-icon" aria-hidden="true">
        ⓘ
      </span>
      <span className="tooltip-text">{tooltip}</span>
    </span>
  );
}
