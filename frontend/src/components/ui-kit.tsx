import type { LucideIcon } from "lucide-react";
import {
  Barcode,
  ChevronLeft,
  ChevronRight,
  Database,
  Loader2,
  PackageSearch,
  ShieldAlert,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";
import type { ReactNode } from "react";

export interface IconTileProps {
  icon: LucideIcon;
  size?: "sm" | "md" | "lg";
  tone?: "primary" | "emerald" | "amber" | "rose" | "slate";
}

export function IconTile({
  icon: Icon,
  size = "md",
  tone = "primary",
}: IconTileProps) {
  const toneClasses = {
    primary:
      "bg-[#edf2f7] text-primary border border-white/80 shadow-[3px_3px_8px_rgba(166,180,200,0.35),-3px_-3px_8px_#ffffff]",
    emerald:
      "bg-emerald-50/80 text-emerald-700 border border-emerald-200/60 shadow-[3px_3px_8px_rgba(16,185,129,0.12),-3px_-3px_8px_#ffffff]",
    amber:
      "bg-amber-50/80 text-amber-800 border border-amber-200/60 shadow-[3px_3px_8px_rgba(245,158,11,0.15),-3px_-3px_8px_#ffffff]",
    rose:
      "bg-rose-50/80 text-rose-700 border border-rose-200/60 shadow-[3px_3px_8px_rgba(244,63,94,0.15),-3px_-3px_8px_#ffffff]",
    slate:
      "bg-slate-100/80 text-slate-700 border border-slate-200/60 shadow-[3px_3px_8px_rgba(166,180,200,0.35),-3px_-3px_8px_#ffffff]",
  }[tone];

  const sizeClasses = {
    sm: "size-10 rounded-xl",
    md: "size-12 rounded-2xl",
    lg: "size-14 rounded-3xl",
  }[size];

  const iconSizes = {
    sm: "size-4.5",
    md: "size-5.5",
    lg: "size-7",
  }[size];

  return (
    <span
      className={`inline-flex shrink-0 items-center justify-center transition-all duration-200 ${toneClasses} ${sizeClasses}`}
    >
      <Icon className={iconSizes} aria-hidden="true" />
    </span>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`card-surface p-5 rounded-2xl ${className}`}>{children}</div>;
}

export function FormField({
  label,
  htmlFor,
  hint,
  error,
  children,
  required,
  className = "",
}: {
  label: string;
  htmlFor?: string;
  hint?: string;
  error?: string;
  children: ReactNode;
  required?: boolean;
  className?: string;
}) {
  return (
    <div className={`space-y-1.5 ${className}`}>
      <div className="flex items-center justify-between">
        <label htmlFor={htmlFor} className="block text-xs font-semibold text-foreground">
          {label} {required ? <span className="text-destructive">*</span> : null}
        </label>
        {hint ? <span className="text-[11px] text-muted-foreground">{hint}</span> : null}
      </div>
      {children}
      {error ? <p className="text-xs text-destructive font-medium">{error}</p> : null}
    </div>
  );
}

export function Input({
  className = "",
  ...props
}: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={`w-full min-h-[44px] rounded-xl border border-white/70 bg-[#edf2f7] px-3.5 py-2 text-sm font-medium text-foreground outline-none shadow-[inset_2px_2px_5px_rgba(166,180,200,0.38),inset_-2px_-2px_5px_#ffffff] transition-all duration-200 placeholder:text-muted-foreground focus:border-primary/60 focus:ring-2 focus:ring-primary/20 disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
      {...props}
    />
  );
}

export function Select({
  className = "",
  children,
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={`w-full min-h-[44px] rounded-xl border border-white/70 bg-[#edf2f7] px-3.5 py-2 text-sm font-medium text-foreground outline-none shadow-[inset_2px_2px_5px_rgba(166,180,200,0.38),inset_-2px_-2px_5px_#ffffff] transition-all duration-200 focus:border-primary/60 focus:ring-2 focus:ring-primary/20 disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
      {...props}
    >
      {children}
    </select>
  );
}

export function PageHeader({
  title,
  subtitle,
  facilityTag,
  actions,
}: {
  title: string;
  subtitle?: string;
  facilityTag?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight text-foreground md:text-3xl">
            {title}
          </h1>
          {facilityTag}
        </div>
        {subtitle ? (
          <p className="mt-1 max-w-3xl text-sm font-normal text-muted-foreground">{subtitle}</p>
        ) : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2.5">{actions}</div> : null}
    </div>
  );
}

export function EmptyState({
  message,
  hint,
  icon: Icon = PackageSearch,
}: {
  message: string;
  hint?: string;
  icon?: LucideIcon;
}) {
  return (
    <div
      role="status"
      className="flex flex-col items-center justify-center gap-2.5 px-6 py-14 text-center"
    >
      <span className="flex size-16 items-center justify-center rounded-2xl bg-[#edf2f7] text-primary border border-white/80 shadow-[4px_4px_10px_rgba(166,180,200,0.35),-4px_-4px_10px_#ffffff]">
        <Icon className="size-6" aria-hidden="true" />
      </span>
      <p className="text-sm font-semibold text-foreground">{message}</p>
      {hint ? <p className="max-w-md text-sm text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

export function LoadingState({ message = "Loading operational data..." }: { message?: string }) {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="true"
      className="flex items-center justify-center gap-2 px-6 py-16 text-sm text-muted-foreground"
    >
      <Loader2 className="size-5 animate-spin text-primary" aria-hidden="true" />
      <span>{message}</span>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div
      role="alert"
      aria-live="assertive"
      className="my-4 rounded-2xl border border-rose-300/40 bg-gradient-to-r from-rose-50/80 to-[#edf2f7] p-4 text-sm text-status-red shadow-[4px_4px_10px_rgba(244,63,94,0.12),-4px_-4px_10px_#ffffff]"
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <ShieldAlert className="size-4 shrink-0 text-rose-600" aria-hidden="true" />
          <span className="font-medium">{message}</span>
        </div>
        {onRetry ? (
          <button
            type="button"
            onClick={onRetry}
            className="min-h-[44px] inline-flex items-center justify-center rounded-full border border-primary/40 bg-[#edf2f7] px-4 py-2 text-xs font-semibold text-primary shadow-[2px_2px_6px_rgba(166,180,200,0.3),-2px_-2px_6px_#ffffff] transition-all hover:shadow-[4px_4px_10px_rgba(166,180,200,0.35),-4px_-4px_10px_#ffffff] active:shadow-[inset_2px_2px_4px_rgba(166,180,200,0.4),inset_-2px_-2px_4px_#ffffff] focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 cursor-pointer"
          >
            Retry
          </button>
        ) : null}
      </div>
    </div>
  );
}

export function ExceptionBanner({ children }: { children: ReactNode }) {
  return (
    <div className="mb-5 flex items-start gap-3 rounded-2xl border border-amber-300/50 bg-gradient-to-r from-amber-50/90 to-[#edf2f7] px-4 py-3 text-sm text-amber-800 shadow-[4px_4px_10px_rgba(217,119,6,0.12),-4px_-4px_10px_#ffffff]">
      <TriangleAlert className="mt-0.5 size-4 shrink-0 text-amber-600" aria-hidden="true" />
      <div className="flex-1 text-foreground/90 font-medium">{children}</div>
    </div>
  );
}

export function LedgerNoticeBanner({
  message = "This view is backed by an append-only transactional ledger. Inventory quantities cannot be directly overwritten.",
}: {
  message?: string;
}) {
  return (
    <div className="mb-5 flex items-center gap-2.5 rounded-2xl border border-blue-200/80 bg-gradient-to-r from-blue-50/90 to-[#edf2f7] px-4 py-3 text-sm text-primary shadow-[4px_4px_10px_rgba(37,99,235,0.12),-4px_-4px_10px_#ffffff]">
      <Database className="size-4 shrink-0" aria-hidden="true" />
      <span>
        <strong className="font-semibold">Ledger-backed truth:</strong> {message}
      </span>
    </div>
  );
}

export function DuplicateProtectionBanner({
  message = "Duplicate receipt protection is active. If a shipment is scanned again or a laptop freezes, duplicate submissions are safely flagged for manager review.",
}: {
  message?: string;
}) {
  return (
    <div className="mb-4 flex items-center gap-2.5 rounded-2xl border border-blue-200/80 bg-gradient-to-r from-blue-50/90 to-[#edf2f7] px-4 py-3 text-sm text-primary shadow-[4px_4px_10px_rgba(37,99,235,0.12),-4px_-4px_10px_#ffffff]">
      <ShieldCheck className="size-4 shrink-0" aria-hidden="true" />
      <span>
        <strong className="font-semibold">Duplicate safe:</strong> {message}
      </span>
    </div>
  );
}

export function ScannerInputField({
  value,
  onChange,
  ariaLabel,
  placeholder = "Scan UPC barcode or enter SKU...",
  disabled = false,
  className = "",
  autoFocus = false,
  onKeyDown,
}: {
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  ariaLabel: string;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  autoFocus?: boolean;
  onKeyDown?: (e: React.KeyboardEvent<HTMLInputElement>) => void;
}) {
  return (
    <div className={`relative flex items-center ${className}`}>
      <Barcode className="pointer-events-none absolute left-3.5 size-4 text-muted-foreground" aria-hidden="true" />
      <input
        type="text"
        value={value}
        onChange={onChange}
        onKeyDown={onKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        autoFocus={autoFocus}
        aria-label={ariaLabel}
        className="w-full rounded-full border border-white/70 bg-[#edf2f7] py-2.5 pr-4 pl-10 font-mono text-sm font-semibold text-foreground outline-none shadow-[inset_2px_2px_5px_rgba(166,180,200,0.42),inset_-2px_-2px_5px_#ffffff] placeholder:font-sans placeholder:font-normal placeholder:text-muted-foreground transition-all duration-200 focus:border-primary/60 focus:ring-2 focus:ring-primary/20 disabled:bg-muted disabled:text-muted-foreground"
      />
    </div>
  );
}

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "danger" | "ghost";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  loadingLabel?: string;
}

export function Button({
  children,
  variant = "primary",
  size = "md",
  className = "",
  disabled = false,
  loading = false,
  loadingLabel,
  ...props
}: ButtonProps) {
  const styles = {
    primary:
      "bg-gradient-to-r from-blue-600 to-primary text-white border border-blue-400/40 shadow-[4px_4px_10px_rgba(37,99,235,0.28),-2px_-2px_8px_rgba(255,255,255,0.8)] hover:shadow-[6px_6px_14px_rgba(37,99,235,0.35),-3px_-3px_10px_rgba(255,255,255,0.9)] hover:-translate-y-0.5 active:translate-y-0 active:shadow-[inset_2px_2px_5px_rgba(29,78,216,0.5),inset_-2px_-2px_5px_rgba(255,255,255,0.2)] focus-visible:ring-primary/40 font-semibold",
    secondary:
      "bg-[#edf2f7] text-primary border border-white/80 shadow-[3px_3px_8px_rgba(166,180,200,0.35),-3px_-3px_8px_#ffffff] hover:shadow-[5px_5px_12px_rgba(166,180,200,0.4),-5px_-5px_12px_#ffffff] hover:-translate-y-0.5 active:translate-y-0 active:shadow-[inset_2px_2px_5px_rgba(166,180,200,0.45),inset_-2px_-2px_5px_#ffffff] focus-visible:ring-primary/40 font-semibold",
    outline:
      "border border-primary/40 bg-[#edf2f7] text-primary shadow-[2px_2px_6px_rgba(166,180,200,0.3),-2px_-2px_6px_#ffffff] hover:bg-primary-tint hover:shadow-[4px_4px_10px_rgba(166,180,200,0.35),-4px_-4px_10px_#ffffff] hover:-translate-y-0.5 active:translate-y-0 active:shadow-[inset_2px_2px_4px_rgba(166,180,200,0.4),inset_-2px_-2px_4px_#ffffff] focus-visible:ring-primary/40 font-semibold",
    danger:
      "bg-destructive text-destructive-foreground hover:bg-red-700 active:bg-red-800 border border-red-400/30 shadow-[3px_3px_8px_rgba(220,38,38,0.25),-2px_-2px_6px_rgba(255,255,255,0.8)] active:shadow-[inset_2px_2px_4px_rgba(153,27,27,0.5)] focus-visible:ring-destructive/40 font-semibold",
    ghost:
      "text-muted-foreground hover:text-foreground hover:bg-slate-200/50 hover:shadow-[2px_2px_6px_rgba(166,180,200,0.2),-2px_-2px_6px_#ffffff] active:shadow-[inset_1px_1px_3px_rgba(166,180,200,0.3)] focus-visible:ring-primary/40 font-medium",
  }[variant];

  const sizeStyles = {
    sm: "px-3 py-1.5 text-xs rounded-full gap-1.5",
    md: "px-4 py-2 text-sm rounded-full gap-2",
    lg: "px-5 py-2.5 text-sm rounded-full gap-2.5",
  }[size];

  const isDisabled = disabled || loading;

  return (
    <button
      disabled={isDisabled}
      aria-busy={loading ? "true" : undefined}
      className={`inline-flex cursor-pointer items-center justify-center transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none ${styles} ${sizeStyles} ${className}`}
      {...props}
    >
      {loading ? <Loader2 className="size-4 animate-spin shrink-0" aria-hidden="true" /> : null}
      {loading && loadingLabel ? loadingLabel : children}
    </button>
  );
}

export function TableShell({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`card-surface overflow-hidden rounded-2xl ${className}`}>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">{children}</table>
      </div>
    </div>
  );
}

export function Th({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <th
      className={`bg-slate-100/80 border-b border-slate-200/80 px-4 py-3.5 text-left text-xs font-bold tracking-wide text-muted-foreground uppercase whitespace-nowrap align-middle shadow-[inset_0_-1px_0_rgba(226,232,240,0.8)] ${className}`}
    >
      {children}
    </th>
  );
}

export function Td({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <td className={`border-t border-slate-200/60 px-4 py-3 text-foreground align-middle transition-colors duration-150 ${className}`}>
      {children}
    </td>
  );
}

export function Timeline({
  events,
  items,
}: {
  events?: Array<{ id?: string; at: string; label: string; detail?: string }>;
  items?: Array<{ id?: string; at: string; label: string; detail?: string }>;
}) {
  const list = events || items || [];
  return (
    <ol className="relative space-y-3.5 pl-5 text-xs">
      <span className="absolute top-2 bottom-2 left-[3px] w-px bg-slate-200" />
      {list.map((e, idx) => (
        <li key={e.id || idx} className="relative">
          <span className="absolute top-1.5 -left-[19px] size-2 rounded-full bg-blue-600 ring-4 ring-white shadow-xs" />
          <p className="font-semibold text-slate-900">{e.label}</p>
          {e.detail ? <p className="text-slate-600 text-[11px] mt-0.5">{e.detail}</p> : null}
          <p className="text-[10px] font-mono text-slate-400 mt-0.5">{e.at}</p>
        </li>
      ))}
    </ol>
  );
}

export interface MobileRecordListProps {
  children: ReactNode;
  label: string;
  testId: string;
  className?: string;
}

export function MobileRecordList({
  children,
  label,
  testId,
  className = "",
}: MobileRecordListProps) {
  const classes = ["grid gap-3 md:hidden", className].filter(Boolean).join(" ");
  return (
    <div
      role="list"
      aria-label={label}
      data-testid={testId}
      className={classes}
    >
      {children}
    </div>
  );
}

export interface MobileRecordCardProps {
  children: ReactNode;
  className?: string;
  selected?: boolean;
}

export function MobileRecordCard({
  children,
  className = "",
  selected = false,
}: MobileRecordCardProps) {
  const classes = [
    "card-surface p-4 min-w-0 transition-all duration-200",
    selected ? "border-primary ring-2 ring-primary/25 bg-blue-50/50 shadow-[inset_2px_2px_5px_rgba(37,99,235,0.15),inset_-2px_-2px_5px_#ffffff]" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <article
      role="listitem"
      className={classes}
    >
      {children}
    </article>
  );
}

export interface PaginationControlsProps {
  currentPage: number;
  pageSize: number;
  totalCount: number;
  visibleCount: number;
  itemLabel: string;
  onPageChange: (page: number) => void;
  disabled?: boolean;
  className?: string;
}

export function PaginationControls({
  currentPage,
  pageSize,
  totalCount,
  visibleCount,
  itemLabel,
  onPageChange,
  disabled = false,
  className = "",
}: PaginationControlsProps) {
  if (totalCount <= pageSize) {
    return null;
  }

  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
  const safePage = Math.min(Math.max(1, currentPage), totalPages);
  const start = totalCount === 0 ? 0 : (safePage - 1) * pageSize + 1;
  const end = totalCount === 0 ? 0 : Math.min((safePage - 1) * pageSize + visibleCount, totalCount);

  return (
    <nav
      aria-label={`${itemLabel} pagination`}
      className={`flex flex-col sm:flex-row items-center justify-between gap-4 py-3 px-2 ${className}`}
    >
      <p role="status" aria-live="polite" className="text-sm text-muted-foreground order-2 sm:order-1">
        Showing <span className="font-semibold text-foreground">{start}</span>–<span className="font-semibold text-foreground">{end}</span> of{" "}
        <span className="font-semibold text-foreground">{totalCount}</span> {itemLabel}
      </p>
      <div className="flex items-center gap-2 order-1 sm:order-2 w-full sm:w-auto justify-between sm:justify-end">
        <button
          type="button"
          onClick={() => onPageChange(safePage - 1)}
          disabled={disabled || safePage <= 1}
          aria-label={`Go to previous page of ${itemLabel}`}
          className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center gap-1.5 rounded-full border border-white/80 bg-[#edf2f7] px-3.5 py-2 text-sm font-semibold text-foreground shadow-[2px_2px_6px_rgba(166,180,200,0.3),-2px_-2px_6px_#ffffff] hover:shadow-[4px_4px_10px_rgba(166,180,200,0.35),-4px_-4px_10px_#ffffff] hover:-translate-y-0.5 active:translate-y-0 active:shadow-[inset_2px_2px_4px_rgba(166,180,200,0.4),inset_-2px_-2px_4px_#ffffff] disabled:pointer-events-none disabled:opacity-50 transition-all duration-200 cursor-pointer"
        >
          <ChevronLeft className="size-4" aria-hidden="true" />
          <span>Previous</span>
        </button>
        <span className="text-sm font-semibold text-muted-foreground px-2" aria-current="page">
          Page {safePage} of {totalPages}
        </span>
        <button
          type="button"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={disabled || currentPage >= totalPages}
          aria-label={`Go to next page of ${itemLabel}`}
          className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center gap-1.5 rounded-full border border-white/80 bg-[#edf2f7] px-3.5 py-2 text-sm font-semibold text-foreground shadow-[2px_2px_6px_rgba(166,180,200,0.3),-2px_-2px_6px_#ffffff] hover:shadow-[4px_4px_10px_rgba(166,180,200,0.35),-4px_-4px_10px_#ffffff] hover:-translate-y-0.5 active:translate-y-0 active:shadow-[inset_2px_2px_4px_rgba(166,180,200,0.4),inset_-2px_-2px_4px_#ffffff] disabled:pointer-events-none disabled:opacity-50 transition-all duration-200 cursor-pointer"
        >
          <span>Next</span>
          <ChevronRight className="size-4" aria-hidden="true" />
        </button>
      </div>
    </nav>
  );
}
