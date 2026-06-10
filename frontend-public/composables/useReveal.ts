// Scroll reveal hook — gắn vào element có class .reveal.
// Dùng IntersectionObserver, respect prefers-reduced-motion.

export const useReveal = () => {
  if (process.server) return

  onMounted(() => {
    if (typeof IntersectionObserver === 'undefined') return
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add('in')
          io.unobserve(e.target)
        }
      })
    }, { threshold: 0.12, rootMargin: '0px 0px -60px 0px' })

    document.querySelectorAll('.reveal').forEach((el) => {
      if (reduce) {
        el.classList.add('in')
      } else {
        io.observe(el)
      }
    })
  })
}
