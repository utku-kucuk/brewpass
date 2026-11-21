/** Only follow internal paths after sign-in (no open redirects). */
export function safeNext(value: string | null, fallback = '/'): string {
  if (!value || !value.startsWith('/') || value.startsWith('//')) return fallback
  return value
}
