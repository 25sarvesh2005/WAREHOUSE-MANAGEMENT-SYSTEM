import { STATUS_BADGE_CLASSES, STATUS_BADGE_COLORS } from "@/components/StatusBadge.constants";

export function StatusBadge({ value, className = "" }: { value: string; className?: string }) {
  const tone = STATUS_BADGE_COLORS[value] ?? "gray";
  const badgeStyle = STATUS_BADGE_CLASSES[tone] ?? STATUS_BADGE_CLASSES["gray"];

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs font-medium tracking-normal whitespace-nowrap shrink-0 ${badgeStyle} ${className}`}
    >
      <span className="size-1.5 rounded-full bg-current opacity-80 shrink-0" />
      <span>{value.replaceAll("_", " ")}</span>
    </span>
  );
}

export function FacilityBadge({
  code,
  compact = false,
  className = "",
}: {
  code: string;
  compact?: boolean;
  className?: string;
}) {
  const isReno = code.toUpperCase().includes("RNO") || code.toUpperCase().includes("RENO");
  const isColumbus = code.toUpperCase().includes("CMH") || code.toUpperCase().includes("COLUMBUS");

  if (isReno) {
    return (
      <span
        title="Reno, NV"
        className={`inline-flex items-center gap-1.5 rounded-md bg-cyan-50 dark:bg-cyan-950/60 px-2 py-0.5 text-xs font-medium text-cyan-800 dark:text-cyan-300 border border-cyan-200 dark:border-cyan-800/70 whitespace-nowrap shrink-0 ${className}`}
      >
        <span className="size-1.5 rounded-full bg-cyan-600 dark:bg-cyan-400 shrink-0" />
        {compact ? code : `${code} (Reno, NV)`}
      </span>
    );
  }

  if (isColumbus) {
    return (
      <span
        title="Columbus, OH"
        className={`inline-flex items-center gap-1.5 rounded-md bg-amber-50 dark:bg-amber-950/60 px-2 py-0.5 text-xs font-medium text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800/70 whitespace-nowrap shrink-0 ${className}`}
      >
        <span className="size-1.5 rounded-full bg-amber-600 dark:bg-amber-400 shrink-0" />
        {compact ? code : `${code} (Columbus, OH)`}
      </span>
    );
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-xs font-medium text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 whitespace-nowrap shrink-0 ${className}`}
    >
      <span className="size-1.5 rounded-full bg-slate-500 dark:bg-slate-400 shrink-0" />
      {code}
    </span>
  );
}
