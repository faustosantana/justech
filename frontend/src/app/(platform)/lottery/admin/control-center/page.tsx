import { redirect } from "next/navigation";

/** J-10X: Control Center hub identity lives at /lottery. */
export default function ControlCenterHubRedirect() {
  redirect("/lottery");
}
