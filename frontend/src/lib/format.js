export function formatDateTime(isoString) {
  if (!isoString) return ''
  const d = new Date(isoString)
  if (Number.isNaN(d.getTime())) return isoString
  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(d)
}

export function formatBudgetAmount(value) {
  if (value == null || value === '') return ''
  const num = Number(value)
  if (Number.isNaN(num)) return String(value)
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(num)
}

export function formatDate(isoOrDate) {
  if (!isoOrDate) return ''
  const d = new Date(isoOrDate)
  if (Number.isNaN(d.getTime())) return String(isoOrDate)
  return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short' }).format(d)
}

export function toDatetimeLocalValue(isoString) {
  if (!isoString) return ''
  const d = new Date(isoString)
  if (Number.isNaN(d.getTime())) return ''
  const pad = (n) => String(n).padStart(2, '0')
  const y = d.getFullYear()
  const m = pad(d.getMonth() + 1)
  const day = pad(d.getDate())
  const h = pad(d.getHours())
  const min = pad(d.getMinutes())
  return `${y}-${m}-${day}T${h}:${min}`
}

export function fromDatetimeLocalValue(localValue) {
  if (!localValue) return ''
  const d = new Date(localValue)
  if (Number.isNaN(d.getTime())) return ''
  return d.toISOString()
}

export function todayISODateLocal() {
  const d = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

export function addDaysToISODate(isoDate, deltaDays) {
  if (!isoDate) return todayISODateLocal()
  const parts = isoDate.split('-').map(Number)
  const d = new Date(parts[0], parts[1] - 1, parts[2])
  d.setDate(d.getDate() + deltaDays)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

export function formatTimeShort(isoString) {
  if (!isoString) return ''
  const dt = new Date(isoString)
  if (Number.isNaN(dt.getTime())) return ''
  return new Intl.DateTimeFormat('pt-BR', { timeStyle: 'short' }).format(dt)
}
