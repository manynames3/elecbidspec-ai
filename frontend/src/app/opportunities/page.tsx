import { Suspense } from "react";
import { OpportunityDetail } from "@/components/OpportunityDetail";

export default function OpportunityPage() {
  return (
    <Suspense fallback={<div className="empty-state">Loading opportunity...</div>}>
      <OpportunityDetail />
    </Suspense>
  );
}
