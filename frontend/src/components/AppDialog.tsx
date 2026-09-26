import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

export interface AppDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
  contentClassName?: string;
  preventCloseWhilePending?: boolean;
  pending?: boolean;
  returnFocusRef?: React.RefObject<HTMLElement | null>;
}

export function AppDialog({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
  className,
  contentClassName,
  preventCloseWhilePending = true,
  pending = false,
  returnFocusRef,
}: AppDialogProps) {
  const isCloseBlocked = pending && preventCloseWhilePending;

  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen && isCloseBlocked) {
      return;
    }
    onOpenChange(nextOpen);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent
        showCloseButton={false}
        className={cn(
          "max-w-lg w-[calc(100%-2rem)] max-h-[calc(100dvh-2rem)] md:max-h-[85vh] p-0 flex flex-col overflow-hidden rounded-2xl border border-border bg-card shadow-panel",
          className,
        )}
        onCloseAutoFocus={(event) => {
          const target = returnFocusRef?.current;
          if (target?.isConnected) {
            event.preventDefault();
            target.focus();
          }
        }}
        onEscapeKeyDown={(e) => {
          if (isCloseBlocked) {
            e.preventDefault();
          }
        }}
        onPointerDownOutside={(e) => {
          if (isCloseBlocked) {
            e.preventDefault();
          }
        }}
      >
        <DialogHeader className="px-6 pt-5 pb-3 text-left border-b border-border/80 shrink-0">
          <div className="flex items-center justify-between gap-4 pr-8">
            <DialogTitle className="text-lg font-bold tracking-tight text-foreground">
              {title}
            </DialogTitle>
          </div>
          {description ? (
            <DialogDescription className="text-xs text-muted-foreground mt-1">
              {description}
            </DialogDescription>
          ) : (
            <DialogDescription className="sr-only">{title}</DialogDescription>
          )}
        </DialogHeader>

        <div className={cn("p-6 overflow-y-auto flex-1 min-h-0", contentClassName)}>
          {children}
        </div>

        {footer ? (
          <DialogFooter className="px-6 py-4 border-t border-border/80 bg-muted/30 shrink-0 sm:justify-end gap-2">
            {footer}
          </DialogFooter>
        ) : null}

        {!isCloseBlocked && (
          <DialogPrimitive.Close
            type="button"
            aria-label="Close dialog"
            className="absolute right-2 top-2 flex size-11 min-h-[44px] min-w-[44px] items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 cursor-pointer"
          >
            <X className="size-4" />
            <span className="sr-only">Close dialog</span>
          </DialogPrimitive.Close>
        )}
      </DialogContent>
    </Dialog>
  );
}
