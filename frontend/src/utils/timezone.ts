/**
 * Timezone utility functions for date formatting.
 */

// Cache for system timezone
let cachedTimezone: string | null = null
let cacheExpiry: number = 0

/**
 * Parse GMT offset string to minutes.
 * e.g., "GMT+9" -> 540, "GMT-5" -> -300, "GMT+5:30" -> 330
 */
export function parseGMTOffset(timezone: string): number {
  const match = timezone.match(/^GMT([+-])(\d{1,2})(?::(\d{2}))?$/)
  if (!match) return 0

  const sign = match[1] === '+' ? 1 : -1
  const hours = parseInt(match[2], 10)
  const minutes = parseInt(match[3] || '0', 10)

  return sign * (hours * 60 + minutes)
}

/**
 * Get the cached timezone or fetch from API.
 */
export async function getSystemTimezone(): Promise<string> {
  const now = Date.now()

  // Return cached value if still valid (cache for 5 minutes)
  if (cachedTimezone && cacheExpiry > now) {
    return cachedTimezone
  }

  try {
    // Dynamic import to avoid circular dependency
    const { getSystemSettings } = await import('@/services/settings')
    const settings = await getSystemSettings()
    cachedTimezone = settings.timezone || 'GMT+0'
    cacheExpiry = now + 5 * 60 * 1000 // 5 minutes
    return cachedTimezone
  } catch {
    return cachedTimezone || 'GMT+0'
  }
}

/**
 * Set timezone cache (called when settings are loaded).
 */
export function setTimezoneCache(timezone: string): void {
  cachedTimezone = timezone
  cacheExpiry = Date.now() + 5 * 60 * 1000
}

/**
 * Get cached timezone synchronously (returns default if not cached).
 */
export function getCachedTimezone(): string {
  return cachedTimezone || 'GMT+0'
}

/**
 * Format date string with the system timezone.
 * @param dateString - ISO date string (UTC from server)
 * @param timezone - GMT offset string (e.g., "GMT+9")
 * @param includeTime - Whether to include time in the output
 */
export function formatDateWithTimezone(
  dateString: string | null | undefined,
  timezone: string,
  includeTime: boolean = true
): string {
  if (!dateString) return '-'

  try {
    // Server sends UTC time without 'Z' suffix, so we need to append it
    // to ensure JavaScript parses it as UTC, not local time
    let normalizedDateString = dateString
    if (!dateString.endsWith('Z') && !dateString.includes('+') && !dateString.includes('-', 10)) {
      normalizedDateString = dateString + 'Z'
    }

    const date = new Date(normalizedDateString)
    if (isNaN(date.getTime())) return '-'

    // Get UTC timestamp and add timezone offset
    const offsetMinutes = parseGMTOffset(timezone)
    const targetTimestamp = date.getTime() + offsetMinutes * 60 * 1000

    // Create a new date with the adjusted timestamp
    // Use UTC methods to get the values (since we already applied the offset)
    const targetDate = new Date(targetTimestamp)

    const year = targetDate.getUTCFullYear()
    const month = targetDate.getUTCMonth()
    const day = targetDate.getUTCDate()
    const hours = targetDate.getUTCHours()
    const minutes = targetDate.getUTCMinutes()

    const monthNames = ['1월', '2월', '3월', '4월', '5월', '6월', '7월', '8월', '9월', '10월', '11월', '12월']

    if (includeTime) {
      const period = hours >= 12 ? '오후' : '오전'
      const hour12 = hours % 12 || 12
      return `${year}. ${monthNames[month]} ${day}. ${period} ${hour12}:${minutes.toString().padStart(2, '0')}`
    } else {
      return `${year}. ${monthNames[month]} ${day}.`
    }
  } catch {
    return '-'
  }
}

/**
 * Format date for display (date only, no time).
 */
export function formatDateOnly(
  dateString: string | null | undefined,
  timezone: string
): string {
  return formatDateWithTimezone(dateString, timezone, false)
}

/**
 * Format datetime using cached timezone (synchronous).
 */
export function formatDateTime(dateString: string | null | undefined): string {
  return formatDateWithTimezone(dateString, getCachedTimezone(), true)
}

/**
 * Format time only using cached timezone (synchronous).
 */
export function formatTime(dateString: string | null | undefined): string {
  if (!dateString) return '-'

  try {
    let normalizedDateString = dateString
    if (!dateString.endsWith('Z') && !dateString.includes('+') && !dateString.includes('-', 10)) {
      normalizedDateString = dateString + 'Z'
    }

    const date = new Date(normalizedDateString)
    if (isNaN(date.getTime())) return '-'

    const timezone = getCachedTimezone()
    const offsetMinutes = parseGMTOffset(timezone)
    const targetTimestamp = date.getTime() + offsetMinutes * 60 * 1000
    const targetDate = new Date(targetTimestamp)

    const hours = targetDate.getUTCHours()
    const minutes = targetDate.getUTCMinutes()

    const period = hours >= 12 ? '오후' : '오전'
    const hour12 = hours % 12 || 12
    return `${period} ${hour12}:${minutes.toString().padStart(2, '0')}`
  } catch {
    return '-'
  }
}
