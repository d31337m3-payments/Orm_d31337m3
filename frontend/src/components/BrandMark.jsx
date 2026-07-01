import React from "react";

const BrandMark = ({ size = 44, theme = "dark", showWordmark = true, showSubmark = false, className = "" }) => {
  const muted = theme === "light" ? "#6B7280" : "#C4B5FD";
  const iconColor = theme === "light" ? "#111827" : "#FFFFFF";
  const iconSize = Number(size) || 44;

  return (
    <div className={`inline-flex items-center gap-3 ${className}`.trim()} aria-label="d31337m3 brand mark">
      <div
        style={{ width: iconSize, height: iconSize, fontSize: Math.round(iconSize * 0.35) }}
        className="rounded-md bg-purple-600 flex items-center justify-center text-white font-bold select-none"
      >
        D3
      </div>

      {showWordmark && (
        <div className="flex flex-col leading-none">
          <span style={{ fontSize: Math.round(iconSize * 0.4), color: iconColor }} className="font-bold leading-none select-none">
            d31337m3
          </span>
          {showSubmark && <span className="font-mono text-[9px] uppercase tracking-[0.32em]" style={{ color: muted }}>privacy ops platform</span>}
        </div>
      )}
    </div>
  );
};

export default BrandMark;
