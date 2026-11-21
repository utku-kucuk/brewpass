export function formatDistance(meters: number | null): string | null {
  if (meters === null) return null
  const roundedMeters = Math.round(meters / 10) * 10
  if (roundedMeters < 1000) return `${roundedMeters} m`
  // Math.round avoids toFixed float artefacts (4.85.toFixed(1) === "4.8").
  return `${(Math.round(meters / 100) / 10).toFixed(1)} km`
}

/** "07:30:00" -> "07:30" */
export const formatTime = (time: string) => time.slice(0, 5)

export function formatHours(opensAt: string | null, closesAt: string | null): string {
  if (!opensAt || !closesAt) return 'Closed'
  return `${formatTime(opensAt)}–${formatTime(closesAt)}`
}

// Turkish lira in its local style: ₺90,00
const currency = new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY' })

export const formatPrice = (amount: string | number) => currency.format(Number(amount))

export const CATEGORY_LABELS: Record<string, string> = {
  HOT_COFFEE: 'Hot coffee',
  COLD_COFFEE: 'Cold coffee',
  TEA: 'Tea',
  OTHER: 'Other drinks',
}
