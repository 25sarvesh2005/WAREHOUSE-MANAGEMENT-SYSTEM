import { STATUS_BADGE_CLASSES, STATUS_BADGE_COLORS } from "@/components/StatusBadge.constants";

export function StatusBadge({ value, className = "" }: { value: string; className?: string }) {
  const tone = STATUS_BADGE_COLORS[value] ?? "gray";
  const badgeStyle = STATUS_BADGE_CLASSES[tone] ?? STATUS_BADGE_CLASSES["gray"];

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs tracking-tight whitespace-nowrap ${badgeStyle} ${className}`}
    >
      <span className="size-1.5 rounded-full bg-current opacity-80" />
      <span>{value.replaceAll("_", " ")}</span>
    </span>
  );
}

export function FacilityBadge({ code, className = "" }: { code: string; className?: string }) {
  const isReno = code.toUpperCase().includes("RNO") || code.toUpperCase().includes("RENO");
  const isColumbus = code.toUpperCase().includes("CMH") || code.toUpperCase().includes("COLUMBUS");

  if (isReno) {
    return (
      <span
        className={`inline-flex items-center gap-1 rounded-md bg-cyan-50 px-2 py-0.5 text-xs font-semibold text-cyan-800 border border-cyan-200 ${className}`}
      >
        <span className="size-1.5 rounded-full bg-cyan-600" />
        {code} (Reno, NV)
      </span>
    );
  }

  if (isColumbus) {
    return (
      <span
        className={`inline-flex items-center gap-1 rounded-md bg-amber-50 px-2 py-0.5 text-xs font-semibold text-amber-800 border border-amber-200 ${className}`}
      >
        <span className="size-1.5 rounded-full bg-amber-600" />
        {code} (Columbus, OH)
      </span>
    );
  }

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-700 border border-slate-200 ${className}`}
    >
      <span className="size-1.5 rounded-full bg-slate-500" />
      {code}
    </span>
  );
}
