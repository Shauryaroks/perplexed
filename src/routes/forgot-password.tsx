import { createRoute } from '@tanstack/react-router'
import type { RootRoute } from '@tanstack/react-router'

function ForgotPassword() {
  return <div className="w-screen h-screen flex justify-center items-center">
    Ma chuda
  </div>
}

export default (parentRoute: RootRoute) =>
  createRoute({
    path: '/forgot-password',
    component: ForgotPassword,
    getParentRoute: () => parentRoute,
  })
