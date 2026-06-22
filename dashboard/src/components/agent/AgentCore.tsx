"use client";

import { memo } from "react";

export type CoreState = "idle" | "thinking";

/**
 * The Arad Agent Core — the signature animated mark of the quality agent.
 *
 * A faceted intelligence core inside concentric measurement rings, with data
 * nodes orbiting on each ring and instrument crosshairs at the cardinal points.
 * Pure SVG + CSS so it stays razor-sharp at any size and animates live.
 *
 *  - `idle`     : slow, calm rotation — the agent at rest.
 *  - `thinking` : rings accelerate, pulse rings emit, the core breathes brighter.
 *
 * Set `animated={false}` for repeated/static contexts (e.g. message avatars)
 * to keep the render cheap.
 */
export const AgentCore = memo(function AgentCore({
  size = 120,
  state = "idle",
  animated = false,
  className,
}: {
  size?: number;
  state?: CoreState;
  animated?: boolean;
  className?: string;
}) {
  const thinking = state === "thinking";
  const spin = animated ? "ac-spin" : "";
  const spinRev = animated ? "ac-spin-rev" : "";

  // Ring rotation periods (seconds). Thinking accelerates everything.
  const dOuter = thinking ? 13 : 26;
  const dMid = thinking ? 8 : 15;
  const dInner = thinking ? 9 : 18;
  const dInnerNode = thinking ? 5.5 : 11;
  const dSweep = thinking ? 3.6 : 7;

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 120 120"
      fill="none"
      className={className}
      role="img"
      aria-label="Arad agent core"
      style={{ overflow: "visible", display: "block" }}
    >
      <defs>
        <radialGradient id="ac-core" cx="50%" cy="40%" r="62%">
          <stop offset="0%" stopColor="#e6efff" />
          <stop offset="44%" stopColor="#82aeff" />
          <stop offset="100%" stopColor="#7c4dff" />
        </radialGradient>
        <linearGradient id="ac-ring" x1="6" y1="6" x2="114" y2="114" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#4e8cff" />
          <stop offset="100%" stopColor="#8b5cf6" />
        </linearGradient>
        <filter id="ac-glow" x="-70%" y="-70%" width="240%" height="240%">
          <feGaussianBlur stdDeviation="2.6" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Pulse rings — emitted only while thinking */}
      {animated && thinking && (
        <>
          <circle cx="60" cy="60" r="31" stroke="url(#ac-ring)" strokeWidth="1.2" className="ac-pulse" />
          <circle
            cx="60"
            cy="60"
            r="31"
            stroke="url(#ac-ring)"
            strokeWidth="1"
            className="ac-pulse"
            style={{ animationDelay: "1.2s" }}
          />
        </>
      )}

      {/* Radar sweep wedge */}
      <g
        className={`ac-rot ${spin}`}
        style={animated ? { animationDuration: `${dSweep}s` } : undefined}
      >
        <path d="M60 60 L60 9 A51 51 0 0 1 102 37 Z" fill="url(#ac-ring)" opacity={thinking ? 0.17 : 0.07} />
      </g>

      {/* Outer dashed ring */}
      <circle
        cx="60"
        cy="60"
        r="50"
        stroke="url(#ac-ring)"
        strokeOpacity="0.5"
        strokeWidth="1"
        strokeDasharray="2 7"
        className={`ac-rot ${spin}`}
        style={animated ? { animationDuration: `${dOuter}s` } : undefined}
      />

      {/* Instrument crosshair ticks */}
      <g stroke="#9ec2ff" strokeOpacity="0.6" strokeWidth="1.4" strokeLinecap="round">
        <line x1="60" y1="1.5" x2="60" y2="9" />
        <line x1="60" y1="111" x2="60" y2="118.5" />
        <line x1="1.5" y1="60" x2="9" y2="60" />
        <line x1="111" y1="60" x2="118.5" y2="60" />
      </g>

      {/* Mid ring + two orbiting data nodes */}
      <circle cx="60" cy="60" r="40" stroke="url(#ac-ring)" strokeOpacity="0.32" strokeWidth="1" />
      <g
        className={`ac-rot ${spin}`}
        style={animated ? { animationDuration: `${dMid}s` } : undefined}
      >
        <circle cx="60" cy="20" r="3" fill="#9ec2ff" filter="url(#ac-glow)" />
        <circle cx="60" cy="100" r="2.2" fill="#b39dff" filter="url(#ac-glow)" />
      </g>

      {/* Inner dashed ring (counter-rotating) + cyan telemetry node */}
      <circle
        cx="60"
        cy="60"
        r="29"
        stroke="url(#ac-ring)"
        strokeOpacity="0.42"
        strokeWidth="1"
        strokeDasharray="1.5 6"
        className={`ac-rot ${spinRev}`}
        style={animated ? { animationDuration: `${dInner}s` } : undefined}
      />
      <g
        className={`ac-rot ${spinRev}`}
        style={animated ? { animationDuration: `${dInnerNode}s` } : undefined}
      >
        <circle cx="89" cy="60" r="2.4" fill="#22d3ee" filter="url(#ac-glow)" />
      </g>

      {/* Faceted core */}
      <g filter="url(#ac-glow)" className={animated && thinking ? "ac-breathe" : undefined} style={{ transformBox: "view-box", transformOrigin: "60px 60px" }}>
        <path
          d="M72 60 L66 70.39 L54 70.39 L48 60 L54 49.61 L66 49.61 Z"
          fill="url(#ac-core)"
          stroke="#d7e6ff"
          strokeOpacity="0.45"
          strokeWidth="0.8"
        />
        <path d="M60 49.61 L60 70.39 M54 49.61 L66 70.39 M66 49.61 L54 70.39" stroke="#ffffff" strokeOpacity="0.18" strokeWidth="0.6" />
        <circle cx="60" cy="60" r="2.6" fill="#ffffff" />
      </g>
    </svg>
  );
});
