/**
 * MapView - Cyberpunk Map Visualization
 * Displays Street View and Static Maps with "hacker-style" aesthetic
 */

import React, { useState, useEffect } from 'react';

interface MapViewProps {
    imageUrl?: string;
    type: 'STREET' | 'STATIC';
    location?: string;
    onClose: () => void;
}

const MapView: React.FC<MapViewProps> = ({ imageUrl, type, location, onClose }) => {
    const [isLoaded, setIsLoaded] = useState(false);

    useEffect(() => {
        if (imageUrl) {
            setIsLoaded(false);
            const img = new Image();
            img.src = imageUrl;
            img.onload = () => setIsLoaded(true);
        }
    }, [imageUrl]);

    return (
        <div className="map-view animate-fade-in">
            {/* Header Info */}
            <div className="map-header">
                <div className="map-type-badge">{type}_FEED</div>
                <div className="map-location">{location || 'TRACKING_COORDINATES...'}</div>
                <button className="map-close-btn" onClick={onClose}>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
            </div>

            <div className="map-content-container">
                {/* Decorative Grid */}
                <div className="map-grid-overlay"></div>

                {/* The Map Image */}
                {imageUrl ? (
                    <div className={`map-image-wrapper ${isLoaded ? 'loaded' : ''}`}>
                        <img src={imageUrl} alt="System Map" className="map-display-image" />

                        {/* Scanline Effect Overlay */}
                        <div className="map-scanline"></div>

                        {/* HUD Overlays */}
                        <div className="map-hud-top-left">
                            <div className="hud-line">LAT: 50.4501</div>
                            <div className="hud-line">LNG: 30.5234</div>
                            <div className="hud-line">ALT: 179m</div>
                        </div>

                        <div className="map-hud-bottom-right">
                            <div className="hud-status">ENCRYPTED_LINK_ACTIVE</div>
                            <div className="hud-timestamp">{new Date().toLocaleTimeString()}</div>
                        </div>

                        {/* Corner Brackets */}
                        <div className="map-corner tl"></div>
                        <div className="map-corner tr"></div>
                        <div className="map-corner bl"></div>
                        <div className="map-corner br"></div>
                    </div>
                ) : (
                    <div className="map-placeholder">
                        <div className="animate-pulse">WAITING_FOR_SATELLITE_UPLINK...</div>
                    </div>
                )}
            </div>

            <style>{`
        .map-view {
          width: 100%;
          height: 100%;
          display: flex;
          flex-direction: column;
          background: rgba(0, 0, 0, 0.4);
          padding: 20px;
          position: relative;
        }

        .map-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 12px;
          border-bottom: 1px solid rgba(0, 163, 255, 0.2);
          padding-bottom: 8px;
        }

        .map-type-badge {
          font-family: 'JetBrains Mono', monospace;
          font-size: 10px;
          color: var(--atlas-blue);
          background: rgba(0, 163, 255, 0.1);
          padding: 2px 8px;
          border: 1px solid var(--atlas-blue);
          letter-spacing: 2px;
        }

        .map-location {
          font-size: 11px;
          color: var(--user-turquoise);
          text-transform: uppercase;
          letter-spacing: 1px;
        }

        .map-close-btn {
          background: transparent;
          border: none;
          color: var(--atlas-blue);
          cursor: pointer;
          opacity: 0.6;
          transition: all 0.2s;
        }

        .map-close-btn:hover {
          opacity: 1;
          color: var(--grisha-orange);
        }

        .map-content-container {
          flex: 1;
          position: relative;
          border: 1px solid rgba(0, 163, 255, 0.1);
          background: #020202;
          overflow: hidden;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .map-grid-overlay {
          position: absolute;
          inset: 0;
          background-image: 
            linear-gradient(rgba(0, 163, 255, 0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0, 163, 255, 0.05) 1px, transparent 1px);
          background-size: 30px 30px;
          pointer-events: none;
          z-index: 1;
        }

        .map-image-wrapper {
          position: relative;
          width: 100%;
          height: 100%;
          opacity: 0;
          transform: scale(0.98);
          transition: all 0.6s cubic-bezier(0.16, 1, 0.3, 1);
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .map-image-wrapper.loaded {
          opacity: 1;
          transform: scale(1);
        }

        .map-display-image {
          max-width: 100%;
          max-height: 100%;
          object-fit: contain;
          /* Blue-scale filter if needed, but Swift already does it */
          filter: drop-shadow(0 0 10px rgba(0, 163, 255, 0.2));
        }

        .map-scanline {
          position: absolute;
          inset: 0;
          background: linear-gradient(
            to bottom,
            transparent 0%,
            rgba(0, 163, 255, 0.05) 50%,
            transparent 100%
          );
          background-size: 100% 4px;
          pointer-events: none;
          animation: scan 10s linear infinite;
        }

        .map-hud-top-left {
          position: absolute;
          top: 15px;
          left: 15px;
          font-family: 'JetBrains Mono', monospace;
          font-size: 8px;
          color: var(--atlas-blue);
          text-shadow: 0 0 5px rgba(0, 163, 255, 0.5);
          z-index: 5;
        }

        .map-hud-bottom-right {
          position: absolute;
          bottom: 15px;
          right: 15px;
          text-align: right;
          font-family: 'JetBrains Mono', monospace;
          font-size: 8px;
          color: var(--user-turquoise);
          text-shadow: 0 0 5px rgba(0, 229, 255, 0.5);
          z-index: 5;
        }

        .hud-line, .hud-status {
          margin-bottom: 2px;
        }

        .map-placeholder {
          font-family: 'JetBrains Mono', monospace;
          font-size: 10px;
          color: var(--atlas-blue);
          opacity: 0.4;
          letter-spacing: 4px;
        }

        .map-corner {
          position: absolute;
          width: 15px;
          height: 15px;
          border: 1px solid var(--atlas-blue);
          opacity: 0.6;
          z-index: 5;
        }

        .tl { top: 10px; left: 10px; border-right: none; border-bottom: none; }
        .tr { top: 10px; right: 10px; border-left: none; border-bottom: none; }
        .bl { bottom: 10px; left: 10px; border-right: none; border-top: none; }
        .br { bottom: 10px; right: 10px; border-left: none; border-top: none; }

        @keyframes scan {
          from { background-position: 0 0; }
          to { background-position: 0 100%; }
        }
      `}</style>
        </div>
    );
};

export default MapView;
