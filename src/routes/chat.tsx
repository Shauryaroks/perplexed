import { createRoute } from '@tanstack/react-router'
import type { RootRoute } from '@tanstack/react-router'

function Chat() {

}

export default (parentRoute: RootRoute) =>
  createRoute({
    path: '/chat',
    component: Chat,
    getParentRoute: () => parentRoute,
  })
