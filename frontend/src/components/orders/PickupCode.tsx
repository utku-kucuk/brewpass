import { QRCodeSVG } from 'qrcode.react'

import styles from './PickupCode.module.css'

/** The signed pickup payload as a QR image, on white so scanners read it in dark mode too. */
export function PickupCode({ payload, orderId }: { payload: string; orderId: string }) {
  return (
    <figure className={styles.figure}>
      <div className={styles.qr}>
        <QRCodeSVG
          value={payload}
          size={220}
          level="M"
          marginSize={2}
          title="Pickup QR code"
          role="img"
          aria-label="Pickup QR code to show at the counter"
        />
      </div>
      <figcaption className={styles.caption}>
        Show this code at the counter.
        <span className={styles.ref}>Order #{orderId.slice(0, 8).toUpperCase()}</span>
      </figcaption>
    </figure>
  )
}
