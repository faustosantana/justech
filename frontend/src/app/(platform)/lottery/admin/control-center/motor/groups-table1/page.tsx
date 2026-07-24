import { redirect } from "next/navigation";

export default function GroupsTable1Redirect() {
  redirect("/lottery/admin/control-center/motor/agrupaciones?tab=table1");
}
