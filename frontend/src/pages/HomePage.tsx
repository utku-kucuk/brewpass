import { CreditCard, MapPin, QrCode } from 'lucide-react'

import { Card } from '../components/ui/Card'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { useAuthStore } from '../lib/auth-store'
import styles from './Page.module.css'

const STEPS = [
  { icon: CreditCard, title: 'Pick a pass', text: 'Sip, Daily or Bottomless — renews monthly.' },
  { icon: MapPin, title: 'Find a café', text: 'Partner shops near you, with live opening hours.' },
  { icon: QrCode, title: 'Show your code', text: 'Order ahead and pick up with a signed QR code.' },
]

export function HomePage() {
  useDocumentTitle('Home')
  const name = useAuthStore((state) => state.user?.fullName?.split(' ')[0])

  return (
    <>
      <section className={styles.hero}>
        <h1>{name ? `Good to see you, ${name}.` : 'Welcome to BrewPass.'}</h1>
        <p>Your daily cup, already paid for.</p>
      </section>
      <div className={styles.grid}>
        {STEPS.map(({ icon: Icon, title, text }) => (
          <Card key={title} className={styles.step}>
            <Icon className={styles.stepIcon} aria-hidden />
            <h2>{title}</h2>
            <p>{text}</p>
          </Card>
        ))}
      </div>
    </>
  )
}
