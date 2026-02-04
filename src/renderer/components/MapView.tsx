/**
 * MapView - Cyberpunk Map Visualization
 * Displays Street View and Static Maps with "hacker-style" aesthetic
 * Blue-turquoise theme matching AtlasTrinity design system
 */

/// <reference types="google.maps" />

import type React from 'react';
import { memo, useCallback, useEffect, useRef, useState } from 'react';

interface MapViewProps {
  imageUrl?: string;
  type: 'STREET' | 'STATIC' | 'INTERACTIVE';
  location?: string;
  onClose: () => void;
  agentView?: {
    heading: number;
    pitch: number;
    fov: number;
    timestamp: string;
  } | null;
}

interface GmpMapElement extends HTMLElement {
  innerMap?: google.maps.Map;
  shadowRoot: ShadowRoot | null;
}

interface GmpxPlacePickerElement extends HTMLElement {
  value?: {
    location?: google.maps.LatLng;
  };
}

// AtlasTrinity Cyberpunk Map Style - Blue/Turquoise Theme

const CYBERPUNK_MAP_STYLE = [
  { elementType: 'geometry', stylers: [{ color: '#020a10' }] },
  { elementType: 'labels.text.stroke', stylers: [{ color: '#020a10' }] },
  { elementType: 'labels.text.fill', stylers: [{ color: '#00e5ff' }] },
  {
    featureType: 'administrative',
    elementType: 'geometry.stroke',
    stylers: [{ color: '#00a3ff' }, { weight: 1.2 }],
  },
  {
    featureType: 'administrative.country',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#00e5ff' }],
  },
  {
    featureType: 'landscape',
    elementType: 'geometry',
    stylers: [{ color: '#051520' }],
  },
  {
    featureType: 'poi',
    elementType: 'geometry',
    stylers: [{ color: '#0a1a25' }],
  },
  {
    featureType: 'poi',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#00e5ff' }],
  },
  {
    featureType: 'poi.park',
    elementType: 'geometry',
    stylers: [{ color: '#062030' }],
  },
  {
    featureType: 'road',
    elementType: 'geometry',
    stylers: [{ color: '#002535' }],
  },
  {
    featureType: 'road',
    elementType: 'geometry.stroke',
    stylers: [{ color: '#00a3ff' }, { weight: 0.4 }],
  },
  {
    featureType: 'road',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#00e5ff' }],
  },
  {
    featureType: 'road.highway',
    elementType: 'geometry',
    stylers: [{ color: '#004060' }],
  },
  {
    featureType: 'road.highway',
    elementType: 'geometry.stroke',
    stylers: [{ color: '#00a3ff' }, { weight: 0.8 }],
  },
  {
    featureType: 'transit',
    elementType: 'geometry',
    stylers: [{ color: '#003050' }],
  },
  {
    featureType: 'water',
    elementType: 'geometry',
    stylers: [{ color: '#001520' }],
  },
  {
    featureType: 'water',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#00a3ff' }],
  },
];

// Google Maps API Key from environment (loaded from global config via Vite plugin)
const GOOGLE_MAPS_API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || '';

// Debug logging to verify key source
console.log(
  '🗺️ MapView: VITE_GOOGLE_MAPS_API_KEY loaded:',
  GOOGLE_MAPS_API_KEY ? '✓ Present' : '✗ Missing',
);
console.log('🗺️ MapView: Key length:', GOOGLE_MAPS_API_KEY.length);
if (GOOGLE_MAPS_API_KEY) {
  console.log('🗺️ MapView: Key starts with:', `${GOOGLE_MAPS_API_KEY.substring(0, 10)}...`);
}

