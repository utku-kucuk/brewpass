import { useEffect } from 'react'

/** Sets a descriptive tab title per page (also announced by screen readers on navigation). */
export function useDocumentTitle(title: string) {
  useEffect(() => {
    document.title = `${title} · BrewPass`
  }, [title])
}
