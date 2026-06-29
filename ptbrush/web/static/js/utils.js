export const MASKED_SENTINEL = '***';

const SIZE_UNITS = [
    ['TiB', 1024 ** 4],
    ['GiB', 1024 ** 3],
    ['MiB', 1024 ** 2],
    ['KiB', 1024],
    ['B', 1],
];

const SPEED_UNITS = [
    ['GiB/s', 1024 ** 3],
    ['MiB/s', 1024 ** 2],
    ['KiB/s', 1024],
    ['B/s', 1],
];

export function formatBytes(bytes, decimals = 2) {
    if (!bytes) return '0 B';
    for (const [unit, factor] of SIZE_UNITS) {
        if (bytes >= factor) {
            return `${(bytes / factor).toFixed(decimals)} ${unit}`;
        }
    }
    return `${bytes} B`;
}

export function formatSpeed(bytesPerSecond) {
    return ((bytesPerSecond || 0) / (1024 * 1024)).toFixed(2);
}

export function formatGiB(bytes) {
    return ((bytes || 0) / (1024 ** 3)).toFixed(0);
}

export function truncate(text, max) {
    if (!text) return '';
    return text.length > max ? text.substring(0, max) + '...' : text;
}

export function sizeToBytes({ value, unit }) {
    const factor = Object.fromEntries(SIZE_UNITS)[unit] ?? 1;
    return Math.round(Number(value) * factor);
}

export function speedToBps({ value, unit }) {
    const factor = Object.fromEntries(SPEED_UNITS)[unit] ?? 1;
    return Math.round(Number(value) * factor);
}

export function expandWorkTime(s) {
    if (!s) return [];
    const hours = [];
    for (const part of s.split(',')) {
        const m = part.trim().match(/^(\d{1,2})-(\d{1,2})$/);
        if (!m) continue;
        const start = +m[1];
        const end = +m[2];
        if (start > end) continue;
        for (let h = start; h <= end && h <= 23; h++) {
            if (!hours.includes(h)) hours.push(h);
        }
    }
    return hours;
}

export function compressWorkTime(hours) {
    if (!hours || !hours.length) return '';
    const sorted = [...new Set(hours.filter(h => h >= 0 && h <= 23))].sort((a, b) => a - b);
    if (!sorted.length) return '';
    const ranges = [];
    let start = sorted[0];
    let prev = sorted[0];
    for (let i = 1; i < sorted.length; i++) {
        if (sorted[i] === prev + 1) {
            prev = sorted[i];
        } else {
            ranges.push(`${start}-${prev}`);
            start = prev = sorted[i];
        }
    }
    ranges.push(`${start}-${prev}`);
    return ranges.join(',');
}

export function isMasked(value) {
    return value === '' || value === MASKED_SENTINEL;
}
