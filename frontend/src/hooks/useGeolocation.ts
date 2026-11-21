import { useEffect, useState } from 'react'

export interface Coordinates {
  lat: number
  lng: number
}

export type GeolocationState =
  | { status: 'pending'; coords: null }
  | { status: 'granted'; coords: Coordinates }
  | { status: 'denied' | 'unavailable'; coords: null }

/** Asks once for the member's location; works without it (shops are then sorted by rating). */
export function useGeolocation(): GeolocationState {
  const [state, setState] = useState<GeolocationState>(() =>
    typeof navigator !== 'undefined' && 'geolocation' in navigator
      ? { status: 'pending', coords: null }
      : { status: 'unavailable', coords: null },
  )

  useEffect(() => {
    if (state.status !== 'pending') return
    let active = true
    navigator.geolocation.getCurrentPosition(
      (position) => {
        if (active) {
          setState({
            status: 'granted',
            coords: { lat: position.coords.latitude, lng: position.coords.longitude },
          })
        }
      },
      (error) => {
        if (active) {
          setState({
            status: error.code === error.PERMISSION_DENIED ? 'denied' : 'unavailable',
            coords: null,
          })
        }
      },
      { enableHighAccuracy: false, timeout: 8000, maximumAge: 5 * 60_000 },
    )
    return () => {
      active = false
    }
  }, [state.status])

  return state
}
