import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'

import { toSessionUser, updateMe, type User } from '../api/auth'
import { ApiError } from '../lib/api'
import { useAuthStore } from '../lib/auth-store'
import { errorMessage } from '../lib/errors'
import { Button } from './ui/Button'
import { TextField } from './ui/TextField'

const splitList = (value: string) =>
  value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)

interface ProfileFormProps {
  user: Pick<User, 'full_name' | 'email' | 'preferences'>
  submitLabel: string
  onSaved?: (user: User) => void
}

export function ProfileForm({ user, submitLabel, onSaved }: ProfileFormProps) {
  const queryClient = useQueryClient()
  const setUser = useAuthStore((state) => state.setUser)
  const [fullName, setFullName] = useState(user.full_name ?? '')
  const [email, setEmail] = useState(user.email ?? '')
  const [drinks, setDrinks] = useState(user.preferences.favorite_drinks.join(', '))
  const [allergens, setAllergens] = useState(user.preferences.allergens.join(', '))
  const [nameError, setNameError] = useState<string>()

  const save = useMutation({
    mutationFn: updateMe,
    onSuccess: (saved) => {
      setUser(toSessionUser(saved))
      queryClient.setQueryData(['me'], saved)
      onSaved?.(saved)
    },
  })

  const fieldErrors = save.error instanceof ApiError ? save.error.fieldErrors() : {}
  const generalError =
    save.error && Object.keys(fieldErrors).length === 0 ? errorMessage(save.error) : undefined

  function submit(event: FormEvent) {
    event.preventDefault()
    if (fullName.trim().length < 2) {
      setNameError('Tell us your name (at least 2 characters).')
      return
    }
    setNameError(undefined)
    save.mutate({
      full_name: fullName.trim(),
      email: email.trim() || null,
      preferences: { favorite_drinks: splitList(drinks), allergens: splitList(allergens) },
    })
  }

  return (
    <form onSubmit={submit} noValidate>
      <TextField
        label="Full name"
        name="full_name"
        autoComplete="name"
        value={fullName}
        onChange={(event) => setFullName(event.target.value)}
        error={nameError ?? fieldErrors.full_name}
        required
      />
      <TextField
        label="Email (optional)"
        name="email"
        type="email"
        autoComplete="email"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        error={fieldErrors.email}
      />
      <TextField
        label="Favourite drinks (optional)"
        name="favorite_drinks"
        hint="Separate with commas, e.g. Flat White, Cortado"
        value={drinks}
        onChange={(event) => setDrinks(event.target.value)}
      />
      <TextField
        label="Allergens (optional)"
        name="allergens"
        hint="Separate with commas, e.g. lactose, nuts"
        value={allergens}
        onChange={(event) => setAllergens(event.target.value)}
      />
      {generalError && (
        <p role="alert" style={{ color: 'var(--color-danger)' }}>
          {generalError}
        </p>
      )}
      {save.isSuccess && !onSaved && <p role="status">Saved.</p>}
      <Button type="submit" fullWidth loading={save.isPending}>
        {submitLabel}
      </Button>
    </form>
  )
}
