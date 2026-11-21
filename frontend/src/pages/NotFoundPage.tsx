import { Link } from 'react-router'

import { EmptyState } from '../components/ui/StateMessage'
import { useDocumentTitle } from '../hooks/useDocumentTitle'

export function NotFoundPage() {
  useDocumentTitle('Page not found')
  return (
    <EmptyState
      title="This cup is empty"
      description="We couldn't find that page."
      action={<Link to="/">Back to home</Link>}
    />
  )
}
