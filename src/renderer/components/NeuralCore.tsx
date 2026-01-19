/**
 * NeuralCore - Central Orbital Visualization
 * Premium "Cyberpunk" Edition
 */

import React from 'react';

type AgentName = 'ATLAS' | 'TETYANA' | 'GRISHA' | 'SYSTEM' | 'USER';
type SystemState = 'IDLE' | 'PROCESSING' | 'EXECUTING' | 'VERIFYING' | 'ERROR';

interface NeuralCoreProps {
  state: SystemState;
  activeAgent: AgentName;
}

const NeuralCore: React.FC<NeuralCoreProps> = ({ state, activeAgent }) => {
  // --- STATE COLORS ---
  const getStateColor = (): string => {
    switch (state) {
      case 'IDLE':
        return 'var(--state-idle)';
      case 'PROCESSING':
        return 'var(--state-processing)';
      case 'EXECUTING':
        return 'var(--state-executing)';
      case 'VERIFYING':
        return 'var(--state-processing)';
      case 'ERROR':
        return 'var(--state-error)';
      default:
        return 'var(--atlas-blue)';
    }
  };

  const getStateLabel = () => {
    switch (state) {
      case 'IDLE':
        return 'SYSTEM ONLINE';
      case 'PROCESSING':
        return 'THINKING_PROCES...';
      case 'EXECUTING':
        return 'EXECUTING PROTOCOL';
      case 'VERIFYING':
        return 'VAL_DATA_AUDIT';
      case 'ERROR':
        return 'CORE_FAILURE_ERR';
      default:
        return 'CORE_ACTIVE';
    }
  };

  // Use inline style for dynamic CSS variables
  const containerStyle = {
    color: getStateColor(),
  } as React.CSSProperties;

  return (
    <div className="neural-core transition-colors-slow" style={containerStyle}>
      <svg viewBox="-400 -400 800 800" className="orbital-svg">
        <defs>
          <filter id="glow-core">
            <feGaussianBlur stdDeviation="5" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <radialGradient id="grad-core" cx="0.5" cy="0.5" r="0.5">
            <stop offset="0%" stopColor="currentColor" stopOpacity="0.6" />
            <stop offset="60%" stopColor="currentColor" stopOpacity="0.2" />
            <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* --- DECORATIVE OUTER RINGS --- */}
        <circle r="380" fill="none" stroke="currentColor" strokeWidth="0.5" opacity="0.05" />
        <circle r="340" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.1" strokeDasharray="2 10" />

        {/* --- DATA FLOW RINGS --- */}
        
        {/* Outer orbital (300) - Data Nodes */}
        <g className="animate-spin-slow origin-center">
            <circle r="300" fill="none" stroke="currentColor" strokeWidth="0.5" opacity="0.1" strokeDasharray="1 150" />
            <circle cx="300" cy="0" r="3" fill="currentColor" opacity="0.4" />
            <circle cx="-300" cy="0" r="3" fill="currentColor" opacity="0.4" />
        </g>

        {/* Layer 2 (250) - Dashed Pulse */}
        <g className="animate-spin-ccw-slow origin-center">
          <circle r="250" fill="none" stroke="currentColor" strokeWidth="1" strokeDasharray="100 200" opacity="0.2" />
          <circle cx="0" cy="250" r="2" fill="currentColor" />
        </g>

        {/* Layer 3 (200) - Middle Orbital */}
        <g className="animate-spin-medium origin-center">
          <circle r="190" fill="none" stroke="currentColor" strokeWidth="3" strokeDasharray="10 370" opacity="0.5" />
          <circle r="185" fill="none" stroke="currentColor" strokeWidth="1" strokeDasharray="50 50" opacity="0.1" />
        </g>

        {/* Inner Logic Ring (130) */}
        <g className="animate-spin-ccw-medium origin-center-130">
           <circle r="130" fill="none" stroke="currentColor" strokeWidth="1" strokeDasharray="5 5" opacity="0.3" />
        </g>

        {/* Inner Logic Ring (100) */}
        <g className="animate-spin-fast origin-center">
          <circle r="100" fill="none" stroke="currentColor" strokeWidth="2" strokeDasharray="80 120" opacity="0.6" />
        </g>

        {/* --- CENTRAL CORE --- */}
        <g className="core-group" filter="url(#glow-core)">
          {/* Multi-layered pulse */}
          <circle r="60" fill="url(#grad-core)" className="animate-pulse" />
          <circle r="35" fill="none" stroke="currentColor" strokeWidth="0.5" className="animate-pulse-slow" />
          <circle r="15" fill="currentColor" className="animate-pulse-fast" />
          <circle r="5" fill="#fff" opacity="0.9" />
          
          {/* Core Crosshair */}
          <line x1="-20" y1="0" x2="20" y2="0" stroke="currentColor" strokeWidth="0.5" opacity="0.5" />
          <line x1="0" y1="-20" x2="0" y2="20" stroke="currentColor" strokeWidth="0.5" opacity="0.5" />
        </g>

        {/* --- AGENT NODES --- */}
        {/* ATLAS */}
        <g>
          <line x1="0" y1="-60" x2="0" y2="-170" stroke="var(--atlas-blue)" strokeWidth="0.5" opacity={activeAgent === 'ATLAS' ? 0.6 : 0.1} />
          <circle cx="0" cy="-180" r={activeAgent === 'ATLAS' ? 10 : 4} fill="var(--atlas-blue)" className={activeAgent === 'ATLAS' ? 'animate-pulse' : ''} />
          <text x="0" y="-205" textAnchor="middle" fill="var(--atlas-blue)" fontSize="9" fontWeight="bold" letterSpacing="3" opacity={activeAgent === 'ATLAS' ? 1 : 0.3}>ATLAS</text>
        </g>

        {/* GRISHA */}
        <g transform="rotate(120)">
           <line x1="0" y1="-60" x2="0" y2="-170" stroke="var(--grisha-orange)" strokeWidth="0.5" opacity={activeAgent === 'GRISHA' ? 0.6 : 0.1} />
           <g transform="translate(0, -180)">
             <circle r={activeAgent === 'GRISHA' ? 10 : 4} fill="var(--grisha-orange)" transform="rotate(-120)" className={activeAgent === 'GRISHA' ? 'animate-pulse' : ''} />
             <text y="25" transform="rotate(-120)" textAnchor="middle" fill="var(--grisha-orange)" fontSize="9" fontWeight="bold" letterSpacing="3" opacity={activeAgent === 'GRISHA' ? 1 : 0.3}>GRISHA</text>
           </g>
        </g>

        {/* TETYANA */}
        <g transform="rotate(240)">
           <line x1="0" y1="-60" x2="0" y2="-170" stroke="var(--tetyana-green)" strokeWidth="0.5" opacity={activeAgent === 'TETYANA' ? 0.6 : 0.1} />
           <g transform="translate(0, -180)">
              <circle r={activeAgent === 'TETYANA' ? 10 : 4} fill="var(--tetyana-green)" transform="rotate(-240)" className={activeAgent === 'TETYANA' ? 'animate-pulse' : ''} />
              <text y="25" transform="rotate(-240)" textAnchor="middle" fill="var(--tetyana-green)" fontSize="9" fontWeight="bold" letterSpacing="3" opacity={activeAgent === 'TETYANA' ? 1 : 0.3}>TETYANA</text>
           </g>
        </g>
      </svg>

      {/* --- RECTANGULAR STATUS INDICATOR --- */}
      <div className="status-indicator">
        <div className="status-glow"></div>
        <div className="status-box">
          <span className="status-text">{getStateLabel()}</span>
        </div>
      </div>

      <style>{`
                .neural-core {
                    position: relative;
                    width: 100%;
                    height: 100%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    overflow: visible;
                }
                .orbital-svg {
                    width: 480px;
                    height: 480px;
                    max-width: 90%;
                    max-height: 90%;
                }
                .status-indicator {
                    position: absolute;
                    bottom: 12%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .status-box {
                    position: relative;
                    padding: 10px 30px;
                    background: rgba(0, 0, 0, 0.9);
                    border: 1.5px solid currentColor;
                    box-shadow: 0 0 15px currentColor, inset 0 0 5px currentColor;
                    z-index: 2;
                }
                .status-glow {
                    position: absolute;
                    width: 120%;
                    height: 140%;
                    background: currentColor;
                    filter: blur(30px);
                    opacity: 0.45;
                    z-index: 1;
                }
                .status-text {
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 14px;
                    font-weight: 700;
                    letter-spacing: 4px;
                    color: currentColor;
                    text-transform: uppercase;
                    text-shadow: 0 0 8px currentColor;
                }
                /* Custom CCW rotation for inner rings */
                @keyframes spin-ccw {
                    from { transform: rotate(360deg); }
                    to { transform: rotate(0deg); }
                }
                .animate-spin-ccw-medium {
                    animation: spin-ccw 8s linear infinite;
                }
            `}</style>
    </div>
  );
};

export default NeuralCore;
