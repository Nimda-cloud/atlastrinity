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
  // No explicit street view toggling needed with native control
  // We just allow the user to drag the Pegman
  const [lightingMode, setLightingMode] = useState<'night' | 'day' | 'twilight'>('night');
  // Track street view active state for the custom toggle button
  const [streetViewActive, setStreetViewActive] = useState(false);
  // Track Pegman dragging state for road highlighting
  const [isDraggingPegman, setIsDraggingPegman] = useState(false);
  // Cyberpunk filter toggle - enabled by default for satellite/hybrid, roadmap always uses night style
  const [cyberpunkFilterEnabled, setCyberpunkFilterEnabled] = useState(true);
  const mapContainerRef = useRef<HTMLDivElement>(null);

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

              // Listen for Street View visibility changes to sync state
              const streetView = mapElement.innerMap.getStreetView();
              google.maps.event.addListener(streetView, 'visible_changed', () => {
                setStreetViewActive(streetView.getVisible());
              });

              // Inject styles into shadow DOM to darken the copyright bar and position Pegman

              // Inject styles into shadow DOM to darken the copyright bar and position Pegman
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
                  /* Target the google logo if possible, generic filter */
                  a[href^="https://maps.google.com/maps"] img {
                    filter: invert(1) grayscale(1) brightness(2) drop-shadow(0 0 2px #00e5ff);
                  }
                  
                  /* Native Pegman Control Styling - Injected into Shadow DOM */
                  /* Position at center-top to align with centered control bar */
                  .gm-svpc {
                     position: absolute !important;
                     top: 4px !important; 
                     left: 50% !important;
                     transform: translateX(66px) !important; /* Offset to align with last button */
                     right: auto !important;
   
                     /* Visible and draggable */
                     opacity: 1 !important;
                     background: transparent !important;
                     
                     border: none !important;
                     box-shadow: none !important;
                     width: 42px !important;
                     height: 36px !important; 
                     z-index: 200 !important;
                     cursor: grab !important;
                     transition: transform 0.2s, opacity 0.2s;
                  }
                  
                  .gm-svpc:hover {
                     transform: translateX(66px) scale(1.1) !important;
                  }
                  
                  .gm-svpc:active {
                     cursor: grabbing !important;
                  }
                  
                  /* We don't style inner img because we are hiding the container */
                  .gm-svpc img {
                     visibility: hidden !important;
                  }
                  
                  /* Hide the floor/arrows in street view if needed, but here we just style the pegman button */
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

  // Manual toggle for Street View (button click)
  const handleStreetViewToggle = useCallback(() => {
    const mapElement = document.querySelector('gmp-map') as GmpMapElement;
    if (!mapElement?.innerMap) return;

    if (streetViewActive) {
      const streetView = mapElement.innerMap.getStreetView();
      if (streetView) {
        streetView.setVisible(false);
        setStreetViewActive(false);
      }
    } else {
      // Check for coverage before activating to avoid white screen
      const streetViewService = new google.maps.StreetViewService();
      const center = mapElement.innerMap.getCenter();

      if (center) {
        streetViewService.getPanorama(
          {
            location: center,
            radius: 100, // Check 100m radius
            preference: google.maps.StreetViewPreference.NEAREST,
          },
          (data, status) => {
            if (status === google.maps.StreetViewStatus.OK && data?.location?.latLng) {
              // Re-check innerMap existence just in case, though unlikely to change in callback
              if (mapElement.innerMap) {
                const streetView = mapElement.innerMap.getStreetView();
                streetView.setPosition(data.location.latLng);
                streetView.setVisible(true);
                setStreetViewActive(true);
              }
            } else {
              console.warn('Street View not available at this location');
              // Optional: Show a toast?
            }
          },
        );
      }
    }
  }, [streetViewActive]);

  // Pegman drag handlers for Street View activation with road highlighting
  const handlePegmanDragStart = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault();
    setIsDraggingPegman(true);

    // Get initial position
    const startX = 'touches' in e ? e.touches[0].clientX : e.clientX;
    const startY = 'touches' in e ? e.touches[0].clientY : e.clientY;

    // Create draggable Pegman clone that follows cursor
    const dragClone = document.createElement('div');
    dragClone.id = 'pegman-drag-clone';
    dragClone.innerHTML = `
      <svg width="32" height="32" viewBox="0 0 24 24" fill="#ff9800" stroke="none">
        <circle cx="12" cy="4" r="3" />
        <path d="M12 8c-2.5 0-4.5 1.5-4.5 3.5V15h2v6h5v-6h2v-3.5C16.5 9.5 14.5 8 12 8z" />
      </svg>
    `;
    dragClone.style.cssText = `
      position: fixed;
      left: ${startX - 16}px;
      top: ${startY - 16}px;
      z-index: 10000;
      pointer-events: none;
      filter: drop-shadow(0 0 10px #ff9800) drop-shadow(0 0 20px rgba(255,152,0,0.6));
      animation: pegman-float 0.3s ease infinite alternate;
      transition: transform 0.1s ease;
    `;
    document.body.appendChild(dragClone);

    // Add class to map for visual road highlighting effect
    const mapElement = document.querySelector('gmp-map');
    if (mapElement) {
      mapElement.classList.add('pegman-drag-active');
    }

    // Track mouse/touch position and update clone position
    const handleMove = (moveEvent: MouseEvent | TouchEvent) => {
      moveEvent.preventDefault();
      const clientX = 'touches' in moveEvent ? moveEvent.touches[0].clientX : moveEvent.clientX;
      const clientY = 'touches' in moveEvent ? moveEvent.touches[0].clientY : moveEvent.clientY;

      // Update clone position
      dragClone.style.left = `${clientX - 16}px`;
      dragClone.style.top = `${clientY - 16}px`;
    };

    const handleEnd = (endEvent: MouseEvent | TouchEvent) => {
      setIsDraggingPegman(false);

      // Remove clone
      const clone = document.getElementById('pegman-drag-clone');
      if (clone) {
        clone.remove();
      }

      // Remove highlighting class
      const map = document.querySelector('gmp-map');
      if (map) {
        map.classList.remove('pegman-drag-active');
      }

      // Get drop position
      const clientX =
        'touches' in endEvent ? endEvent.changedTouches[0]?.clientX : endEvent.clientX;
      const clientY =
        'touches' in endEvent ? endEvent.changedTouches[0]?.clientY : endEvent.clientY;

      if (clientX === undefined || clientY === undefined) return;

      // Check if dropped on the map
      const mapEl = document.querySelector('gmp-map') as GmpMapElement;
      if (mapEl?.innerMap) {
        const mapBounds = mapEl.getBoundingClientRect();

        if (
          clientX >= mapBounds.left &&
          clientX <= mapBounds.right &&
          clientY >= mapBounds.top &&
          clientY <= mapBounds.bottom
        ) {
          // Convert screen coordinates to map coordinates
          const projection = mapEl.innerMap.getProjection();
          const bounds = mapEl.innerMap.getBounds();

          if (projection && bounds) {
            const ne = bounds.getNorthEast();
            const sw = bounds.getSouthWest();

            const xPercent = (clientX - mapBounds.left) / mapBounds.width;
            const yPercent = (clientY - mapBounds.top) / mapBounds.height;

            const lng = sw.lng() + xPercent * (ne.lng() - sw.lng());
            const lat = ne.lat() - yPercent * (ne.lat() - sw.lat());

            // Check for Street View coverage and activate
            const streetViewService = new google.maps.StreetViewService();
            const dropLocation = new google.maps.LatLng(lat, lng);

            streetViewService.getPanorama(
              {
                location: dropLocation,
                radius: 50,
                preference: google.maps.StreetViewPreference.NEAREST,
              },
              (data, status) => {
                if (status === google.maps.StreetViewStatus.OK && data?.location?.latLng) {
                  const streetView = mapEl.innerMap?.getStreetView();
                  if (streetView) {
                    streetView.setPosition(data.location.latLng);
                    streetView.setVisible(true);
                    setStreetViewActive(true);
                  }
                } else {
                  console.warn('No Street View coverage at drop location');
                }
              },
            );
          }
        }
      }

      // Cleanup listeners
      document.removeEventListener('mousemove', handleMove);
      document.removeEventListener('mouseup', handleEnd);
      document.removeEventListener('touchmove', handleMove);
      document.removeEventListener('touchend', handleEnd);
    };

    document.addEventListener('mousemove', handleMove);
    document.addEventListener('mouseup', handleEnd);
    document.addEventListener('touchmove', handleMove, { passive: false });
    document.addEventListener('touchend', handleEnd);
  }, []);

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
            {/* Masked Map Layer */}
            <div className="masked-map-layer">
              {/* API Loader */}
              {renderApiLoader()}

              <gmp-map
                center="50.4501,30.5234"
                zoom="12"
                rendering-type="raster"
                data-map-type={mapType}
                data-lighting-mode={lightingMode}
                data-cyberpunk-filter={
                  cyberpunkFilterEnabled && mapType !== 'roadmap' ? 'enabled' : 'disabled'
                }
                street-view-control
                style={{ width: '100%', height: '100%' }}
              >
                <div slot="control-block-start-inline-start" className="place-picker-container">
                  <gmpx-place-picker placeholder="SEARCH_TARGET_LOCATION..."></gmpx-place-picker>
                </div>
              </gmp-map>
            </div>

            {/* Unmasked Controls Layer */}
            <div className="map-controls-layer">
              {/* Loading overlay - keep it here so it's visible */}
              {!mapInitialized && (
                <div className="map-loading-overlay">
                  <div className="loading-spinner"></div>
                  <div className="loading-text">INITIALIZING_SATELLITE_UPLINK...</div>
                </div>
              )}

              {/* Unified Control Group - Horizontal Row at Top */}
              <div className="map-controls-group">
                {/* Map Type Controls */}
                <div className="control-section">
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
                  <div className="control-separator-vertical"></div>
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
                  <div className="control-separator-vertical"></div>
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

                {/* Zoom Controls */}
                <div className="control-section zoom-section">
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
                  <div className="control-separator-vertical"></div>
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

                {/* Street View Toggle Button - Restored per request */}
                <div className="control-section">
                  <div className="control-separator-vertical"></div>
                  <button
                    className={`street-view-btn ${streetViewActive ? 'active' : ''}`}
                    onClick={handleStreetViewToggle}
                    aria-label="Toggle Street View"
                    title="STREET_VIEW_POV"
                  >
                    {/* Using the icon from the screenshot reference roughly (Pegman-like or Eye) */}
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                      <circle cx="12" cy="12" r="3"></circle>
                    </svg>
                  </button>
                </div>

                {/* Draggable Pegman Icon for Street View */}
                <div className="control-section pegman-section">
                  <div className="control-separator-vertical"></div>
                  <div
                    className={`pegman-draggable ${isDraggingPegman ? 'dragging' : ''}`}
                    title="Drag to road for Street View"
                    aria-label="Drag Pegman to Street View"
                    onMouseDown={handlePegmanDragStart}
                    onTouchStart={handlePegmanDragStart}
                  >
                    <svg
                      width="18"
                      height="18"
                      viewBox="0 0 24 24"
                      fill="currentColor"
                      stroke="none"
                    >
                      {/* Pegman-style person icon */}
                      <circle cx="12" cy="4" r="3" />
                      <path d="M12 8c-2.5 0-4.5 1.5-4.5 3.5V15h2v6h5v-6h2v-3.5C16.5 9.5 14.5 8 12 8z" />
                    </svg>
                  </div>
                </div>

                {/* Cyberpunk Filter Toggle - only for satellite/hybrid */}
                <div className="control-section filter-section">
                  <div className="control-separator-vertical"></div>
                  <button
                    className={`filter-toggle-btn ${cyberpunkFilterEnabled ? 'active' : ''} ${mapType === 'roadmap' ? 'disabled' : ''}`}
                    onClick={() => setCyberpunkFilterEnabled(!cyberpunkFilterEnabled)}
                    aria-label="Toggle Cyberpunk Filter"
                    title={
                      mapType === 'roadmap'
                        ? 'FILTER_N/A_ROADMAP'
                        : cyberpunkFilterEnabled
                          ? 'FILTER_ENABLED'
                          : 'FILTER_DISABLED'
                    }
                    disabled={mapType === 'roadmap'}
                  >
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      {/* Filter/Adjustment icon */}
                      <circle cx="12" cy="12" r="10"></circle>
                      <path d="M12 2v20M2 12h20"></path>
                      <circle cx="12" cy="12" r="4"></circle>
                    </svg>
                  </button>
                </div>
              </div>
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
          overflow: visible;
          display: flex;
          align-items: center;
          justify-content: center;
          margin-left: -194px; /* Half of side panel width */
          margin-right: -194px;
          z-index: 50;
        }

        .masked-map-layer {
          position: absolute;
          inset: 0;
          z-index: 0;
          /* CSS Masking for true edge transparency - SMOOTHER GRADIENT */
          /* Using radial gradient for softer vignette to avoid banding lines */
          -webkit-mask-image: radial-gradient(ellipse at center, black 60%, transparent 98%);
          mask-image: radial-gradient(ellipse at center, black 60%, transparent 98%);
          mask-composite: intersect;
          pointer-events: auto; /* Allow map interactions */
        }
        
        .map-controls-layer {
          position: absolute;
          inset: 0;
          z-index: 100;
          pointer-events: none; /* Let clicks pass through, children will re-enable */
        }
        
        /* Enable pointer events for controls inside the layer */
        .map-zoom-controls, 
        .map-type-controls, 
        .street-view-controls {
           pointer-events: auto;
        }

        /* Removed vignette overlay in favor of masking */

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
        
        /* Interactive Map Container */
        gmp-map {
          width: 100%;
          height: 100%;
          position: absolute;
          top: 0;
          left: 0;
          /* Default Map Filter (Roadmap/Satellite) managed by 'filter' prop in style, 
             but we can enforce base transitions here */
          transition: filter 0.5s ease;
        }
        
        /* Specialized Filter for Street View Mode (Cyberpunk effect) */
        .street-view-mode gmp-map {
           filter: sepia(0.8) hue-rotate(170deg) saturate(1.5) contrast(1.1) brightness(1.2) !important;
        }

        /* 
         * Custom Map Controls Layer 
         * Sits ON TOP of the mask to ensure buttons are clickable.
         */ 

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
        
        /* HIDE DEFAULT CONTROLS/LOGOS FILTER, but allow Pegman */
        .gmnoprint a, .gm-style-cc {
           display: none;
        }
        
        /* Ensure Pegman container is visible even if inside gmnoprint */
        .gmnoprint {
           display: block !important;
        }
        /* Specific elements inside gmnoprint to hide if needed, e.g. text labels */
        .gmnoprint > span {
           display: none;
        }

        .interactive-map-wrapper.loaded {
          opacity: 1;
        }
        
        /* Zoom & Map Type Controls Styling */
        /* Unified Control Group - Horizontal Row at Top */
        .map-controls-group {
          position: absolute;
          top: 0px; /* User requested 0px */
          right: 190px; /* User requested 190px */
          display: flex;
          flex-direction: row;
          gap: 0;
          background: rgba(0, 10, 20, 0.2); /* More transparent per request (was 0.9 then 0.4) */
          border: 1px solid rgba(0, 163, 255, 0.3);
          border-top: none; /* Look like it hangs from top */
          border-radius: 0 0 4px 4px;
          padding: 2px 4px;
          backdrop-filter: blur(4px);
          z-index: 10;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
          align-items: center;
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
          /* CSS Masking for true edge transparency */
          /* Horizontal: 60px full transparent -> 300px fade */
          /* Vertical: 20px full transparent -> 100px fade */
          /* CSS Masking for true edge transparency */
          /* Horizontal: 100px full transparent -> 400px fade (Wide transition) */
          /* Vertical: 20px full transparent -> 100px fade */
          -webkit-mask-image: 
            linear-gradient(to right, transparent 0px, transparent 100px, black 500px, black calc(100% - 500px), transparent calc(100% - 100px), transparent 100%),
            linear-gradient(to bottom, transparent 0px, transparent 20px, black 120px, black calc(100% - 120px), transparent calc(100% - 20px), transparent 100%);
          -webkit-mask-composite: source-in;
          mask-image: 
            linear-gradient(to right, transparent 0px, transparent 100px, black 500px, black calc(100% - 500px), transparent calc(100% - 100px), transparent 100%),
            linear-gradient(to bottom, transparent 0px, transparent 20px, black 120px, black calc(100% - 120px), transparent calc(100% - 20px), transparent 100%);
          mask-composite: intersect;
          transition: filter 0.8s ease;
        }


        /* ===== TACTICAL LIGHTING SYSTEM ===== */
        /* Night Mode (18:00 - 06:00): Dark, high contrast, deep blue tint */
        /* Applied to ALL map types including roadmap for unified look */
        /* ===== TACTICAL LIGHTING SYSTEM ===== */
        /* Night Mode (18:00 - 06:00): Dark, high contrast, deep blue tint */
        /* Applied to ALL map types including roadmap per user request */
        /* ===== TACTICAL LIGHTING SYSTEM ===== */
        /* Night Mode (18:00 - 06:00): Dark, high contrast, deep blue tint */
        /* ONLY applied to Satellite/Hybrid. Roadmap uses custom JSON for night mode look. */
        gmp-map[data-lighting-mode="night"]:not([data-map-type="roadmap"]) {
          filter: grayscale(1) brightness(0.7) contrast(1.4) sepia(1) hue-rotate(180deg) saturate(5) !important;
        }

        /* Roadmap Night Mode: Just slight brightness/contrast tweak, relies on JSON styles */
        gmp-map[data-lighting-mode="night"][data-map-type="roadmap"] {
           filter: brightness(0.9) contrast(1.2) hue-rotate(10deg) !important;
        }
        
        /* Day Mode (06:00 - 18:00): Lighter, less saturated, subtle cyan overlay */
        gmp-map[data-lighting-mode="day"] {
          filter: brightness(0.95) contrast(1.15) sepia(0.4) hue-rotate(180deg) saturate(2.5) !important;
        }

        /* Twilight Mode (05:00-06:00, 18:00-19:00): Transition blend */
        gmp-map[data-lighting-mode="twilight"] {
          filter: grayscale(0.6) brightness(0.82) contrast(1.25) sepia(0.8) hue-rotate(185deg) saturate(3.5) !important;
        }

        /* Street View Panorama styling */
        .gm-style-pano {
          filter: grayscale(0.3) brightness(0.9) contrast(1.1) sepia(0.3) hue-rotate(180deg) saturate(2) !important;
        }

        /* Unified Control Row - Horizontal with slide animation */
        .map-controls-group {
          position: absolute;
          top: -44px; /* Fully hidden behind top bar */
          left: 220px; /* Positioned near INTERACTIVE_FEED label */
          transform: none;
          display: flex;
          flex-direction: row; /* Horizontal */
          gap: 0;
          width: fit-content; /* Size to content only */
          background: rgba(0, 10, 20, 0.7); 
          border: none; /* No border */
          border-radius: 0 0 8px 8px;
          box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
          overflow: visible;
          z-index: 100;
          pointer-events: auto;
          backdrop-filter: blur(8px);
          transition: top 0.35s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.35s ease;
          opacity: 0.15; /* Almost invisible when hidden */
        }
        
        /* Hover trigger area - extends above the panel */
        .map-controls-group::before {
          content: '';
          position: absolute;
          top: -30px;
          left: -30px;
          right: -30px;
          height: 80px; /* Extended hover area */
          z-index: -1;
        }
        
        /* Slide in on hover */
        .map-controls-group:hover,
        .map-content-container:hover .map-controls-group {
          top: 0px; /* Slide down into view */
          opacity: 1; /* Fully visible when shown */
        }

        .control-section {
          padding: 2px 6px;
          display: flex;
          flex-direction: row; /* Horizontal within sections too */
          align-items: center;
          height: 40px;
        }

        /* Pegman section styling */
        .pegman-section {
          padding-right: 8px;
        }
        
        /* Draggable Pegman Icon */
        .pegman-draggable {
          width: 36px;
          height: 36px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #ff9800;
          cursor: grab;
          border-radius: 4px;
          transition: all 0.25s ease;
          position: relative;
        }
        
        .pegman-draggable:hover {
          color: #ffb74d;
          background: rgba(255, 152, 0, 0.2);
          transform: scale(1.15);
          box-shadow: 0 0 15px rgba(255, 152, 0, 0.4);
        }
        
        .pegman-draggable:active {
          cursor: grabbing;
          transform: scale(0.9);
          color: #ffa726;
        }
        
        .pegman-draggable svg {
          filter: drop-shadow(0 0 3px currentColor);
          transition: filter 0.2s;
        }
        
        .pegman-draggable:hover svg {
          filter: drop-shadow(0 0 8px currentColor);
        }
        
        /* Pegman dragging state */
        .pegman-draggable.dragging {
          cursor: grabbing;
          color: #ff5722;
          transform: scale(1.2);
          box-shadow: 0 0 20px rgba(255, 87, 34, 0.6);
          animation: pegman-pulse 0.5s ease infinite alternate;
        }
        
        @keyframes pegman-pulse {
          from { box-shadow: 0 0 15px rgba(255, 152, 0, 0.5); }
          to { box-shadow: 0 0 25px rgba(255, 87, 34, 0.8); }
        }

        /* Road highlighting when Pegman is being dragged */
        /* Orange glow effect on the entire map to emphasize roads */
        gmp-map.pegman-drag-active {
          filter: contrast(1.1) saturate(1.2) brightness(1.05) !important;
          /* Add orange tint overlay via box-shadow workaround */
        }
        
        /* Orange road overlay via pseudo-element on container */
        .map-content-container:has(gmp-map.pegman-drag-active)::after {
          content: '';
          position: absolute;
          inset: 0;
          background: radial-gradient(circle at center, transparent 30%, rgba(255, 152, 0, 0.1) 100%);
          pointer-events: none;
          z-index: 50;
          animation: road-glow 1s ease infinite alternate;
        }
        
        @keyframes road-glow {
          from { opacity: 0.5; }
          to { opacity: 0.9; }
        }
        
        /* Pegman floating animation when being dragged */
        @keyframes pegman-float {
          from { transform: translateY(0px) scale(1); }
          to { transform: translateY(-3px) scale(1.05); }
        }
        
        /* Filter Toggle Button Styles */
        .filter-toggle-btn {
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
          border-radius: 2px;
        }
        
        .filter-toggle-btn:hover:not(.disabled) {
          background: rgba(0, 163, 255, 0.3);
          color: #00e5ff;
          filter: drop-shadow(0 0 5px #00e5ff);
        }
        
        .filter-toggle-btn.active {
          color: #00e5ff;
          background: rgba(0, 163, 255, 0.4);
          box-shadow: inset 0 0 8px rgba(0, 229, 255, 0.4);
        }
        
        .filter-toggle-btn.disabled {
          color: rgba(100, 100, 100, 0.4);
          cursor: not-allowed;
          opacity: 0.4;
        }
        
        /* Cyberpunk filter for satellite/hybrid maps when enabled */
        gmp-map[data-map-type="satellite"][data-cyberpunk-filter="enabled"],
        gmp-map[data-map-type="hybrid"][data-cyberpunk-filter="enabled"] {
          /* Sepia(1) + 150deg = Bright Cyan / Light Blue (Turquoise) */
          /* Increased brightness to 1.1 to make it 'lighter' as requested */
          filter: sepia(1) hue-rotate(150deg) saturate(3) contrast(1.1) brightness(1.1);
        }
        
        /* Natural view - no filter */
        gmp-map[data-map-type="satellite"][data-cyberpunk-filter="disabled"],
        gmp-map[data-map-type="hybrid"][data-cyberpunk-filter="disabled"] {
          filter: none;
        }
        
        /* Roadmap always uses night style, ABSOLUTELY NO FILTER */
        gmp-map[data-map-type="roadmap"] {
          filter: none !important;
        }
        
        /* Native Pegman Control - Styled via shadow DOM injection */
        /* These are fallback styles in case shadow DOM injection fails */
        .gm-svpc {
           cursor: grab !important;
        }
        
        .gm-svpc:active {
           cursor: grabbing !important;
        }

        .control-separator-vertical {
          width: 1px;
          background: rgba(0, 163, 255, 0.2);
          height: 60%;
          margin: 0 4px;
        }

        .map-type-btn, .zoom-btn {
          width: 32px;
          height: 32px;
          background: transparent;
          border: none;
          color: rgba(0, 229, 255, 0.8);
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s;
          border-radius: 2px;
        }

        .map-type-btn:hover, .zoom-btn:hover {
          background: rgba(0, 163, 255, 0.3);
          color: #fff;
          filter: drop-shadow(0 0 5px #00e5ff);
        }
        
        .map-type-btn.active {
          background: rgba(0, 163, 255, 0.5); /* Stronger active state */
          color: #00e5ff;
          box-shadow: inset 0 0 10px rgba(0, 229, 255, 0.5);
          border-bottom: 2px solid #00e5ff; /* Horizontal indicator */
          border: none;
        }
        
        .control-label {
           display: none; /* Hide labels for compact horizontal bar */
        }

        /* Loading Overlay */
        .map-loading-overlay {
          position: absolute;
          inset: 0;
          width: 100%;
          height: 100%;
          z-index: 50; /* Above map layer but below controls if needed, though here it's inside controls layer */
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 16px;
          background: rgba(0,0,0,0.5); /* Semi-transparent dimming */
          pointer-events: none;
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
