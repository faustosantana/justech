import { redirect } from "next/navigation";

/**
 * /apps index was missing from the App Router (only /apps/[appId] existed),
 * producing a production 404. /dashboard is the canonical AppsLauncher route.
 */
export default function AppsIndexPage() {
  redirect("/dashboard");
}
