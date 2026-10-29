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
    primary: "bg-blue-50 text-blue-700 border border-blue-200/80",
    emerald: "bg-emerald-50 text-emerald-700 border border-emerald-200/80",
    amber: "bg-amber-50 text-amber-800 border border-amber-200/80",
    rose: "bg-rose-50 text-rose-700 border border-rose-200/80",
    slate: "bg-slate-100 text-slate-700 border border-slate-200/80",
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

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`card-surface p-5 rounded-xl ${className}`}>{children}</div>;
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
        <label htmlFor={htmlFor} className="block text-xs font-semibold text-slate-700">
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
      className={`w-full min-h-[42px] rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-sm text-foreground shadow-xs outline-none transition-all placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary/15 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:opacity-60 ${className}`}
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
      className={`w-full min-h-[42px] rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-sm font-medium text-foreground shadow-xs outline-none transition-all focus:border-primary focus:ring-2 focus:ring-primary/15 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:opacity-60 ${className}`}
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
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 md:text-3xl">
            {title}
          </h1>
          {facilityTag}
        </div>
        {subtitle ? (
          <p className="mt-1 max-w-3xl text-sm text-slate-500">{subtitle}</p>
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
      <span className="flex size-14 items-center justify-center rounded-xl bg-slate-100 text-slate-600 border border-slate-200">
        <Icon className="size-6" aria-hidden="true" />
      </span>
      <p className="text-sm font-semibold text-slate-900">{message}</p>
      {hint ? <p className="max-w-md text-sm text-slate-500">{hint}</p> : null}
    </div>
  );
}

export function LoadingState({ message = "Loading operational data..." }: { message?: string }) {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="true"
      className="flex items-center justify-center gap-2 px-6 py-16 text-sm text-slate-500"
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
      className="my-4 rounded-xl border border-rose-200 bg-rose-50/80 p-4 text-sm text-rose-800"
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
            className="min-h-[44px] inline-flex items-center justify-center rounded-lg border border-rose-300 bg-white px-3.5 py-1.5 text-xs font-semibold text-rose-700 shadow-xs transition-colors hover:bg-rose-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-500/30 cursor-pointer"
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
    <div className="mb-5 flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50/90 px-4 py-3 text-sm text-amber-900 shadow-xs">
      <TriangleAlert className="mt-0.5 size-4 shrink-0 text-amber-600" aria-hidden="true" />
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
    <div className="mb-5 flex items-center gap-2.5 rounded-xl border border-blue-200 bg-blue-50/80 px-4 py-3 text-sm text-blue-900 shadow-xs">
      <Database className="size-4 shrink-0 text-blue-600" aria-hidden="true" />
      <span>
        <strong className="font-semibold text-blue-950">Ledger-backed truth:</strong> {message}
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
    <div className="mb-4 flex items-center gap-2.5 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-800 shadow-xs">
      <ShieldCheck className="size-4 shrink-0 text-slate-600" aria-hidden="true" />
      <span>
        <strong className="font-semibold text-slate-900">Duplicate safe:</strong> {message}
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
      <Barcode className="pointer-events-none absolute left-3 size-4 text-slate-400" aria-hidden="true" />
      <input
        type="text"
        value={value}
        onChange={onChange}
        onKeyDown={onKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        autoFocus={autoFocus}
        aria-label={ariaLabel}
        className="w-full rounded-lg border border-slate-300 bg-white py-2 pr-3.5 pl-9 font-mono text-sm font-semibold text-slate-900 shadow-xs outline-none placeholder:font-sans placeholder:font-normal placeholder:text-slate-400 transition-colors focus:border-primary focus:ring-2 focus:ring-primary/15 disabled:bg-slate-50 disabled:text-slate-400"
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
      "bg-primary text-primary-foreground hover:bg-primary-dark border border-blue-700/30 font-semibold shadow-[inset_0_1px_0_rgba(255,255,255,0.2),0_1px_2px_rgba(37,99,235,0.25)] hover:shadow-[0_2px_4px_rgba(37,99,235,0.3)] active:bg-blue-800 active:scale-[0.99] focus-visible:ring-primary/30",
    secondary:
      "bg-slate-100 text-slate-800 hover:bg-slate-200/80 active:bg-slate-200 border border-slate-200/80 font-semibold focus-visible:ring-slate-400/30",
    outline:
      "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 hover:text-slate-900 active:bg-slate-100 font-semibold shadow-xs focus-visible:ring-primary/30",
    danger:
      "bg-destructive text-destructive-foreground hover:bg-red-700 active:bg-red-800 border border-red-700/30 font-semibold shadow-[0_1px_2px_rgba(220,38,38,0.2)] focus-visible:ring-destructive/30",
    ghost:
      "text-slate-600 hover:text-slate-900 hover:bg-slate-100 active:bg-slate-200 font-medium border border-transparent focus-visible:ring-slate-400/30",
  }[variant];

  const sizeStyles = {
    sm: "px-3 py-1.5 text-xs rounded-md gap-1.5",
    md: "px-3.5 py-2 text-sm rounded-lg gap-2",
    lg: "px-4.5 py-2.5 text-sm rounded-lg gap-2.5",
  }[size];

  const isDisabled = disabled || loading;

  return (
    <button
      disabled={isDisabled}
      aria-busy={loading ? "true" : undefined}
      className={`inline-flex cursor-pointer items-center justify-center transition-all duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none ${styles} ${sizeStyles} ${className}`}
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
    <div className={`card-surface overflow-hidden rounded-xl border border-slate-200 ${className}`}>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">{children}</table>
      </div>
    </div>
  );
}

