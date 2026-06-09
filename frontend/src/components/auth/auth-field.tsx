import * as React from "react";

import { cn } from "@/lib/utils";

type AuthFieldProps = React.InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  hint?: string;
  icon?: React.ReactNode;
  error?: boolean;
};

export const AuthField = React.forwardRef<HTMLInputElement, AuthFieldProps>(
  ({ label, hint, icon, error, className, id, ...props }, ref) => {
    const fieldId = id ?? props.name;

    return (
      <div className="space-y-2">
        <label htmlFor={fieldId} className="auth-field-label">
          {label}
        </label>
        <div className="relative">
          {icon && <span className="auth-field-icon">{icon}</span>}
          <input
            ref={ref}
            id={fieldId}
            className={cn("auth-field-input", icon && "pl-11", error && "auth-field-input-error", className)}
            {...props}
          />
        </div>
        {hint && <p className="text-xs leading-relaxed text-muted-foreground">{hint}</p>}
      </div>
    );
  },
);
AuthField.displayName = "AuthField";
