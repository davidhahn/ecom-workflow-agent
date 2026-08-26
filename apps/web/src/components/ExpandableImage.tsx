"use client";

import { useEffect, useState } from "react";

// The architecture diagram is an Excalidraw export with small embedded text.
// CSS can't grow that text independently of the image, so the fix is a
// bigger default size plus a click-to-enlarge view instead of a font change.
export function ExpandableImage({
  src,
  alt,
  className,
}: {
  src: string;
  alt: string;
  className?: string;
}) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open]);

  return (
    <>
      {/* eslint-disable-next-line @next/next/no-img-element -- static SVG, no optimization needed */}
      <img
        src={src}
        alt={alt}
        onClick={() => setOpen(true)}
        className={`cursor-zoom-in ${className ?? ""}`}
      />
      {open && (
        <div
          role="dialog"
          aria-modal="true"
          onClick={() => setOpen(false)}
          className="fixed inset-0 z-50 flex cursor-zoom-out items-center justify-center bg-black/80 p-4"
        >
          {/* eslint-disable-next-line @next/next/no-img-element -- static SVG, no optimization needed */}
          <img
            src={src}
            alt={alt}
            className="max-h-full max-w-full rounded-md bg-white dark:bg-gray-900"
          />
        </div>
      )}
    </>
  );
}
