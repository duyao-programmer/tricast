import { usePermissionCtx } from '../context/PermissionContext'

export function usePermission() {
  const { components } = usePermissionCtx()

  return {
    canView: (componentKey) => components.includes(componentKey),
    components,
  }
}
