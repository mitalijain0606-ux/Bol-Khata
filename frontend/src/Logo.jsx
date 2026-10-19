import React from "react";

// Bol-Khata logo: a clean microphone — "ye app bolke chalti hai" at first glance.
export default function Logo({ size = 42, radius = 14 }) {
  return (
    <div
      className="logo-mark"
      style={{ width: size, height: size, borderRadius: radius }}
      aria-label="Bol-Khata"
    >
      <svg viewBox="0 0 24 24" fill="none" width={size * 0.62} height={size * 0.62}>
        <rect x="9" y="2.5" width="6" height="11" rx="3" fill="#fff" />
        <path d="M5.5 11a6.5 6.5 0 0 0 13 0" stroke="#fff" strokeWidth="2" strokeLinecap="round" />
        <line x1="12" y1="17.5" x2="12" y2="20.5" stroke="#fff" strokeWidth="2" strokeLinecap="round" />
        <line x1="8.8" y1="20.8" x2="15.2" y2="20.8" stroke="#fff" strokeWidth="2" strokeLinecap="round" />
      </svg>
    </div>
  );
}
