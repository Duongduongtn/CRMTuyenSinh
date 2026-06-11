/**
 * Formatter VN: tiền tệ, số, ngày giờ. Áp dụng nguyên tắc CORE_RULES VN style.
 * Dùng locale `vi-VN` cho mọi nơi hiển thị user, KHÔNG cho data raw.
 */

const VN_LOCALE = 'vi-VN'
const VN_TZ = 'Asia/Ho_Chi_Minh'

/** Placeholder hiển thị khi giá trị trống. En-dash thay cho em-dash để khớp typography VN. */
export const NO_VALUE = '–'

const currencyFmt = new Intl.NumberFormat(VN_LOCALE, {
  style: 'currency',
  currency: 'VND',
  maximumFractionDigits: 0,
})

const numberFmt = new Intl.NumberFormat(VN_LOCALE, {
  maximumFractionDigits: 2,
})

const dateFmt = new Intl.DateTimeFormat(VN_LOCALE, {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  timeZone: VN_TZ,
})

const dateTimeFmt = new Intl.DateTimeFormat(VN_LOCALE, {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
  timeZone: VN_TZ,
})

const timeAgoUnits: Array<[number, Intl.RelativeTimeFormatUnit]> = [
  [60, 'second'],
  [60, 'minute'],
  [24, 'hour'],
  [30, 'day'],
  [12, 'month'],
  [Number.POSITIVE_INFINITY, 'year'],
]

const rtf = new Intl.RelativeTimeFormat(VN_LOCALE, { numeric: 'auto' })

export function formatVND(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === '') return NO_VALUE
  const n = typeof value === 'string' ? Number(value) : value
  if (Number.isNaN(n)) return NO_VALUE
  return currencyFmt.format(n)
}

export function formatNumber(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === '') return NO_VALUE
  const n = typeof value === 'string' ? Number(value) : value
  if (Number.isNaN(n)) return NO_VALUE
  return numberFmt.format(n)
}

export function formatDate(value: string | Date | null | undefined): string {
  if (!value) return NO_VALUE
  const d = typeof value === 'string' ? new Date(value) : value
  if (Number.isNaN(d.getTime())) return NO_VALUE
  return dateFmt.format(d)
}

export function formatDateTime(value: string | Date | null | undefined): string {
  if (!value) return NO_VALUE
  const d = typeof value === 'string' ? new Date(value) : value
  if (Number.isNaN(d.getTime())) return NO_VALUE
  return dateTimeFmt.format(d)
}

/** "5 phút trước", "2 giờ trước", "hôm qua"… */
export function timeAgo(value: string | Date | null | undefined): string {
  if (!value) return NO_VALUE
  const d = typeof value === 'string' ? new Date(value) : value
  if (Number.isNaN(d.getTime())) return NO_VALUE
  let diff = (d.getTime() - Date.now()) / 1000
  for (const [step, unit] of timeAgoUnits) {
    if (Math.abs(diff) < step) {
      return rtf.format(Math.round(diff), unit)
    }
    diff /= step
  }
  return formatDate(d)
}

/** SDT chuẩn VN: 0903 456 789 */
export function formatPhone(value: string | null | undefined): string {
  if (!value) return NO_VALUE
  const cleaned = value.replace(/\D/g, '')
  if (cleaned.length === 10) {
    return `${cleaned.slice(0, 4)} ${cleaned.slice(4, 7)} ${cleaned.slice(7)}`
  }
  return value
}
