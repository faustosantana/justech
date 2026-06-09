"use client";

import { Bell, CheckCheck, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import { NOTIFICATION_TYPE_LABELS, type Notification } from "@/lib/tasks";
import { t } from "@/i18n";
import { cn } from "@/lib/utils";

const m = t();

export default function NotificationsPage() {
  const router = useRouter();
  const [items, setItems] = useState<Notification[]>([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!getAccessToken()) {
      router.replace("/login");
      return;
    }
    setLoading(true);
    try {
      const res = await apiClient.getNotifications(false, 100);
      setItems(res.items);
      setUnread(res.unread_count);
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    load();
  }, [load]);

  const markRead = async (id: string) => {
    await apiClient.markNotificationRead(id);
    load();
  };

  const markAll = async () => {
    await apiClient.markAllNotificationsRead();
    load();
  };

  return (
    <AppShell title={m.notifications.title} description={m.notifications.description}>
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2 justify-end">
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
          </Button>
          {unread > 0 && (
            <Button size="sm" variant="secondary" onClick={markAll}>
              <CheckCheck className="mr-2 h-4 w-4" />
              {m.notifications.markAllRead}
            </Button>
          )}
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Bell className="h-4 w-4" />
              {unread > 0 ? `${unread} ${m.notifications.unread}` : m.notifications.allRead}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {loading ? (
              <p className="text-sm text-muted-foreground">{m.common.loading}</p>
            ) : items.length === 0 ? (
              <p className="text-sm text-muted-foreground">{m.notifications.empty}</p>
            ) : (
              items.map((n) => (
                <div
                  key={n.id}
                  className={cn(
                    "rounded-lg border p-4 flex items-start justify-between gap-4",
                    !n.is_read ? "border-primary/40 bg-primary/5" : "border-border",
                  )}
                >
                  <div>
                    <p className="font-medium text-sm">{n.title}</p>
                    <p className="text-sm text-muted-foreground mt-1">{n.message}</p>
                    <p className="text-xs text-muted-foreground mt-2">
                      {new Date(n.created_at).toLocaleString("es-DO")} · {NOTIFICATION_TYPE_LABELS[n.type] ?? n.type}
                    </p>
                    {n.related_task_id && (
                      <Link href={`/tasks/${n.related_task_id}`} className="text-xs text-primary hover:underline mt-1 inline-block">
                        {m.notifications.viewTask}
                      </Link>
                    )}
                  </div>
                  {!n.is_read && (
                    <Button size="sm" variant="ghost" onClick={() => markRead(n.id)}>
                      {m.notifications.markRead}
                    </Button>
                  )}
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
