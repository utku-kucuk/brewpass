import styles from './Spinner.module.css'

interface SpinnerProps {
  size?: number
  /** Accessible label; pass an empty string when the parent already announces loading. */
  label?: string
}

export function Spinner({ size = 24, label = 'Loading' }: SpinnerProps) {
  return (
    <span
      className={styles.spinner}
      style={{ width: size, height: size }}
      role={label ? 'status' : undefined}
      aria-label={label || undefined}
      aria-hidden={label ? undefined : true}
    />
  )
}
