"use client";

import { useEffect, useRef, useState } from "react";
import { Popover, PopoverContent } from "@/components/ui/popover";
import { Button } from "@/components/ui/button";

export function SelectionPopover({ addData }: {
  data: string[],
  addData: (d: string) => void
}) {
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState<{ x: number; y: number } | null>(null);
  const [text, setText] = useState("");
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleMouseUp = (e: any) => {
      if (popoverRef.current?.contains(e.target as Node)) return;

      const selection = window.getSelection();
      if (selection && !selection.isCollapsed) {
        const range = selection.getRangeAt(0);
        const rect = range.getBoundingClientRect();
        setPosition({ x: rect.left + rect.width / 2, y: rect.top - 10 });
        setText(selection.toString());
        setOpen(true);
      } else {
        setOpen(false);
      }
    };

    document.addEventListener("mouseup", handleMouseUp);
    return () => document.removeEventListener("mouseup", handleMouseUp);
  }, []);

  if (!position) return null;

  return (
    <Popover open={open}>
      <PopoverContent 
        ref={popoverRef}
        side="right"
        align="center"
        className="p-2 text-sm shadow-md border-none shadow-none"
        style={{
          background: 'none',
          position: "fixed",
          left: position.x,
          top: position.y,
          transform: "translate(-50%, -100%)",
        }}
      >
        <Button size="sm" variant="default" onClick={() => {
          addData(text);
          setOpen(false);
        }}>
          Save
        </Button>
      </PopoverContent>
    </Popover>
  );
}