const MapView: React.FC<MapViewProps> = memo(({ imageUrl, type, location, onClose, agentView }) => {
  const [isLoaded, setIsLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mapInitialized, setMapInitialized] = useState(false);
  const [mapType, setMapType] = useState<'roadmap' | 'satellite' | 'hybrid'>('roadmap');
  const [streetViewActive, setStreetViewActive] = useState(false);
  const [streetViewCooldown, setStreetViewCooldown] = useState(false);
  const [lightingMode, setLightingMode] = useState<'night' | 'day' | 'twilight'>('night');
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const streetViewRef = useRef<google.maps.StreetViewPanorama | null>(null);
  const streetViewDebounceRef = useRef<NodeJS.Timeout | null>(null);

  // Calculate time-based lighting mode for adaptive filters
  const getTimeBasedLightingMode = useCallback((): 'night' | 'day' | 'twilight' => {
    const hour = new Date().getHours();
    if (hour >= 6 && hour < 18) return 'day';
    if ((hour >= 5 && hour < 6) || (hour >= 18 && hour < 19)) return 'twilight';
    return 'night';
  }, []);

  // Update lighting mode on mount and every minute
  useEffect(() => {
    setLightingMode(getTimeBasedLightingMode());
    const interval = setInterval(() => {
      setLightingMode(getTimeBasedLightingMode());
    }, 60000); // Check every minute
    return () => clearInterval(interval);
  }, [getTimeBasedLightingMode]);

  // Load the Extended Component Library script
  useEffect(() => {
    console.log('🗺️ MapView mounted/updated', { type, isLoaded, mapInitialized });
    return () => console.log('🗺️ MapView unmounted');
  }, [type, isLoaded, mapInitialized]);

  useEffect(() => {
    if (type !== 'INTERACTIVE') return;

    // Check for API key first
    if (!GOOGLE_MAPS_API_KEY) {
      console.error('Critical: VITE_GOOGLE_MAPS_API_KEY is missing!');
      setError('MISSING_API_KEY');
      return;
    }

    // Script is now loaded globally in index.html for stability
    setIsLoaded(true);
  }, [type]);

  // Initialize the interactive map with cyberpunk styling
  useEffect(() => {
    if (type !== 'INTERACTIVE' || !isLoaded || mapInitialized) return;

    const initMap = async () => {
      try {
        // Wait for custom elements to be defined
        await customElements.whenDefined('gmp-map');
        await customElements.whenDefined('gmpx-api-loader');

        // Small delay to ensure everything is rendered
        await new Promise((resolve) => setTimeout(resolve, 500));

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const mapElement = document.querySelector('gmp-map') as GmpMapElement;

        if (mapElement) {
          // Wait for the inner map to be available
          const checkMap = setInterval(() => {
            if (mapElement.innerMap) {
              clearInterval(checkMap);
              mapElement.innerMap.setOptions({
                styles: CYBERPUNK_MAP_STYLE,
                disableDefaultUI: true,
                zoomControl: false,
                mapTypeControl: false,
                streetViewControl: true, // Enable Pegman drag-and-drop
                fullscreenControl: false,
              });

              // Listen for Street View visibility changes (Pegman drop)
              const streetView = mapElement.innerMap.getStreetView();
              google.maps.event.addListener(streetView, 'visible_changed', () => {
                const isVisible = streetView.getVisible();
                setStreetViewActive(isVisible);
                if (isVisible) {
                  streetViewRef.current = streetView;
                } else {
                  streetViewRef.current = null;
                }
              });

              // Inject styles into shadow DOM to darken the copyright bar
              if (mapElement.shadowRoot) {
                const style = document.createElement('style');
                style.textContent = `
                  .gm-style-cc { 
                    filter: invert(1) hue-rotate(180deg) brightness(1.2) contrast(1.2);
                    opacity: 0.8;
                    mix-blend-mode: screen;
                  }
                  .gm-style-cc span, .gm-style-cc a {
                    color: #00e5ff !important; 
                  }
                  /* Invert the background strip but keep text readable */
                  .gmnoprint a, .gmnoprint span {
                    color: #00e5ff !important;
                  }
                  /* Target the google logo if possible, generic filter */
                  a[href^="https://maps.google.com/maps"] img {
                    filter: invert(1) grayscale(1) brightness(2) drop-shadow(0 0 2px #00e5ff);
                  }
                `;
                mapElement.shadowRoot.appendChild(style);
              }
              setMapInitialized(true);
            }
          }, 100);

          // Timeout after 10 seconds
          setTimeout(() => clearInterval(checkMap), 10000);
        }
      } catch (err) {
        console.error('Failed to initialize map:', err);
        setError('Failed to initialize map');
      }
    };

    initMap();
  }, [type, isLoaded, mapInitialized]);

  // Handle image loading for static/street view
  useEffect(() => {
    if (imageUrl && type !== 'INTERACTIVE') {
      setIsLoaded(false);
      setError(null);
      const img = new Image();
      img.src = imageUrl;
      img.onload = () => setIsLoaded(true);
      img.onerror = () => setError('Failed to load map image');
    }
  }, [imageUrl, type]);

  // Handle place picker changes
  const handlePlaceChange = useCallback(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const placePicker = document.querySelector('gmpx-place-picker') as GmpxPlacePickerElement;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const mapElement = document.querySelector('gmp-map') as GmpMapElement;

    if (placePicker && mapElement?.innerMap) {
      const place = placePicker.value;
      if (place?.location) {
        mapElement.innerMap.panTo(place.location);
        mapElement.innerMap.setZoom(17);
      }
    }
  }, []);

  // Set up place picker event listener
  useEffect(() => {
    if (type !== 'INTERACTIVE' || !mapInitialized) return;

    const placePicker = document.querySelector('gmpx-place-picker');
    if (placePicker) {
      placePicker.addEventListener('gmpx-placechange', handlePlaceChange);
      return () => placePicker.removeEventListener('gmpx-placechange', handlePlaceChange);
    }
  }, [type, mapInitialized, handlePlaceChange]);

  const handleZoom = (delta: number) => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const mapElement = document.querySelector('gmp-map') as GmpMapElement;

    if (mapElement?.innerMap) {
      const currentZoom = mapElement.innerMap.getZoom();
      if (currentZoom !== undefined) {
        mapElement.innerMap.setZoom(currentZoom + delta);
      }
    }
  };

  const handleMapTypeChange = useCallback((newType: 'roadmap' | 'satellite' | 'hybrid') => {
    setMapType(newType);
    const mapElement = document.querySelector('gmp-map') as GmpMapElement;
    if (mapElement?.innerMap) {
      mapElement.innerMap.setMapTypeId(newType);
      // Re-apply custom styles for roadmap and hybrid types (hybrid styles labels)
      if (newType === 'roadmap' || newType === 'hybrid') {
        mapElement.innerMap.setOptions({ styles: CYBERPUNK_MAP_STYLE });
      } else {
        // For pure satellite, remove custom JSON styles (they don't apply)
        mapElement.innerMap.setOptions({ styles: [] });
      }
    }
  }, []);

  // Toggle Street View mode with rate limiting
  const handleStreetViewToggle = useCallback(() => {
    // Prevent rapid clicking that causes 429 errors
    if (streetViewCooldown) {
      console.warn('🛰️ Street View: Please wait before toggling again');
      return;
    }

    const mapElement = document.querySelector('gmp-map') as GmpMapElement;
    if (!mapElement?.innerMap) return;

    // Check if using placeholder API key
    const isPlaceholder = GOOGLE_MAPS_API_KEY.includes('AIzaSyBq4tcSGVtpl');
    if (isPlaceholder && !streetViewActive) {
      console.error(
        '⚠️  PLACEHOLDER API KEY DETECTED! Street View requires a real Google Cloud API key with billing enabled.',
      );
      console.info('Please run: python3 scripts/setup_google_maps.py');
      setError('PLACEHOLDER_API_KEY: Street View unavailable. Configure real API key.');
      return;
    }

    if (streetViewActive) {
      // Exit Street View
      const streetView = mapElement.innerMap.getStreetView();
      if (streetView) {
        streetView.setVisible(false);
        streetViewRef.current = null;
      }
      setStreetViewActive(false);
      setError(null); // Clear any previous errors
    } else {
      if (streetViewDebounceRef.current) {
        clearTimeout(streetViewDebounceRef.current);
      }

      streetViewDebounceRef.current = setTimeout(async () => {
        // Re-query mapElement inside timeout to ensure it's still valid
        const mapEl = document.querySelector('gmp-map') as GmpMapElement;
        if (!mapEl?.innerMap) return;

        // Enter Street View at current map center
        const center = mapEl.innerMap.getCenter();
        if (center) {
          // Check Street View coverage before activating to avoid wasted requests
          const streetViewService = new google.maps.StreetViewService();
          try {
            const response = await streetViewService.getPanorama({
              location: center,
              radius: 50, // Search within 50m radius
              preference: google.maps.StreetViewPreference.NEAREST,
              source: google.maps.StreetViewSource.OUTDOOR,
            });

            if (response.data?.location?.latLng) {
              const streetView = mapEl.innerMap.getStreetView();
              // Optimize Street View settings to reduce tile requests
              streetView.setOptions({
                position: response.data.location.latLng,
                pov: { heading: 0, pitch: 0 },
                zoom: 0, // Lowest zoom = fewer tiles
                motionTracking: false, // Disable device motion tracking
                motionTrackingControl: false,
                addressControl: false, // Reduce UI elements
                linksControl: true, // Keep navigation arrows
                enableCloseButton: true,
                clickToGo: true,
              });
              streetView.setVisible(true);
              streetViewRef.current = streetView;
              setStreetViewActive(true);
            }
          } catch {
            console.warn('🛰️ Street View: No coverage at this location');
            setError('No Street View coverage at this location');
            setTimeout(() => setError(null), 3000);
          }
        }
      }, 1500); // Debounce to reduce 429 errors
    }

    // Set cooldown for 5 seconds (increased from 4s)
    setStreetViewCooldown(true);
    setTimeout(() => setStreetViewCooldown(false), 5000);
  }, [streetViewActive, streetViewCooldown]);

  // API loader is now handled at App level to prevent redundant initializations and 429 errors
  const renderApiLoader = () => null;

  return (
    <div className="map-view animate-fade-in">
      {/* Header Info */}
      <div className="map-header">
        <div className="map-type-badge">{type}_FEED</div>
        <div className="map-location">
          {location ||
            (type === 'INTERACTIVE' ? 'INTERACTIVE_SEARCH_ACTIVE' : 'TRACKING_COORDINATES...')}
        </div>
        <button className="map-close-btn" onClick={onClose}>
          <svg
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
          >
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>

      <div className="map-content-container" ref={mapContainerRef}>
        {/* Error State */}
        {error && (
          <div className="map-error">
            <div className="error-icon">⚠</div>
            <div className="error-text">{error}</div>
            <div className="error-hint">API_CONNECTION_FAILED</div>
          </div>
        )}

        {/* The Map Image / Interactive Map */}
        {!error && type === 'INTERACTIVE' ? (
          <div className={`interactive-map-wrapper ${isLoaded ? 'loaded' : ''}`}>
            {/* API Loader with correct key attribute */}
            {renderApiLoader()}

            <gmp-map
              center="50.4501,30.5234"
              zoom="12"
              rendering-type="raster"
              data-map-type={mapType}
              data-lighting-mode={lightingMode}
              style={{ width: '100%', height: '100%' }}
            >
              <div slot="control-block-start-inline-start" className="place-picker-container">
                <gmpx-place-picker placeholder="SEARCH_TARGET_LOCATION..."></gmpx-place-picker>
              </div>
            </gmp-map>

            {/* Loading overlay */}
            {!mapInitialized && (
              <div className="map-loading-overlay">
                <div className="loading-spinner"></div>
                <div className="loading-text">INITIALIZING_SATELLITE_UPLINK...</div>
              </div>
            )}

            {/* Custom Zoom Controls */}
            <div className="map-zoom-controls">
              <button className="zoom-btn" onClick={() => handleZoom(1)} aria-label="Zoom In">
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <line x1="12" y1="5" x2="12" y2="19"></line>
                  <line x1="5" y1="12" x2="19" y2="12"></line>
                </svg>
              </button>
              <div className="zoom-separator"></div>
              <button className="zoom-btn" onClick={() => handleZoom(-1)} aria-label="Zoom Out">
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <line x1="5" y1="12" x2="19" y2="12"></line>
                </svg>
              </button>
            </div>

            {/* Map Type Controls */}
            <div className="map-type-controls">
              <button
                className={`map-type-btn ${mapType === 'roadmap' ? 'active' : ''}`}
                onClick={() => handleMapTypeChange('roadmap')}
                aria-label="Map View"
                title="TACTICAL_MAP"
              >
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                  <line x1="3" y1="9" x2="21" y2="9"></line>
                  <line x1="9" y1="21" x2="9" y2="9"></line>
                </svg>
              </button>
              <div className="map-type-separator"></div>
              <button
                className={`map-type-btn ${mapType === 'satellite' ? 'active' : ''}`}
                onClick={() => handleMapTypeChange('satellite')}
                aria-label="Satellite View"
                title="SATELLITE_FEED"
              >
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <circle cx="12" cy="12" r="10"></circle>
                  <circle cx="12" cy="12" r="4"></circle>
                  <line x1="21.17" y1="8" x2="12" y2="8"></line>
                  <line x1="3.95" y1="6.06" x2="8.54" y2="14"></line>
                  <line x1="10.88" y1="21.94" x2="15.46" y2="14"></line>
                </svg>
              </button>
              <div className="map-type-separator"></div>
              <button
                className={`map-type-btn ${mapType === 'hybrid' ? 'active' : ''}`}
                onClick={() => handleMapTypeChange('hybrid')}
                aria-label="Hybrid View"
                title="HYBRID_OVERLAY"
              >
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                  <circle cx="12" cy="12" r="4"></circle>
                </svg>
              </button>
            </div>

            {/* Street View Toggle */}
            <div className="street-view-controls">
              <button
                className={`street-view-btn ${streetViewActive ? 'active' : ''}`}
                onClick={handleStreetViewToggle}
                aria-label={streetViewActive ? 'Exit Street View' : 'Enter Street View'}
                title={streetViewActive ? 'EXIT_STREET_VIEW' : 'AGENT_POV_MODE'}
              >
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <circle cx="12" cy="7" r="4"></circle>
                  <path d="M5.5 21a8.38 8.38 0 0 1 0 -6"></path>
                  <path d="M18.5 21a8.38 8.38 0 0 0 0 -6"></path>
                  <path d="M12 11v10"></path>
                </svg>
                <span className="control-label">{streetViewActive ? 'EXIT' : 'POV'}</span>
              </button>
            </div>
          </div>
        ) : !error && imageUrl ? (
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

            {/* Agent POV Telemetry */}
            {agentView && (
              <div className="agent-pov-telemetry animate-pulse">
                <div className="telemetry-item">
                  <span className="telemetry-label">HEADING:</span>
                  <span className="telemetry-value">{agentView.heading.toFixed(1)}°</span>
                </div>
                <div className="telemetry-item">
                  <span className="telemetry-label">PITCH:</span>
                  <span className="telemetry-value">{agentView.pitch.toFixed(1)}°</span>
                </div>
                <div className="telemetry-item">
                  <span className="telemetry-label">FOV:</span>
                  <span className="telemetry-value">{agentView.fov}°</span>
                </div>
                <div className="telemetry-item">
                  <span className="telemetry-label">SOURCE:</span>
                  <span className="telemetry-value">AGENT_NEURAL_UPLINK</span>
                </div>
              </div>
            )}

            {/* Corner Brackets */}
            <div className="map-corner tl"></div>
            <div className="map-corner tr"></div>
            <div className="map-corner bl"></div>
            <div className="map-corner br"></div>
          </div>
        ) : !error ? (
          <div className="map-placeholder">
            <div className="animate-pulse">WAITING_FOR_SATELLITE_UPLINK...</div>
          </div>
        ) : null}
      </div>

      <style>{`
        .map-view {
          width: 100%;
          height: 100%;
          display: flex;
          flex-direction: column;
          background: transparent;
          padding: 0;
          position: relative;
        }

        .map-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 12px;
          border-bottom: 1px solid rgba(0, 163, 255, 0.3);
          padding-bottom: 8px;
        }

        .map-type-badge {
          font-family: 'JetBrains Mono', monospace;
          font-size: 10px;
          color: #00a3ff;
          background: rgba(0, 163, 255, 0.15);
          padding: 4px 12px;
          border: 1px solid #00a3ff;
          letter-spacing: 2px;
          text-shadow: 0 0 10px rgba(0, 163, 255, 0.5);
        }

        .map-location {
          font-size: 11px;
          color: #00e5ff;
          text-transform: uppercase;
          letter-spacing: 1px;
          text-shadow: 0 0 8px rgba(0, 229, 255, 0.5);
        }

        .map-close-btn {
          background: transparent;
          border: 1px solid rgba(0, 163, 255, 0.3);
          color: #00a3ff;
          cursor: pointer;
          opacity: 0.7;
          transition: all 0.3s;
          padding: 6px;
          border-radius: 2px;
        }

        .map-close-btn:hover {
          opacity: 1;
          border-color: #00e5ff;
          box-shadow: 0 0 15px rgba(0, 229, 255, 0.4);
        }

        .map-content-container {
          flex: 1;
          position: relative;
          overflow: hidden;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .map-error {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 12px;
          color: #ff4757;
          font-family: 'JetBrains Mono', monospace;
          text-align: center;
          z-index: 5;
        }

        .error-icon {
          font-size: 48px;
          animation: pulse 2s infinite;
        }

        .error-text {
          font-size: 12px;
          color: #ff6b7a;
        }

        .error-hint {
          font-size: 9px;
          color: rgba(255, 71, 87, 0.6);
          letter-spacing: 3px;
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
          filter: drop-shadow(0 0 20px rgba(0, 163, 255, 0.3));
          border: 1px solid rgba(0, 163, 255, 0.2);
        }

        .map-scanline {
          position: absolute;
          inset: 0;
          background: linear-gradient(
            to bottom,
            transparent 0%,
            rgba(0, 163, 255, 0.03) 50%,
            transparent 100%
          );
          background-size: 100% 4px;
          pointer-events: none;
          animation: scan 8s linear infinite;
        }

        .map-hud-top-left {
          position: absolute;
          top: 15px;
          left: 15px;
          font-family: 'JetBrains Mono', monospace;
          font-size: 9px;
          color: #00a3ff;
          text-shadow: 0 0 8px rgba(0, 163, 255, 0.6);
          z-index: 5;
          background: rgba(0, 10, 20, 0.7);
          padding: 8px 12px;
          border-left: 2px solid #00a3ff;
        }

        .map-hud-bottom-right {
          position: absolute;
          bottom: 15px;
          right: 15px;
          text-align: right;
          font-family: 'JetBrains Mono', monospace;
          font-size: 9px;
          color: #00e5ff;
          text-shadow: 0 0 8px rgba(0, 229, 255, 0.6);
          z-index: 5;
          background: rgba(0, 10, 20, 0.7);
          padding: 8px 12px;
          border-right: 2px solid #00e5ff;
        }

        .hud-line, .hud-status {
          margin-bottom: 3px;
        }

        .map-placeholder {
          font-family: 'JetBrains Mono', monospace;
          font-size: 11px;
          color: #00a3ff;
          opacity: 0.5;
          letter-spacing: 4px;
        }

        .map-corner {
          position: absolute;
          width: 20px;
          height: 20px;
          border: 1px solid #00a3ff;
          opacity: 0.5;
          z-index: 5;
        }

        .tl { top: 10px; left: 10px; border-right: none; border-bottom: none; }
        .tr { top: 10px; right: 10px; border-left: none; border-bottom: none; }
        .bl { bottom: 10px; left: 10px; border-right: none; border-top: none; }
        .br { bottom: 10px; right: 10px; border-left: none; border-top: none; }

        @keyframes scan {
          from { transform: translateY(-100%); }
          to { transform: translateY(100%); }
        }

        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }

        .interactive-map-wrapper {
          width: 100%;
          height: 100%;
          position: relative;
          z-index: 2;
          opacity: 0;
          transition: opacity 0.5s ease;
        }


        /* Cyberpunk overrides for Google Maps internals */
        
        /* SEARCH BOX (gmpx-place-picker) */
        gmpx-place-picker {
          --gmpx-color-surface: rgba(0, 10, 20, 0.9);
          --gmpx-color-on-surface: #00e5ff;
          --gmpx-color-on-surface-variant: #00a3ff;
          --gmpx-color-primary: #00e5ff;
          --gmpx-font-family-base: 'JetBrains Mono', monospace;
          box-shadow: 0 0 15px rgba(0, 163, 255, 0.2);
          border: 1px solid #00a3ff;
          border-radius: 4px;
        }

        gmpx-place-picker::part(input) {
          background: rgba(0, 10, 20, 0.9);
          color: #00e5ff;
          font-family: 'JetBrains Mono', monospace;
          border: none;
        }
        
        /* Fix internal input styles if part doesn't catch everything */
        gmpx-place-picker input {
          background-color: transparent !important;
          color: #00e5ff !important;
        }

        /* AUTOCOMPLETE DROPDOWN (.pac-container) */
        /* Note: This might attach to body, so we use global selector in App.tsx usually, 
           but if it's scoped here we try deep selecting or rely on global styles */
        
        /* INFO WINDOW (.gm-style-iw) */
        /* We need deep selectors or global styles for this as it renders in the map container */
        .gm-style .gm-style-iw-c {
          background-color: rgba(0, 10, 20, 0.95) !important;
          border: 1px solid #00a3ff !important;
          border-radius: 2px !important;
          box-shadow: 0 0 20px rgba(0, 163, 255, 0.3) !important;
          padding: 12px !important;
        }

        .gm-style .gm-style-iw-tc::after {
          background: rgba(0, 10, 20, 0.95) !important;
          border: 1px solid #00a3ff !important;
          border-top: none;
          border-left: none;
        }

        .gm-style .gm-style-iw-d {
          overflow: hidden !important;
          color: #00e5ff !important;
          font-family: 'JetBrains Mono', monospace !important;
        }

        /* Info Window Content */
        .gm-style .gm-title {
          color: #00e5ff !important;
          font-size: 14px !important;
          font-weight: bold !important;
          text-shadow: 0 0 5px rgba(0, 229, 255, 0.5);
        }

        .gm-style .gm-basicinfo {
          color: #00a3ff !important;
          line-height: 1.4 !important;
        }
        
        /* Close Button */
        .gm-style .gm-ui-hover-effect {
          background-color: rgba(0, 0, 0, 0.5) !important;
          border-radius: 50% !important;
          top: 4px !important;
          right: 4px !important;
        }
        
        .gm-style .gm-ui-hover-effect > span {
          background-color: #00e5ff !important;
        }

        /* HIDE DEFAULT CONTROLS/LOGOS FILTER */
        a[href^="http://maps.google.com/maps"] {
          display: none !important;
        }
        
        .gmnoprint a, .gmnoprint span, .gm-style-cc {
           display: none;
        }

        .interactive-map-wrapper.loaded {
          opacity: 1;
        }
        
        /* Zoom & Map Type Controls Styling */
        .map-zoom-controls, .map-type-controls, .street-view-controls {
          position: absolute;
          display: flex;
          flex-direction: column;
          background: rgba(0, 10, 20, 0.9);
          border: 1px solid rgba(0, 163, 255, 0.3);
          border-radius: 4px;
          padding: 2px;
          backdrop-filter: blur(4px);
          z-index: 10;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
        }

        .map-zoom-controls {
          bottom: 24px;
          right: 24px;
        }

        .map-type-controls {
          top: 24px;
          right: 24px;
        }

        .street-view-controls {
          top: 140px;
          right: 24px;
        }

        .zoom-btn, .map-type-btn, .street-view-btn {
          background: transparent;
          border: none;
          color: #00a3ff;
          padding: 8px;
          cursor: pointer;
          transition: all 0.2s;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 2px;
        }

        .zoom-btn:hover, .map-type-btn:hover, .street-view-btn:hover {
          color: #00e5ff;
          background: rgba(0, 163, 255, 0.1);
          text-shadow: 0 0 8px rgba(0, 229, 255, 0.6);
        }

        .zoom-btn:active, .map-type-btn:active, .street-view-btn:active {
          transform: scale(0.95);
        }

        .map-type-btn.active, .street-view-btn.active {
          color: #00e5ff;
          background: rgba(0, 163, 255, 0.2);
          box-shadow: 0 0 10px rgba(0, 229, 255, 0.3);
          border: 1px solid rgba(0, 163, 255, 0.5);
        }

        .zoom-separator, .map-type-separator {
          height: 1px;
          background: rgba(0, 163, 255, 0.2);
          margin: 2px 4px;
        }
        
        .street-view-btn {
           flex-direction: column;
           gap: 4px;
           padding: 10px 6px;
        }
        
        .control-label {
           font-size: 9px;
           font-family: 'JetBrains Mono', monospace;
           font-weight: bold;
        }

        /* Loading Overlay */
        .map-loading-overlay {
          position: absolute;
          inset: 0;
          gap: 16px;
          z-index: 10;
        }

        .loading-spinner {
          width: 40px;
          height: 40px;
          border: 2px solid rgba(0, 163, 255, 0.2);
          border-top-color: #00a3ff;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        .loading-text {
          font-family: 'JetBrains Mono', monospace;
          font-size: 10px;
          color: #00a3ff;
          letter-spacing: 3px;
          animation: pulse 2s infinite;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        /* Styling for the Google Maps Web Components */
        gmpx-place-picker {
          width: 100%;
          --gmpx-color-surface: rgba(0, 10, 20, 0.95) !important;
          --gmpx-color-on-surface: #00e5ff !important;
          --gmpx-color-on-surface-variant: #00a3ff !important;
          --gmpx-color-primary: #00a3ff !important;
          --gmpx-color-on-primary: #020a10 !important;
          --gmpx-font-family-base: 'JetBrains Mono', monospace !important;
          --gmpx-font-family-headings: 'JetBrains Mono', monospace !important;
          border: 1px solid rgba(0, 163, 255, 0.5) !important;
          box-shadow: 0 0 15px rgba(0, 163, 255, 0.3);
        }

        gmp-map {
          filter: contrast(1.02) brightness(0.98);
          /* Edge fade effect - 60px transparent gradient on all sides for performance */
          -webkit-mask-image: 
            linear-gradient(to right, transparent 0, black 60px, black calc(100% - 60px), transparent 100%),
            linear-gradient(to bottom, transparent 0, black 60px, black calc(100% - 60px), transparent 100%);
          -webkit-mask-composite: source-in;
          mask-image: 
            linear-gradient(to right, transparent 0, black 60px, black calc(100% - 60px), transparent 100%),
            linear-gradient(to bottom, transparent 0, black 60px, black calc(100% - 60px), transparent 100%);
          mask-composite: intersect;
          transition: filter 0.8s ease;
        }

        /* ===== TACTICAL LIGHTING SYSTEM ===== */
        /* Night Mode (18:00 - 06:00): Dark, high contrast, deep blue tint */
        gmp-map[data-lighting-mode="night"][data-map-type="satellite"],
        gmp-map[data-lighting-mode="night"][data-map-type="hybrid"] {
          filter: grayscale(1) brightness(0.7) contrast(1.4) sepia(1) hue-rotate(180deg) saturate(5) !important;
        }

        /* Day Mode (06:00 - 18:00): Lighter, less saturated, subtle cyan overlay */
        gmp-map[data-lighting-mode="day"][data-map-type="satellite"],
        gmp-map[data-lighting-mode="day"][data-map-type="hybrid"] {
          filter: brightness(0.95) contrast(1.15) sepia(0.4) hue-rotate(180deg) saturate(2.5) !important;
        }

        /* Twilight Mode (05:00-06:00, 18:00-19:00): Transition blend */
        gmp-map[data-lighting-mode="twilight"][data-map-type="satellite"],
        gmp-map[data-lighting-mode="twilight"][data-map-type="hybrid"] {
          filter: grayscale(0.6) brightness(0.82) contrast(1.25) sepia(0.8) hue-rotate(185deg) saturate(3.5) !important;
        }

        /* Street View Panorama styling */
        .gm-style-pano {
          filter: grayscale(0.3) brightness(0.9) contrast(1.1) sepia(0.3) hue-rotate(180deg) saturate(2) !important;
        }

        /* Pegman control styling - position above zoom controls with cyberpunk theme */
        .gm-svpc {
          position: absolute !important;
          right: 10px !important;
          bottom: 130px !important;
          z-index: 100 !important;
          filter: hue-rotate(180deg) brightness(1.2) saturate(2) drop-shadow(0 0 8px rgba(0, 229, 255, 0.8)) !important;
          background: rgba(0, 10, 20, 0.9) !important;
          border: 1px solid #ff9800 !important;
          border-radius: 3px !important;
          padding: 2px !important;
          box-shadow: 0 0 15px rgba(255, 152, 0, 0.4), inset 0 0 5px rgba(0, 229, 255, 0.1) !important;
          transition: all 0.3s ease !important;
        }

        .gm-svpc:hover {
          box-shadow: 0 0 25px rgba(255, 152, 0, 0.7), 0 0 10px rgba(0, 229, 255, 0.5) !important;
          border-color: #ffb74d !important;
        }

        /* Style the Pegman icon inside */
        .gm-svpc img,
        .gm-svpc button {
          filter: brightness(1.3) !important;
        }

        /* Street View control container positioning */
        .gmnoprint[controlwidth="40"][controlheight="40"] {
          position: absolute !important;
          right: 10px !important;
          bottom: 130px !important;
        }

        .map-zoom-controls {
          position: absolute;
          bottom: 40px;
          right: 20px;
          display: flex;
          flex-direction: column;
          background: rgba(0, 10, 20, 0.9);
          border: 1px solid #00a3ff;
          border-radius: 2px;
          box-shadow: 0 0 15px rgba(0, 163, 255, 0.2);
          z-index: 10;
        }

        .zoom-btn {
          width: 32px;
          height: 32px;
          background: transparent;
          border: none;
          color: #00e5ff;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s;
        }

        .zoom-btn:hover {
          background: rgba(0, 163, 255, 0.2);
          color: #fff;
          text-shadow: 0 0 8px #00e5ff;
        }

        .zoom-btn:active {
          transform: scale(0.95);
        }

        .zoom-separator {
          height: 1px;
          background: rgba(0, 163, 255, 0.3);
          width: 100%;
        }

        .agent-pov-telemetry {
          position: absolute;
          top: 15px;
          right: 15px;
          display: flex;
          flex-direction: column;
          gap: 6px;
          background: rgba(0, 10, 20, 0.7);
          padding: 10px 14px;
          border-right: 2px solid #ff00ff;
          font-family: 'JetBrains Mono', monospace;
          z-index: 10;
          pointer-events: none;
        }

        .telemetry-item {
          display: flex;
          justify-content: space-between;
          gap: 12px;
          font-size: 9px;
          letter-spacing: 1px;
        }

        .telemetry-label {
          color: rgba(255, 255, 255, 0.5);
        }

        .telemetry-value {
          color: #ff00ff;
          text-shadow: 0 0 8px rgba(255, 0, 255, 0.6);
        }

        /* Map Type Controls */
        .map-type-controls {
          position: absolute;
          top: 60px;
          right: 20px;
          display: flex;
          flex-direction: column;
          background: rgba(0, 10, 20, 0.9);
          border: 1px solid rgba(0, 163, 255, 0.5);
          border-radius: 2px;
          box-shadow: 0 0 15px rgba(0, 163, 255, 0.2);
          z-index: 10;
        }

        .map-type-btn {
          width: 32px;
          height: 32px;
          background: transparent;
          border: none;
          color: rgba(0, 229, 255, 0.6);
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s;
        }

        .map-type-btn:hover {
          background: rgba(0, 163, 255, 0.2);
          color: #fff;
        }

        .map-type-btn.active {
          background: rgba(0, 163, 255, 0.25);
          color: #00e5ff;
          box-shadow: inset 0 0 10px rgba(0, 229, 255, 0.3);
        }

        .map-type-separator {
          height: 1px;
          background: rgba(0, 163, 255, 0.3);
          width: 100%;
        }

        /* Street View Controls */
        .street-view-controls {
          position: absolute;
          top: 180px;
          right: 20px;
          z-index: 10;
        }

        .street-view-btn {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 4px;
          padding: 8px;
          background: rgba(0, 10, 20, 0.9);
          border: 1px solid rgba(0, 163, 255, 0.5);
          border-radius: 2px;
          color: rgba(0, 229, 255, 0.6);
          cursor: pointer;
          transition: all 0.2s;
          box-shadow: 0 0 15px rgba(0, 163, 255, 0.2);
        }

        .street-view-btn:hover {
          background: rgba(0, 163, 255, 0.2);
          color: #fff;
          border-color: #00a3ff;
        }

        .street-view-btn.active {
          background: rgba(255, 140, 0, 0.15);
          border-color: #ff8c00;
          color: #ff8c00;
          box-shadow: 0 0 20px rgba(255, 140, 0, 0.3);
        }

        .control-label {
          font-family: 'JetBrains Mono', monospace;
          font-size: 8px;
          letter-spacing: 1px;
        }
      `}</style>

      {/* Global styles for Google Places Autocomplete dropdown - injected into document */}
      <style>{`
        /* Google Places Autocomplete Dropdown - Dark Theme */
        .pac-container {
          background-color: rgba(2, 10, 16, 0.98) !important;
          border: 1px solid rgba(0, 163, 255, 0.5) !important;
          border-top: none !important;
          border-radius: 0 0 4px 4px !important;
          box-shadow: 0 4px 20px rgba(0, 163, 255, 0.3) !important;
          font-family: 'JetBrains Mono', 'Outfit', sans-serif !important;
          z-index: 10000 !important;
          margin-top: -1px !important;
        }

        .pac-item {
          background-color: transparent !important;
          border-bottom: 1px solid rgba(0, 163, 255, 0.15) !important;
          padding: 10px 12px !important;
          color: #00e5ff !important;
          cursor: pointer !important;
          line-height: 1.4 !important;
        }

        .pac-item:hover,
        .pac-item-selected {
          background-color: rgba(0, 163, 255, 0.15) !important;
        }

        .pac-item:last-child {
          border-bottom: none !important;
        }

        .pac-item-query {
          color: #00a3ff !important;
          font-size: 12px !important;
          font-weight: 500 !important;
        }

        .pac-icon {
          filter: invert(1) sepia(1) saturate(5) hue-rotate(175deg) brightness(1.2) !important;
          margin-right: 10px !important;
        }

        .pac-icon-marker {
          background-position: -1px -161px !important;
        }

        .pac-matched {
          color: #00e5ff !important;
          font-weight: 600 !important;
        }

        /* Secondary text (address details) */
        .pac-item span:not(.pac-item-query):not(.pac-matched) {
          color: rgba(0, 163, 255, 0.7) !important;
          font-size: 11px !important;
        }

        /* "Powered by Google" footer styling */
        .pac-container::after {
          background-color: rgba(2, 10, 16, 0.95) !important;
          background-image: none !important;
          border-top: 1px solid rgba(0, 163, 255, 0.2) !important;
          padding: 8px 12px !important;
          color: rgba(0, 163, 255, 0.4) !important;
          font-size: 9px !important;
        }

        .pac-logo::after {
          filter: invert(1) grayscale(1) brightness(1.5) hue-rotate(180deg) !important;
        }

        /* Hide "powered by Google" text, keep only logo filtered */
        .hdpi.pac-logo::after {
          background-image: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=) !important;
        }
      `}</style>
    </div>
  );
});

// Add global declarations for Google Maps Web Components to satisfy TypeScript
declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace JSX {
    interface IntrinsicElements {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      'gmp-map': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
        center?: string;
        zoom?: string;
        'rendering-type'?: string;
      };
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      'gmpx-api-loader': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
        key?: string;
        'solution-channel'?: string;
        version?: string;
      };
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      'gmpx-place-picker': React.DetailedHTMLProps<
        React.HTMLAttributes<HTMLElement>,
        HTMLElement
      > & {
        placeholder?: string;
      };
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      'gmp-advanced-marker': React.DetailedHTMLProps<
        React.HTMLAttributes<HTMLElement>,
        HTMLElement
      >;
    }
  }
}

export default MapView;
