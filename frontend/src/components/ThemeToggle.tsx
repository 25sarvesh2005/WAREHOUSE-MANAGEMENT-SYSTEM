import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/lib/theme-context";

export function ThemeToggle({
  className = "",
  showLabel = false,
}: {
  className?: string;
  showLabel?: boolean;
}) {
  const { resolvedTheme, toggleTheme } = useTheme();
  const isDark = resolvedTheme === "dark";

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
      title={isDark ? "Switch to light theme" : "Switch to dark theme"}
      className={`inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg border border-slate-200/80 bg-white p-2 text-slate-600 shadow-2xs transition-colors hover:bg-slate-100 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-slate-100 cursor-pointer ${className}`}
    >
      {isDark ? (
        <Sun className="size-4 shrink-0 text-amber-400 transition-transform hover:rotate-45" aria-hidden="true" />
      ) : (
        <Moon className="size-4 shrink-0 text-slate-700 transition-transform hover:-rotate-12" aria-hidden="true" />
      )}
      {showLabel ? (
        <span className="ml-2 text-xs font-semibold">
          {isDark ? "Light mode" : "Dark mode"}
        </span>
      ) : null}
    </button>
  );
}
