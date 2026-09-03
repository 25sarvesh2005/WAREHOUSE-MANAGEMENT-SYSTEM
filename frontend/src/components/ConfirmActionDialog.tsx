import * as React from "react";
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui-kit";
import { cn } from "@/lib/utils";

export interface ConfirmActionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  recordIdentifier?: string;
  confirmLabel: string;
  cancelLabel?: string;
  destructive?: boolean;
  pending?: boolean;
  onConfirm: () => void | Promise<void>;
}

export function ConfirmActionDialog({
  open,
  onOpenChange,
  title,
  description,
  recordIdentifier,
  confirmLabel,
  cancelLabel = "Cancel",
  destructive = false,
  pending = false,
  onConfirm,
}: ConfirmActionDialogProps) {
  const isSubmitting = React.useRef(false);

  const handleConfirm = async () => {
    if (pending || isSubmitting.current) return;
    isSubmitting.current = true;
    try {
      await onConfirm();
    } finally {
      isSubmitting.current = false;
    }
  };

  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen && pending) {
      return;
    }
    onOpenChange(nextOpen);
  };

  return (
    <AlertDialog open={open} onOpenChange={handleOpenChange}>
      <AlertDialogContent
        className={cn(
          "max-w-md w-[calc(100%-2rem)] p-6 rounded-2xl border border-border bg-card shadow-panel",
        )}
      >
        <AlertDialogHeader className="text-left space-y-2">
          <AlertDialogTitle className="text-lg font-bold tracking-tight text-foreground">
            {title}
          </AlertDialogTitle>
          {recordIdentifier ? (
            <div className="inline-flex items-center gap-1.5 rounded-lg bg-muted px-2.5 py-1 font-mono text-xs font-semibold text-foreground border border-border/80 max-w-fit">
              <span>Record:</span>
              <span className="text-primary">{recordIdentifier}</span>
            </div>
          ) : null}
          <AlertDialogDescription className="text-sm text-muted-foreground leading-relaxed">
            {description}
          </AlertDialogDescription>
        </AlertDialogHeader>

        <AlertDialogFooter className="mt-6 flex flex-col-reverse sm:flex-row sm:justify-end gap-2">
          <Button
            type="button"
            variant="outline"
            disabled={pending}
            onClick={() => onOpenChange(false)}
            className="w-full sm:w-auto"
          >
            {cancelLabel}
          </Button>

          <Button
            type="button"
            variant={destructive ? "danger" : "primary"}
            loading={pending}
            loadingLabel={confirmLabel}
            onClick={handleConfirm}
            className="w-full sm:w-auto"
          >
            {confirmLabel}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
