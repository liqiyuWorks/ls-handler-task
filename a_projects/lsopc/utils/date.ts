/**
 * 平台统一使用北京时间（Asia/Shanghai, UTC+8）展示
 * 后端约定：库存 UTC，接口返回带 Z 的 UTC ISO；历史数据可能无 Z，此处按 UTC 解析。
 */

const BEIJING_TZ = 'Asia/Shanghai';

/** 将可能无 Z 的 UTC ISO 字符串转为可被正确解析的 UTC 字符串 */
function normalizeUtcIso(iso: string): string {
  const s = (iso || '').trim();
  if (!s) return s;
  if (/Z$/.test(s) || /[+-]\d{2}:?\d{2}$/.test(s)) return s;
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(s)) return s.replace(/\.?\d*$/, (m) => m ? m + 'Z' : 'Z');
  return s;
}

/**
 * 将 ISO 字符串或 Date 格式化为北京时间
 * @param isoOrDate ISO 字符串（如 2026-02-15T00:06:00Z）或 Date 或时间戳(ms)
 * @param options 同 Intl.DateTimeFormatOptions，不传则默认 年月日 时:分
 */
export function formatBeijingTime(
  isoOrDate: string | Date | number,
  options: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }
): string {
  try {
    let d: Date;
    if (typeof isoOrDate === 'object' && isoOrDate !== null && 'getTime' in isoOrDate) {
      d = isoOrDate as Date;
    } else if (typeof isoOrDate === 'string') {
      d = new Date(normalizeUtcIso(isoOrDate));
    } else {
      d = new Date(isoOrDate);
    }
    if (Number.isNaN(d.getTime())) return String(isoOrDate);
    return d.toLocaleString('zh-CN', { ...options, timeZone: BEIJING_TZ });
  } catch {
    return String(isoOrDate);
  }
}

/** 仅日期（年月日）北京时间 */
export function formatBeijingDate(isoOrDate: string | Date | number): string {
  return formatBeijingTime(isoOrDate, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
}