export function Th({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <th
      className={`bg-slate-50/90 border-b border-slate-200 px-4 py-3 text-left text-[11px] font-semibold tracking-wider text-slate-500 uppercase whitespace-nowrap align-middle ${className}`}
    >
      {children}
    </th>
  );
}

export function Td({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <td className={`border-t border-slate-100 px-4 py-3 text-slate-800 align-middle transition-colors hover:bg-slate-50/50 ${className}`}>
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
          <span className="absolute top-1.5 -left-[19px] size-2 rounded-full bg-blue-600 ring-4 ring-white" />
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
    "card-surface p-4 min-w-0 transition-colors rounded-xl",
    selected ? "border-primary ring-2 ring-primary/20 bg-blue-50/50" : "",
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
      <p role="status" aria-live="polite" className="text-sm text-slate-500 order-2 sm:order-1">
        Showing <span className="font-semibold text-slate-800">{start}</span>–<span className="font-semibold text-slate-800">{end}</span> of{" "}
        <span className="font-semibold text-slate-800">{totalCount}</span> {itemLabel}
      </p>
      <div className="flex items-center gap-2 order-1 sm:order-2 w-full sm:w-auto justify-between sm:justify-end">
        <button
          type="button"
          onClick={() => onPageChange(safePage - 1)}
          disabled={disabled || safePage <= 1}
          aria-label={`Go to previous page of ${itemLabel}`}
          className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-xs hover:bg-slate-50 hover:text-slate-900 disabled:pointer-events-none disabled:opacity-50 transition-colors cursor-pointer"
        >
          <ChevronLeft className="size-4" aria-hidden="true" />
          <span>Previous</span>
        </button>
        <span className="text-sm font-medium text-slate-600 px-2" aria-current="page">
          Page {safePage} of {totalPages}
        </span>
        <button
          type="button"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={disabled || currentPage >= totalPages}
          aria-label={`Go to next page of ${itemLabel}`}
          className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-xs hover:bg-slate-50 hover:text-slate-900 disabled:pointer-events-none disabled:opacity-50 transition-colors cursor-pointer"
        >
          <span>Next</span>
          <ChevronRight className="size-4" aria-hidden="true" />
        </button>
      </div>
    </nav>
  );
}
