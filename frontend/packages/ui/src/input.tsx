import type { InputHTMLAttributes } from "react";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export function Input({
  label,
  error,
  className = "",
  id,
  ...props
}: InputProps) {
  const inputId = id || label?.toLowerCase().replace(/\s+/g, "-");
  return (
    <div className={`input-group ${className}`.trim()}>
      {label && <label htmlFor={inputId}>{label}</label>}
      <input id={inputId} aria-invalid={!!error} {...props} />
      {error && (
        <span role="alert" className="input-error">
          {error}
        </span>
      )}
    </div>
  );
}
