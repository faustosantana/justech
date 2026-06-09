import { Badge } from "@/components/ui/badge";
import { STATUS_LABELS, type OpportunityStatus } from "@/lib/dgcp";

const VARIANT_MAP: Record<
  OpportunityStatus,
  "default" | "success" | "warning" | "danger" | "muted"
> = {
  detected: "default",
  to_review: "warning",
  interested: "warning",
  to_bid: "success",
  discarded: "muted",
  won: "success",
  lost: "danger",
};

export function StatusBadge({ status }: { status: OpportunityStatus }) {
  return <Badge variant={VARIANT_MAP[status]}>{STATUS_LABELS[status]}</Badge>;
}
