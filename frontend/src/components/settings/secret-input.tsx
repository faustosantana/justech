"use client";

import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";

import { Button } from "@/components/ui/button";

type Props = {
  label: string;
  value: string;
  masked?: string | null;
  configured?: boolean;
  onChange: (v: string) => void;
  placeholder?: string;
};

export function SecretInput({ label, value, masked, configured, onChange, placeholder }: Props) {
  const [show, setShow] = useState(false);
  return (
    <div className="space-y-1.5">
      <label className="text-sm font-medium">{label}</label>
      {configured && masked && !value && (
        <p className="text-xs text-muted-foreground">Guardado: {masked}</p>
      )}
      <div className="flex gap-2">
        <input
          type={show ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder || "Nuevo valor (dejar vacío para mantener)"}
          className="flex-1 rounded-lg border border-input bg-background px-3 py-2 text-sm"
          autoComplete="off"
        />
        <Button type="button" variant="outline" size="icon" onClick={() => setShow(!show)}>
          {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </Button>
      </div>
    </div>
  );
}
