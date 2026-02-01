/**
 * Custom Map Marker Types and Icons
 * Cyberpunk-styled SVG markers for different POI categories
 */

export type MarkerType =
  | 'restaurant'
  | 'hotel'
  | 'attraction'
  | 'custom'
  | 'origin'
  | 'destination';

export interface MarkerData {
  id: string;
  position: { lat: number; lng: number };
  title: string;
  type: MarkerType;
  data?: any;
  icon?: string;
  color?: string;
}

export interface RouteData {
  id: string;
  origin: { lat: number; lng: number };
  destination: { lat: number; lng: number };
  polyline: string;
  distance: string;
  duration: string;
  steps: any[];
  mode: string;
}

export interface MapState {
  markers: MarkerData[];
  routes: RouteData[];
  active_place: any | null;
  center: { lat: number; lng: number };
  zoom: number;
  map_type: string;
  layers: string[];
  agent_view: {
    image_path: string;
    heading: number;
    pitch: number;
    fov: number;
    timestamp: string;
  } | null;
}

/**
 * Get SVG icon for marker type with cyberpunk glow effect
 */
export function getMarkerIcon(type: MarkerType, color?: string): string {
  const glowColor = color || getMarkerColor(type);

  const icons: Record<MarkerType, string> = {
    restaurant: `
      <svg width="40" height="50" viewBox="0 0 40 50" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <filter id="glow-${type}">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>
        <path d="M20 0 L30 40 L20 50 L10 40 Z" fill="${glowColor}" filter="url(#glow-${type})" opacity="0.9"/>
        <circle cx="20" cy="20" r="8" fill="#020a10" stroke="${glowColor}" stroke-width="2"/>
        <text x="20" y="25" font-size="16" text-anchor="middle" fill="${glowColor}">🍴</text>
      </svg>
    `,
    hotel: `
      <svg width="40" height="50" viewBox="0 0 40 50" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <filter id="glow-${type}">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>
        <path d="M20 0 L30 40 L20 50 L10 40 Z" fill="${glowColor}" filter="url(#glow-${type})" opacity="0.9"/>
        <circle cx="20" cy="20" r="8" fill="#020a10" stroke="${glowColor}" stroke-width="2"/>
        <text x="20" y="25" font-size="16" text-anchor="middle" fill="${glowColor}">🏨</text>
      </svg>
    `,
    attraction: `
      <svg width="40" height="50" viewBox="0 0 40 50" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <filter id="glow-${type}">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>
        <path d="M20 0 L30 40 L20 50 L10 40 Z" fill="${glowColor}" filter="url(#glow-${type})" opacity="0.9"/>
        <circle cx="20" cy="20" r="8" fill="#020a10" stroke="${glowColor}" stroke-width="2"/>
        <text x="20" y="25" font-size="16" text-anchor="middle" fill="${glowColor}">⭐</text>
      </svg>
    `,
    custom: `
      <svg width="40" height="50" viewBox="0 0 40 50" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <filter id="glow-${type}">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>
        <path d="M20 0 L30 40 L20 50 L10 40 Z" fill="${glowColor}" filter="url(#glow-${type})" opacity="0.9"/>
        <circle cx="20" cy="20" r="8" fill="#020a10" stroke="${glowColor}" stroke-width="2"/>
        <text x="20" y="25" font-size="16" text-anchor="middle" fill="${glowColor}">📍</text>
      </svg>
    `,
    origin: `
      <svg width="50" height="60" viewBox="0 0 50 60" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <filter id="glow-${type}">
            <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>
        <circle cx="25" cy="25" r="20" fill="#00ff00" filter="url(#glow-${type})" opacity="0.3"/>
        <circle cx="25" cy="25" r="12" fill="#020a10" stroke="#00ff00" stroke-width="3"/>
        <text x="25" y="31" font-size="18" text-anchor="middle" fill="#00ff00" font-weight="bold">A</text>
      </svg>
    `,
    destination: `
      <svg width="50" height="60" viewBox="0 0 50 60" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <filter id="glow-${type}">
            <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>
        <circle cx="25" cy="25" r="20" fill="#ff0000" filter="url(#glow-${type})" opacity="0.3"/>
        <circle cx="25" cy="25" r="12" fill="#020a10" stroke="#ff0000" stroke-width="3"/>
        <text x="25" y="31" font-size="18" text-anchor="middle" fill="#ff0000" font-weight="bold">B</text>
      </svg>
    `,
  };

  return icons[type] || icons.custom;
}

/**
 * Get marker color based on type
 */
export function getMarkerColor(type: MarkerType): string {
  const colors: Record<MarkerType, string> = {
    restaurant: '#00e5ff', // Cyan
    hotel: '#0080ff', // Blue
    attraction: '#ffff00', // Yellow
    custom: '#00e5ff', // Turquoise
    origin: '#00ff00', // Green
    destination: '#ff0000', // Red
  };
  return colors[type] || colors.custom;
}

/**
 * Decode Google Maps polyline to coordinates
 */
export function decodePolyline(encoded: string): Array<{ lat: number; lng: number }> {
  const points: Array<{ lat: number; lng: number }> = [];
  let index = 0;
  let lat = 0;
  let lng = 0;

  while (index < encoded.length) {
    let shift = 0;
    let result = 0;
    let byte;

    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);

    const dlat = result & 1 ? ~(result >> 1) : result >> 1;
    lat += dlat;

    shift = 0;
    result = 0;

    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);

    const dlng = result & 1 ? ~(result >> 1) : result >> 1;
    lng += dlng;

    points.push({
      lat: lat / 1e5,
      lng: lng / 1e5,
    });
  }

  return points;
}
