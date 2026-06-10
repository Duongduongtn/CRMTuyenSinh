// Auth global middleware — gate trang cần đăng nhập.
// Cho phép `/dang-nhap` không cần auth.

export default defineNuxtRouteMiddleware((to) => {
  const publicPaths = ['/dang-nhap', '/quick']
  const isPublic = publicPaths.some(p => to.path === p || to.path.startsWith(p + '/'))
  if (isPublic) return

  if (!import.meta.client) return

  const { isAuthenticated, hydrate } = useAuth()
  hydrate()

  if (!isAuthenticated.value) {
    return navigateTo({ path: '/dang-nhap', query: { next: to.fullPath } })
  }
})
