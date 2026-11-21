import { describe, expect, it } from 'vitest'

import { safeNext } from './navigation'
import { formatPhone, normalizePhone } from './phone'

describe('normalizePhone', () => {
  it.each(['05321112233', '0532 111 22 33', '5321112233', '+90 532 111 22 33', '0090 532 1112233'])(
    'accepts %s',
    (input) => expect(normalizePhone(input)).toBe('+905321112233'),
  )

  it.each(['12345', '02121112233', '+15551234567', ''])('rejects %s', (input) =>
    expect(normalizePhone(input)).toBeNull(),
  )

  it('formats E.164 numbers for display', () => {
    expect(formatPhone('+905321112233')).toBe('+90 532 111 22 33')
  })
})

describe('safeNext', () => {
  it.each([
    ['/profile', '/profile'],
    [null, '/'],
    ['https://evil.example', '/'],
    ['//evil.example', '/'],
  ])('%s -> %s', (input, expected) => expect(safeNext(input)).toBe(expected))
})
