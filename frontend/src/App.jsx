import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { PermissionProvider } from './context/PermissionContext'
import { ToastProvider } from './context/ToastContext'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/Layout'

const LoginPage = lazy(() => import('./pages/LoginPage'))
const RegisterPage = lazy(() => import('./pages/RegisterPage'))
const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const MessagesPage = lazy(() => import('./pages/MessagesPage'))
const MessageDetailPage = lazy(() => import('./pages/MessageDetailPage'))
const StatsPage = lazy(() => import('./pages/StatsPage'))
const DeadLettersPage = lazy(() => import('./pages/DeadLettersPage'))
const SubscriptionPage = lazy(() => import('./pages/SubscriptionPage'))
const PublishPage = lazy(() => import('./pages/PublishPage'))
const PermissionsPage = lazy(() => import('./pages/PermissionsPage'))
const RolePermissionsPage = lazy(() => import('./pages/RolePermissionsPage'))
const ProfilePage = lazy(() => import('./pages/ProfilePage'))
const UsersByRolePage = lazy(() => import('./pages/UsersByRolePage'))
const ChangePasswordPage = lazy(() => import('./pages/ChangePasswordPage'))

export default function App() {
  return (
    <ToastProvider>
      <AuthProvider>
        <PermissionProvider>
          <Suspense fallback={<div style={{ padding: 40, textAlign: 'center' }}>加载中...</div>}>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route element={<ProtectedRoute />}>
                <Route element={<Layout />}>
                  <Route path="/" element={<Navigate to="/dashboard" />} />
                  <Route path="/dashboard" element={<DashboardPage />} />
                  <Route path="/messages" element={<MessagesPage />} />
                  <Route path="/messages/:id" element={<MessageDetailPage />} />
                  <Route path="/stats" element={<StatsPage />} />
                  <Route path="/dead-letters" element={<DeadLettersPage />} />
                  <Route path="/subscriptions" element={<SubscriptionPage />} />
                  <Route path="/publish" element={<PublishPage />} />
                  <Route path="/permissions" element={<PermissionsPage />} />
                  <Route path="/admin/roles" element={<RolePermissionsPage />} />
                  <Route path="/users/:role" element={<UsersByRolePage />} />
                  <Route path="/profile" element={<ProfilePage />} />
                  <Route path="/change-password" element={<ChangePasswordPage />} />
                </Route>
              </Route>
            </Routes>
          </Suspense>
        </PermissionProvider>
      </AuthProvider>
    </ToastProvider>
  )
}
