import { AlertCircle, Coffee } from 'lucide-react'
import type { ReactNode } from 'react'

import { errorMessage } from '../../lib/errors'
import { Button } from './Button'
import { Spinner } from './Spinner'
import styles from './StateMessage.module.css'

export function LoadingState({ label = 'Brewing…' }: { label?: string }) {
  return (
    <div className={styles.state} role="status" aria-live="polite">
      <Spinner size={32} label="" />
      <p className={styles.text}>{label}</p>
    </div>
  )
}

interface ErrorStateProps {
  error: unknown
  title?: string
  onRetry?: () => void
}

export function ErrorState({ error, title = "That didn't work", onRetry }: ErrorStateProps) {
  return (
    <div className={styles.state} role="alert">
      <AlertCircle className={styles.errorIcon} size={32} aria-hidden />
      <h2 className={styles.title}>{title}</h2>
      <p className={styles.text}>{errorMessage(error)}</p>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  )
}

interface EmptyStateProps {
  title: string
  description?: string
  action?: ReactNode
  icon?: ReactNode
}

export function EmptyState({ title, description, action, icon }: EmptyStateProps) {
  return (
    <div className={styles.state}>
      {icon ?? <Coffee className={styles.icon} size={32} aria-hidden />}
      <h2 className={styles.title}>{title}</h2>
      {description && <p className={styles.text}>{description}</p>}
      {action}
    </div>
  )
}
