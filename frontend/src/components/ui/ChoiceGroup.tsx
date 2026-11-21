import { useId } from 'react'

import styles from './ChoiceGroup.module.css'

interface ChoiceGroupProps<T extends string | number> {
  legend: string
  value: T
  options: { value: T; label: string }[]
  onChange: (value: T) => void
}

/** Radio buttons styled as pills; native radios keep keyboard and screen-reader behaviour. */
export function ChoiceGroup<T extends string | number>({
  legend,
  value,
  options,
  onChange,
}: ChoiceGroupProps<T>) {
  const name = useId()
  return (
    <fieldset className={styles.group}>
      <legend className={styles.legend}>{legend}</legend>
      <div className={styles.options}>
        {options.map((option) => (
          <label key={String(option.value)} className={styles.option}>
            <input
              type="radio"
              name={name}
              value={String(option.value)}
              checked={option.value === value}
              onChange={() => onChange(option.value)}
            />
            <span>{option.label}</span>
          </label>
        ))}
      </div>
    </fieldset>
  )
}
