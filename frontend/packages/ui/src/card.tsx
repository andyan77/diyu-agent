import type { HTMLAttributes } from "react";

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  title?: string;
  footer?: React.ReactNode;
}

export function Card({
  title,
  footer,
  className = "",
  children,
  ...props
}: CardProps) {
  return (
    <div className={`card ${className}`.trim()} {...props}>
      {title && <div className="card-header">{title}</div>}
      <div className="card-body">{children}</div>
      {footer && <div className="card-footer">{footer}</div>}
    </div>
  );
}
