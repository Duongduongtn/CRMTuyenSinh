import { ref, watch } from 'vue'

const open = ref(false)

// Khoá scroll body khi drawer mở để swipe không lọt qua backdrop trên mobile.
// Singleton ref + watch global → install 1 lần khi composable file evaluate.
if (typeof document !== 'undefined') {
  watch(open, (v) => {
    document.body.style.overflow = v ? 'hidden' : ''
  })
}

function close() {
  open.value = false
}

function toggle() {
  open.value = !open.value
}

export function useMobileNav() {
  return { open, close, toggle }
}
