// Browser-only progress store. Nothing leaves the browser.
export const PREFIX = 'cpdemo.v1.';
export const TRACK_KEY = `${PREFIX}track`;

function storage(): Storage | null {
	try {
		return window.localStorage;
	} catch {
		return null;
	}
}

export function get(key: string): string | null {
	return storage()?.getItem(key) ?? null;
}

export function set(key: string, value: string | null): void {
	const s = storage();
	if (!s) return;
	if (value === null) s.removeItem(key);
	else s.setItem(key, value);
	window.dispatchEvent(new CustomEvent('cpdemo:change'));
}

export function allKeys(): string[] {
	const s = storage();
	if (!s) return [];
	const keys: string[] = [];
	for (let i = 0; i < s.length; i++) {
		const key = s.key(i);
		if (key?.startsWith(PREFIX)) keys.push(key);
	}
	return keys;
}

export function stepsDone(lab: string): number {
	return allKeys().filter((k) => k.startsWith(`${PREFIX}${lab}.`) && get(k) === '1').length;
}

export function exportState(): string {
	const data: Record<string, string> = {};
	for (const key of allKeys()) data[key] = get(key) ?? '';
	return JSON.stringify({ version: 1, exported: new Date().toISOString(), data }, null, 2);
}

export function importState(text: string): number {
	const parsed = JSON.parse(text);
	const data = parsed?.data;
	if (!data || typeof data !== 'object') throw new Error('Not a progress file exported from this site.');
	let count = 0;
	for (const [key, value] of Object.entries(data)) {
		if (key.startsWith(PREFIX) && typeof value === 'string') {
			storage()?.setItem(key, value);
			count++;
		}
	}
	window.dispatchEvent(new CustomEvent('cpdemo:change'));
	return count;
}

export function resetAll(): void {
	for (const key of allKeys()) storage()?.removeItem(key);
	window.dispatchEvent(new CustomEvent('cpdemo:change'));
}

export function initCheckboxes(): void {
	for (const box of document.querySelectorAll<HTMLInputElement>('input[data-cp-key]')) {
		const key = box.dataset.cpKey!;
		box.checked = get(key) === '1';
		box.addEventListener('change', () => set(key, box.checked ? '1' : null));
	}
}
