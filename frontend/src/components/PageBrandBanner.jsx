import React from "react";

export default function PageBrandBanner({ title, description }) {
  return (
    <div className="mb-6 brutal-card p-4 brand-panel flex items-center justify-between gap-4">
      <div className="flex items-center gap-3 min-w-0">
        <div className="min-w-0 font-mono text-xs text-zinc-400">
          <div className="uppercase tracking-[0.35em] text-[#C4B5FD]">{title}</div>
          <div className="truncate text-zinc-500">{description}</div>
        </div>
      </div>
    </div>
  );
}
