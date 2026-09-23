export function url(path: string): string {
	const base = import.meta.env.BASE_URL.replace(/\/$/, '');
	const clean = path.replace(/^\//, '');
	const withSlash = clean === '' || clean.endsWith('/') || clean.includes('#') ? clean : `${clean}/`;
	return `${base}/${withSlash}`;
}
