/**
 * Client-side check for Turkish mobile numbers, mirroring the server's normalization
 * (`05xx…`, `5xx…`, `+905xx…`, `0090…`, with spaces or dashes). The server has the final say.
 */
export function normalizePhone(input: string): string | null {
  let digits = input.replace(/\D/g, '')
  if (digits.startsWith('0090')) digits = digits.slice(2)
  else if (digits.startsWith('0')) digits = `90${digits.slice(1)}`
  else if (digits.startsWith('5') && digits.length === 10) digits = `90${digits}`
  return /^905\d{9}$/.test(digits) ? `+${digits}` : null
}

/** +905321112233 -> +90 532 111 22 33 */
export function formatPhone(e164: string): string {
  const m = /^\+90(\d{3})(\d{3})(\d{2})(\d{2})$/.exec(e164)
  return m ? `+90 ${m[1]} ${m[2]} ${m[3]} ${m[4]}` : e164
}
