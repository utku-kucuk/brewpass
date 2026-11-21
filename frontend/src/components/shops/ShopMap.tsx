import 'leaflet/dist/leaflet.css'

import L from 'leaflet'
import { useEffect, useMemo } from 'react'
import { CircleMarker, MapContainer, Marker, Popup, TileLayer, useMap } from 'react-leaflet'
import { Link } from 'react-router'

import type { ShopSummary } from '../../api/shops'
import type { Coordinates } from '../../hooks/useGeolocation'
import { formatDistance } from '../../lib/format'
import styles from './ShopMap.module.css'

/** Karaköy, Istanbul: the launch area, used when the member's location is unknown. */
const DEFAULT_CENTER: Coordinates = { lat: 41.0255, lng: 28.9744 }

const markerIcon = (open: boolean, selected: boolean) =>
  L.divIcon({
    className: '',
    html: `<span class="${[styles.marker, open ? styles.open : styles.closed, selected ? styles.selected : ''].join(' ')}"></span>`,
    iconSize: [28, 28],
    iconAnchor: [14, 28],
    popupAnchor: [0, -26],
  })

/**
 * Keeps every shop (and the member) in view. Leaflet measures its container once, so the map is
 * re-measured and re-fitted whenever the container is shown or resized (e.g. the mobile toggle).
 */
function FitToShops({ shops, user }: { shops: ShopSummary[]; user: Coordinates | null }) {
  const map = useMap()
  useEffect(() => {
    const fit = () => {
      map.invalidateSize()
      const points: L.LatLngTuple[] = shops.map((s) => [s.location.lat, s.location.lng])
      if (user) points.push([user.lat, user.lng])
      if (points.length === 0) return
      // No animation: a resize can trigger a second fit while the first is still animating.
      if (points.length === 1) map.setView(points[0], 15, { animate: false })
      else map.fitBounds(L.latLngBounds(points), { padding: [40, 40], maxZoom: 16, animate: false })
    }
    fit()
    const observer = new ResizeObserver(fit)
    observer.observe(map.getContainer())
    return () => observer.disconnect()
  }, [map, shops, user])
  return null
}

interface ShopMapProps {
  shops: ShopSummary[]
  userLocation: Coordinates | null
  selectedId?: string | null
  className?: string
}

export function ShopMap({ shops, userLocation, selectedId, className }: ShopMapProps) {
  const center = userLocation ?? DEFAULT_CENTER
  const icons = useMemo(
    () =>
      Object.fromEntries(shops.map((s) => [s.id, markerIcon(s.is_open_now, s.id === selectedId)])),
    [shops, selectedId],
  )

  return (
    <div className={[styles.wrapper, className].filter(Boolean).join(' ')}>
      <MapContainer
        center={[center.lat, center.lng]}
        zoom={14}
        scrollWheelZoom
        className={styles.map}
        aria-label="Map of partner cafés"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {userLocation && (
          <CircleMarker
            center={[userLocation.lat, userLocation.lng]}
            radius={8}
            pathOptions={{ color: '#f5eee6', weight: 3, fillColor: '#2b1d16', fillOpacity: 1 }}
          >
            <Popup>You are here</Popup>
          </CircleMarker>
        )}
        {shops.map((shop) => (
          <Marker
            key={shop.id}
            position={[shop.location.lat, shop.location.lng]}
            icon={icons[shop.id]}
            title={shop.name}
            alt={shop.name}
          >
            <Popup>
              <strong>{shop.name}</strong>
              <br />
              {shop.is_open_now ? 'Open now' : 'Closed'}
              {shop.distance_m !== null && ` · ${formatDistance(shop.distance_m)}`}
              <br />
              <Link to={`/shops/${shop.id}`}>See menu</Link>
            </Popup>
          </Marker>
        ))}
        <FitToShops shops={shops} user={userLocation} />
      </MapContainer>
    </div>
  )
}
