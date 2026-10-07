"use client";

import { X } from "lucide-react";
import { useEffect, useId, useRef } from "react";

type DialogProps = {
  open: boolean;
  title: string;
  eyebrow?: string;
  onClose: () => void;
  children: React.ReactNode;
  className?: string;
};

export function Dialog({ open, title, eyebrow, onClose, children, className = "" }: DialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const closeCallback = useRef(onClose);
  const ignoreNextClose = useRef(false);
  const titleId = useId();

  useEffect(() => {
    closeCallback.current = onClose;
  }, [onClose]);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    const handleClose = () => {
      if (ignoreNextClose.current) {
        ignoreNextClose.current = false;
        return;
      }
      closeCallback.current();
    };
    dialog.addEventListener("close", handleClose);
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const previousOverflow = document.body.style.overflow;

    if (open && !dialog.open) {
      dialog.showModal();
      document.body.style.overflow = "hidden";
    } else if (!open && dialog.open) {
      ignoreNextClose.current = true;
      dialog.close();
    }

    return () => {
      dialog.removeEventListener("close", handleClose);
      if (dialog.open) {
        ignoreNextClose.current = true;
        dialog.close();
      }
      document.body.style.overflow = previousOverflow;
      if (open) previousFocus?.focus();
    };
  }, [open]);

  return (
    <dialog
      ref={dialogRef}
      className={`dialog-backdrop ${className}`}
      aria-labelledby={titleId}
      onClick={(event) => {
        if (event.target === dialogRef.current) dialogRef.current?.close();
      }}
    >
      <section className="dialog-panel">
        <header className="dialog-heading">
          <div>
            {eyebrow && <p className="eyebrow dialog-eyebrow">{eyebrow}</p>}
            <h2 id={titleId} className="font-head dialog-title">{title}</h2>
          </div>
          <button className="icon-button dialog-close" type="button" onClick={() => dialogRef.current?.close()} aria-label="Cerrar ventana">
            <X size={20} aria-hidden="true" />
          </button>
        </header>
        {children}
      </section>
    </dialog>
  );
}
