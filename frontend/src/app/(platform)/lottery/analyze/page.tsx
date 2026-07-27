import { redirect } from "next/navigation";

/** Alias English path → canonical Spanish analyze route. */
export default function LotteryAnalyzeAliasPage({
  searchParams,
}: {
  searchParams?: Record<string, string | string[] | undefined>;
}) {
  const qs = new URLSearchParams();
  if (searchParams) {
    for (const [k, v] of Object.entries(searchParams)) {
      if (Array.isArray(v)) v.forEach((x) => qs.append(k, x));
      else if (v != null) qs.set(k, v);
    }
  }
  const suffix = qs.toString();
  redirect(suffix ? `/lottery/analizar?${suffix}` : "/lottery/analizar");
}
