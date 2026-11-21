import { LogOut, Receipt } from 'lucide-react'
import { Link } from 'react-router'

import { ProfileForm } from '../components/ProfileForm'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { ErrorState, LoadingState } from '../components/ui/StateMessage'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { useMe } from '../hooks/useMe'
import { useSignOut } from '../hooks/useSignOut'
import { formatPhone } from '../lib/phone'
import styles from './Page.module.css'

export function ProfilePage() {
  useDocumentTitle('Profile')
  const me = useMe()
  const signOut = useSignOut()

  return (
    <div className={styles.narrow}>
      <h1>Your profile</h1>
      {me.isPending && <LoadingState label="Loading your profile…" />}
      {me.isError && <ErrorState error={me.error} onRetry={() => void me.refetch()} />}
      {me.isSuccess && (
        <>
          <p className={styles.lead}>Signed in as {formatPhone(me.data.phone_number)}</p>
          <Card>
            <ProfileForm user={me.data} submitLabel="Save changes" />
          </Card>
          <div className={styles.profileFooter}>
            <Link to="/payments" className={styles.footerLink}>
              <Receipt size={16} aria-hidden /> Payment history
            </Link>
            <Button variant="secondary" icon={<LogOut size={16} aria-hidden />} onClick={signOut}>
              Sign out
            </Button>
          </div>
        </>
      )}
    </div>
  )
}
