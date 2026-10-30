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
    primary: "bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-400 border border-blue-200/80 dark:border-blue-900/60",
    emerald: "bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 border border-emerald-200/80 dark:border-emerald-900/60",
    amber: "bg-amber-50 dark:bg-amber-950/60 text-amber-800 dark:text-amber-400 border border-amber-200/80 dark:border-amber-900/60",
    rose: "bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-400 border border-rose-200/80 dark:border-rose-900/60",
    slate: "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200/80 dark:border-slate-700",
  }[tone];

  const sizeClasses = {
    sm: "size-9 rounded-lg",
    md: "size-10 rounded-lg",
    lg: "size-12 rounded-xl",
  }[size];

  const iconSizes = {
    sm: "size-4",
    md: "size-5",
    lg: "size-6",
  }[size];

  return (
    <span
      className={`inline-flex shrink-0 items-center justify-center ${toneClasses} ${sizeClasses}`}
    >
      <Icon className={iconSizes} aria-hidden="true" />
    </span>
  );
}

export function Card({
  children,
  className = "",
  testId,
}: {
  children: ReactNode;
  className?: string;
  testId?: string;
}) {
  return (
    <div
      data-testid={testId}
      className={`card-surface p-5 ${className}`}
    >
      {children}
    </div>
  );
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
        <label htmlFor={htmlFor} className="block text-[13px] font-medium text-slate-700 dark:text-slate-300">
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
      className={`w-full min-h-11 rounded-md border border-input bg-card px-3 py-2 text-sm text-foreground outline-none transition-[border-color,box-shadow] placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary/15 disabled:cursor-not-allowed disabled:opacity-60 ${className}`}
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
      className={`w-full min-h-11 rounded-md border border-input bg-card px-3 py-2 text-sm text-foreground outline-none transition-[border-color,box-shadow] focus:border-primary focus:ring-2 focus:ring-primary/15 disabled:cursor-not-allowed disabled:opacity-60 ${className}`}
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
    <div className="mb-7 flex flex-wrap items-end justify-between gap-4 border-b border-border pb-5">
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-[1.7rem] font-semibold tracking-tight text-slate-900 dark:text-slate-100 md:text-3xl">
            {title}
          </h1>
          {facilityTag}
        </div>
        {subtitle ? (
          <p className="mt-1.5 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-400">{subtitle}</p>
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
      className="flex flex-col items-center justify-center gap-2.5 px-6 py-10 text-center"
    >
      <span className="flex size-11 items-center justify-center rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
        <Icon className="size-5" aria-hidden="true" />
      </span>
      <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{message}</p>
      {hint ? <p className="max-w-md text-sm text-slate-500 dark:text-slate-400">{hint}</p> : null}
    </div>
  );
}

export function LoadingState({ message = "Loading operational data..." }: { message?: string }) {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="true"
      className="flex items-center justify-center gap-2 px-6 py-16 text-sm text-slate-500 dark:text-slate-400"
    >
      <Loader2 className="size-4 animate-spin text-primary" aria-hidden="true" />
      <span>{message}</span>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div
      role="alert"
      aria-live="assertive"
      className="my-4 rounded-xl border border-rose-200 dark:border-rose-900/60 bg-rose-50/80 dark:bg-rose-950/40 p-4 text-sm text-rose-800 dark:text-rose-200"
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <ShieldAlert className="size-4 shrink-0 text-rose-600 dark:text-rose-400" aria-hidden="true" />
          <span className="font-medium">{message}</span>
        </div>
        {onRetry ? (
          <button
            type="button"
            onClick={onRetry}
            className="min-h-[44px] inline-flex items-center justify-center rounded-lg border border-rose-300 dark:border-rose-800 bg-white dark:bg-slate-900 px-3.5 py-1.5 text-xs font-semibold text-rose-700 dark:text-rose-300 shadow-xs transition-colors hover:bg-rose-50 dark:hover:bg-rose-950 focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-500/30 cursor-pointer"
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
    <div className="mb-5 flex items-start gap-3 rounded-md border border-amber-200 dark:border-amber-900/60 bg-amber-50/80 dark:bg-amber-950/30 px-4 py-3 text-sm text-amber-900 dark:text-amber-200">
      <TriangleAlert className="mt-0.5 size-4 shrink-0 text-amber-600 dark:text-amber-400" aria-hidden="true" />
      <div className="flex-1 font-medium">{children}</div>
    </div>
  );
}

export function LedgerNoticeBanner({
  message = "This view is backed by an append-only transactional ledger. Inventory quantities cannot be directly overwritten.",
}: {
  message?: string;
}) {
  return (
    <div className="mb-5 flex items-start gap-2.5 rounded-md border border-blue-200 dark:border-blue-900/60 bg-blue-50/70 dark:bg-blue-950/30 px-4 py-3 text-sm text-blue-900 dark:text-blue-200">
      <Database className="size-4 shrink-0 text-blue-600 dark:text-blue-400" aria-hidden="true" />
      <span>{message}</span>
    </div>
  );
}

export function DuplicateProtectionBanner({
  message = "Duplicate receipt protection is active. If a shipment is scanned again or a laptop freezes, duplicate submissions are safely flagged for manager review.",
}: {
  message?: string;
}) {
  return (
    <div className="mb-4 flex items-start gap-2.5 rounded-md border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-4 py-3 text-sm text-slate-700 dark:text-slate-300">
      <ShieldCheck className="size-4 shrink-0 text-slate-600 dark:text-slate-400" aria-hidden="true" />
      <span>{message}</span>
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
      <Barcode className="pointer-events-none absolute left-3 size-4 text-slate-400 dark:text-slate-500" aria-hidden="true" />
      <input
        type="text"
        value={value}
        onChange={onChange}
        onKeyDown={onKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        autoFocus={autoFocus}
        aria-label={ariaLabel}
        className="w-full min-h-11 rounded-md border border-input bg-card py-2 pr-3.5 pl-9 font-mono text-sm font-medium text-foreground outline-none placeholder:font-sans placeholder:font-normal placeholder:text-muted-foreground transition-[border-color,box-shadow] focus:border-primary focus:ring-2 focus:ring-primary/15 disabled:opacity-60"
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
      "bg-primary text-primary-foreground hover:bg-primary-dark border border-transparent font-medium shadow-sm active:translate-y-px focus-visible:ring-primary/30",
    secondary:
      "bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-700 border border-transparent font-medium focus-visible:ring-slate-400/30",
    outline:
      "border border-input bg-card text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-100 font-medium focus-visible:ring-primary/30",
    danger:
      "bg-destructive text-destructive-foreground hover:bg-red-700 border border-transparent font-medium focus-visible:ring-destructive/30",
    ghost:
      "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800 font-medium border border-transparent focus-visible:ring-slate-400/30",
  }[variant];

  const sizeStyles = {
    sm: "min-h-9 px-3 py-1.5 text-xs rounded-md gap-1.5",
    md: "min-h-10 px-3.5 py-2 text-sm rounded-md gap-2",
    lg: "min-h-11 px-4 py-2.5 text-sm rounded-md gap-2.5",
  }[size];

  const isDisabled = disabled || loading;

  return (
    <button
      disabled={isDisabled}
      aria-busy={loading ? "true" : undefined}
      className={`inline-flex cursor-pointer items-center justify-center transition-[background-color,border-color,box-shadow,transform] duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none ${styles} ${sizeStyles} ${className}`}
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
    <div className={`card-surface overflow-hidden ${className}`}>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">{children}</table>
      </div>
    </div>
  );
}

export function Th({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <th
      className={`bg-slate-50 dark:bg-slate-900/80 border-b border-slate-200 dark:border-slate-800 px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 whitespace-nowrap align-middle ${className}`}
    >
      {children}
    </th>
  );
}

export function Td({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <td className={`border-t border-slate-100 dark:border-slate-800/80 px-4 py-3 text-slate-800 dark:text-slate-200 align-middle ${className}`}>
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
      <span className="absolute top-2 bottom-2 left-[3px] w-px bg-slate-200 dark:bg-slate-800" />
      {list.map((e, idx) => (
        <li key={e.id || idx} className="relative">
          <span className="absolute top-1.5 -left-[19px] size-2 rounded-full bg-blue-600 ring-4 ring-white dark:ring-slate-900" />
          <p className="font-semibold text-slate-900 dark:text-slate-100">{e.label}</p>
          {e.detail ? <p className="text-slate-600 dark:text-slate-400 text-[11px] mt-0.5">{e.detail}</p> : null}
          <p className="text-[10px] font-mono text-slate-400 dark:text-slate-500 mt-0.5">{e.at}</p>
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
    "card-surface p-4 min-w-0 transition-colors",
    selected ? "border-primary ring-2 ring-primary/20 bg-blue-50/50 dark:bg-blue-950/30" : "",
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
      <p role="status" aria-live="polite" className="text-sm text-slate-500 dark:text-slate-400 order-2 sm:order-1">
        Showing <span className="font-semibold text-slate-800 dark:text-slate-200">{start}</span>–<span className="font-semibold text-slate-800 dark:text-slate-200">{end}</span> of{" "}
        <span className="font-semibold text-slate-800 dark:text-slate-200">{totalCount}</span> {itemLabel}
      </p>
      <div className="flex items-center gap-2 order-1 sm:order-2 w-full sm:w-auto justify-between sm:justify-end">
        <button
          type="button"
          onClick={() => onPageChange(safePage - 1)}
          disabled={disabled || safePage <= 1}
          aria-label={`Go to previous page of ${itemLabel}`}
          className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 shadow-xs hover:bg-slate-50 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-100 disabled:pointer-events-none disabled:opacity-50 transition-colors cursor-pointer"
        >
          <ChevronLeft className="size-4" aria-hidden="true" />
          <span>Previous</span>
        </button>
        <span className="text-sm font-medium text-slate-600 dark:text-slate-400 px-2" aria-current="page">
          Page {safePage} of {totalPages}
        </span>
        <button
          type="button"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={disabled || currentPage >= totalPages}
          aria-label={`Go to next page of ${itemLabel}`}
          className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 shadow-xs hover:bg-slate-50 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-100 disabled:pointer-events-none disabled:opacity-50 transition-colors cursor-pointer"
        >
          <span>Next</span>
          <ChevronRight className="size-4" aria-hidden="true" />
        </button>
      </div>
    </nav>
  );
}
