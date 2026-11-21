import styles from './Logo.module.css'

/** Cup with a ticket notch: the BrewPass mark. */
export function Logo({ withWordmark = true }: { withWordmark?: boolean }) {
  return (
    <span className={styles.logo}>
      <svg viewBox="0 0 32 32" width="32" height="32" aria-hidden focusable="false">
        <rect width="32" height="32" rx="8" fill="var(--color-accent)" />
        <path d="M8 11h13v7a6 6 0 0 1-6 6h-1a6 6 0 0 1-6-6z" fill="var(--cream)" />
        <path d="M21 13h2a3 3 0 0 1 0 6h-2" fill="none" stroke="var(--cream)" strokeWidth="2" />
      </svg>
      {withWordmark && <span className={styles.wordmark}>BrewPass</span>}
    </span>
  )
}
