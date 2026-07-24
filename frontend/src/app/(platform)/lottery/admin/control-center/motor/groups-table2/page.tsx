import { redirect } from "next/navigation";

export default function GroupsTable2Redirect() {
  redirect("/lottery/admin/control-center/motor/agrupaciones?tab=table2");
}
