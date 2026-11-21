import { useMutation } from '@tanstack/react-query'
import { ArrowLeft } from 'lucide-react'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Navigate, useNavigate, useSearchParams } from 'react-router'

import { requestCode, toSessionUser, verifyCode } from '../api/auth'
import { safeNext } from '../lib/navigation'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Logo } from '../components/ui/Logo'
import { errorMessage } from '../lib/errors'
import { TextField } from '../components/ui/TextField'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { ApiError } from '../lib/api'
import { isSignedIn, useAuthStore } from '../lib/auth-store'
import { formatPhone, normalizePhone } from '../lib/phone'
import styles from './SignInPage.module.css'

export function SignInPage() {
  useDocumentTitle('Sign in')
  const [params] = useSearchParams()
  const next = safeNext(params.get('next'))
  const navigate = useNavigate()
  const signedIn = useAuthStore(isSignedIn)
  const signIn = useAuthStore((state) => state.signIn)

  const [phoneInput, setPhoneInput] = useState('')
  const [phone, setPhone] = useState<string | null>(null)
  const [code, setCode] = useState('')
  const [phoneError, setPhoneError] = useState<string>()
  const codeRef = useRef<HTMLInputElement>(null)

  const sendCode = useMutation({
    mutationFn: requestCode,
    onSuccess: (result) => setPhone(result.phone_number),
  })

  const verify = useMutation({
    mutationFn: ({ phoneNumber, otp }: { phoneNumber: string; otp: string }) =>
      verifyCode(phoneNumber, otp),
    onSuccess: (result) => {
      const user = toSessionUser(result.user)
      signIn({ accessToken: result.access_token, refreshToken: result.refresh_token }, user)
      const target = user.profileCompleted ? next : `/welcome?next=${encodeURIComponent(next)}`
      navigate(target, { replace: true })
    },
  })

  useEffect(() => {
    if (phone) codeRef.current?.focus()
  }, [phone])

  if (signedIn && !verify.isSuccess) return <Navigate to={next} replace />

  function submitPhone(event: FormEvent) {
    event.preventDefault()
    const normalized = normalizePhone(phoneInput)
    if (!normalized) {
      setPhoneError('Enter a Turkish mobile number, e.g. 0555 123 45 67.')
      return
    }
    setPhoneError(undefined)
    sendCode.mutate(normalized)
  }

  function submitCode(event: FormEvent) {
    event.preventDefault()
    if (phone) verify.mutate({ phoneNumber: phone, otp: code })
  }

  function changeNumber() {
    setPhone(null)
    setCode('')
    verify.reset()
  }

  const verifyError = verify.error instanceof ApiError ? verify.error : null
  const remaining = (verifyError?.details as { remaining_attempts?: number } | null)
    ?.remaining_attempts

  return (
    <div className={styles.page}>
      <div className={styles.intro}>
        <Logo withWordmark={false} />
        <h1>Your daily cup, already paid for.</h1>
        <p>Sign in with your phone number to order at partner cafés.</p>
      </div>

      <Card className={styles.card}>
        {!phone ? (
          <form onSubmit={submitPhone} noValidate>
            <h2>Sign in or create an account</h2>
            <TextField
              label="Mobile number"
              name="phone"
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              placeholder="0555 123 45 67"
              value={phoneInput}
              onChange={(event) => setPhoneInput(event.target.value)}
              error={phoneError ?? (sendCode.error ? errorMessage(sendCode.error) : undefined)}
              required
            />
            <Button type="submit" fullWidth loading={sendCode.isPending}>
              Send code
            </Button>
          </form>
        ) : (
          <form onSubmit={submitCode} noValidate>
            <Button variant="ghost" className={styles.back} onClick={changeNumber}>
              <ArrowLeft size={16} aria-hidden /> Change number
            </Button>
            <h2>Enter your code</h2>
            <p className={styles.muted}>
              We sent a code to <strong>{formatPhone(phone)}</strong>.
            </p>
            <TextField
              ref={codeRef}
              label="One-time code"
              name="code"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              value={code}
              onChange={(event) => setCode(event.target.value.replace(/\D/g, ''))}
              hint={import.meta.env.DEV ? 'Demo environment: the code is 1234.' : undefined}
              error={
                verify.error
                  ? `${errorMessage(verify.error)}${remaining !== undefined ? ` ${remaining} attempts left.` : ''}`
                  : undefined
              }
              required
            />
            <Button type="submit" fullWidth loading={verify.isPending} disabled={code.length < 4}>
              Verify and continue
            </Button>
            <Button
              variant="ghost"
              fullWidth
              className={styles.resend}
              loading={sendCode.isPending}
              onClick={() => sendCode.mutate(phone)}
            >
              Send a new code
            </Button>
          </form>
        )}
      </Card>
    </div>
  )
}
