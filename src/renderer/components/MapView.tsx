/**
 * MapView - Cyberpunk Map Visualization
 * Displays Street View and Static Maps with "hacker-style" aesthetic
 */

import React, { useState, useEffect } from 'react';

interface MapViewProps {
  imageUrl?: string;
  type: 'STREET' | 'STATIC' | 'INTERACTIVE';
  location?: string;
  onClose: () => void;
}

const CYBERPUNK_MAP_STYLE = [
  { elementType: "geometry", stylers: [{ color: "#020202" }] },
  { elementType: "labels.text.stroke", stylers: [{ color: "#020202" }] },
  { elementType: "labels.text.fill", stylers: [{ color: "#00e5ff" }] },
  {
    featureType: "administrative",
    elementType: "geometry.stroke",
    stylers: [{ color: "#00a3ff" }, { weight: 1.2 }],
  },
  {
    featureType: "landscape",
    elementType: "geometry",
    stylers: [{ color: "#050505" }],
  },
  {
    featureType: "poi",
    elementType: "geometry",
    stylers: [{ color: "#0a0a0a" }],
  },
  {
    featureType: "poi",
    elementType: "labels.text.fill",
    stylers: [{ color: "#00e5ff" }],
  },
  {
    featureType: "road",
    elementType: "geometry",
    stylers: [{ color: "#002030" }],
  },
  {
    featureType: "road",
    elementType: "geometry.stroke",
    stylers: [{ color: "#00a3ff" }, { weight: 0.5 }],
  },
  {
    featureType: "road",
    elementType: "labels.text.fill",
    stylers: [{ color: "#00e5ff" }],
  },
  {
    featureType: "water",
    elementType: "geometry",
    stylers: [{ color: "#001015" }],
  },
];

const MapView: React.FC<MapViewProps> = ({ imageUrl, type, location, onClose }) => {
  const [isLoaded, setIsLoaded] = useState(false);
  const mapRef = React.useRef<any>(null);

  useEffect(() => {
    if (imageUrl && type !== 'INTERACTIVE') {
      setIsLoaded(false);
      const img = new Image();
      img.src = imageUrl;
      img.onload = () => setIsLoaded(true);
    } else if (type === 'INTERACTIVE') {
      // Load interactive map logic
      const initInteractive = async () => {
        // @ts-ignore
        if (window.google) {
          setIsLoaded(true);
        }
      };
      initInteractive();
    }
  }, [imageUrl, type]);

  // Handle place changes in interactive mode
  useEffect(() => {
    const placePicker = document.querySelector('gmpx-place-picker');
    const mapElement = document.querySelector('gmp-map') as any;

    if (placePicker && mapElement) {
      const handlePlaceChange = () => {
        // @ts-ignore
        const place = placePicker.value;
        if (place?.location) {
          mapElement.center = place.location;
          mapElement.zoom = 17;
        }
      };

      placePicker.addEventListener('gmpx-placechange', handlePlaceChange);
      return () => placePicker.removeEventListener('gmpx-placechange', handlePlaceChange);
    }
  }, [isLoaded, type]);

  const googleMapsKey = "AIzaSyDFLLXp5tsbni0sXxH1IcryTh3OqBhaHF8"; // User provided key

  return (
    <div className="map-view animate-fade-in">
      {/* Extended Components Library Script */}
      <script type="module" src="https://ajax.googleapis.com/ajax/libs/@googlemaps/extended-component-library/0.6.11/index.min.js"></script>

      {/* Header Info */}
      <div className="map-header">
        <div className="map-type-badge">{type}_FEED</div>
        <div className="map-location">{location || (type === 'INTERACTIVE' ? 'INTERACTIVE_SEARCH_ACTIVE' : 'TRACKING_COORDINATES...')}</div>
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

        {/* The Map Image / Interactive Map */}
        {type === 'INTERACTIVE' ? (
          <div className="interactive-map-wrapper loaded">
            <gmpx-api-loader key={googleMapsKey}></gmpx-api-loader>
            <gmp-map
              center="50.4501,30.5234"
              zoom="12"
              map-id="ATLAS_MAP_ID"
              style={{ width: '100%', height: '100%' }}
              ref={mapRef}
            >
              <div slot="control-block-start-inline-start" className="place-picker-container">
                <gmpx-place-picker placeholder="SEARCH_ADDRESS_IN_DATABASE..."></gmpx-place-picker>
              </div>
              <gmp-advanced-marker></gmp-advanced-marker>
            </gmp-map>

            {/* Apply Cyberpunk Style via Script since these are web components */}
            <script dangerouslySetInnerHTML={{
              __html: `
              customElements.whenDefined('gmp-map').then(() => {
                const map = document.querySelector('gmp-map');
                if (map) {
                  map.innerMap.setOptions({
                    styles: ${JSON.stringify(CYBERPUNK_MAP_STYLE)},
                    disableDefaultUI: true,
                    zoomControl: true,
                  });
                }
              });
            `}} />
          </div>
        ) : imageUrl ? (
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

        .interactive-map-wrapper {
          width: 100%;
          height: 100%;
          position: relative;
          z-index: 2;
        }

        .place-picker-container {
          padding: 10px;
          width: 300px;
        }

        /* Styling for the Google Maps Web Components */
        gmpx-place-picker {
          width: 100%;
          border: 1px solid var(--atlas-blue) !important;
          background: rgba(0, 0, 0, 0.8) !important;
          color: var(--user-turquoise) !important;
          font-family: 'JetBrains Mono', monospace !important;
          box-shadow: 0 0 10px rgba(0, 163, 255, 0.3);
        }

        gmp-map {
          filter: contrast(1.1) brightness(0.9) saturate(1.2);
        }
      `}</style>
    </div>
  );
};

// Add global declarations for Google Maps Web Components to satisfy TypeScript
declare global {
  namespace JSX {
    interface IntrinsicElements {
      'gmp-map': any;
      'gmpx-api-loader': any;
      'gmpx-place-picker': any;
      'gmp-advanced-marker': any;
    }
  }
}

export default MapView;
