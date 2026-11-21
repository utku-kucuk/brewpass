import { ProfileForm } from '../components/ProfileForm'
import { Card } from '../components/ui/Card'
import { ErrorState, LoadingState } from '../components/ui/StateMessage'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { useMe } from '../hooks/useMe'
import { formatPhone } from '../lib/phone'
import styles from './Page.module.css'

export function ProfilePage() {
  useDocumentTitle('Profile')
  const me = useMe()

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
        </>
      )}
    </div>
  )
}
