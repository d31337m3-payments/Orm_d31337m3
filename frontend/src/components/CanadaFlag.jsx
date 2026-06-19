import React from "react";

// Inline SVG of the Canadian flag — brutalist, no external img
export default function CanadaFlag({ size = 16, className = "" }) {
  return (
    <svg
      viewBox="0 0 200 100"
      width={size * 2}
      height={size}
      className={className}
      aria-label="Made in Canada"
    >
      <rect x="0" y="0" width="50" height="100" fill="#FF0000" />
      <rect x="150" y="0" width="50" height="100" fill="#FF0000" />
      <rect x="50" y="0" width="100" height="100" fill="#FFFFFF" />
      <path
        d="M100 20 L107 38 L125 32 L118 50 L135 55 L120 65 L125 78 L107 73 L107 85 L100 80 L93 85 L93 73 L75 78 L80 65 L65 55 L82 50 L75 32 L93 38 Z"
        fill="#FF0000"
      />
    </svg>
  );
}
