import { useNavigate, useSearchParams } from 'react-router'

import { ProfileForm } from '../components/ProfileForm'
import { Card } from '../components/ui/Card'
import { ErrorState, LoadingState } from '../components/ui/StateMessage'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { useMe } from '../hooks/useMe'
import { safeNext } from '../lib/navigation'
import styles from './Page.module.css'

/** First sign-in: complete the profile before using the app. */
export function WelcomePage() {
  useDocumentTitle('Welcome')
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const me = useMe()

  return (
    <div className={styles.narrow}>
      <h1>Welcome to BrewPass</h1>
      <p className={styles.lead}>A couple of details and your first cup is a tap away.</p>
      <Card>
        {me.isPending && <LoadingState label="Loading your profile…" />}
        {me.isError && <ErrorState error={me.error} onRetry={() => void me.refetch()} />}
        {me.isSuccess && (
          <ProfileForm
            user={me.data}
            submitLabel="Continue"
            onSaved={() => navigate(safeNext(params.get('next')), { replace: true })}
          />
        )}
      </Card>
    </div>
  )
}
