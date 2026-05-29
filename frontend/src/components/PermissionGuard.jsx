import { usePermission } from '../hooks/usePermission'

export default function PermissionGuard({ componentKey, fallback = null, children }) {
  const { canView } = usePermission()
  if (!canView(componentKey)) return fallback
  return children
}
