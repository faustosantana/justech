"use client";

import type { ReactNode } from "react";

import { Button, type ButtonProps } from "@/components/ui/button";
import type { PlatformAccess } from "@/lib/admin";
import { canMutate, MUTATE_DENIED_MESSAGE } from "@/lib/permissions";

type MutateButtonProps = ButtonProps & {
  permission: string;
  access: PlatformAccess | null;
  /** Si false, muestra el botón deshabilitado con tooltip nativo. */
  hideWhenDenied?: boolean;
  children: ReactNode;
};

export function MutateButton({
  permission,
  access,
  hideWhenDenied = true,
  disabled,
  title,
  children,
  ...props
}: MutateButtonProps) {
  const allowed = canMutate(access, permission);
  if (!allowed && hideWhenDenied) return null;

  return (
    <Button
      {...props}
      disabled={disabled || !allowed}
      title={!allowed ? MUTATE_DENIED_MESSAGE : title}
    >
      {children}
    </Button>
  );
}
