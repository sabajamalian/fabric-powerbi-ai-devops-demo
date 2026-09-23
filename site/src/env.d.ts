/// <reference path="../.astro/types.d.ts" />
declare const __REPO__: string;

declare module 'virtual:repo-files' {
	const files: Record<string, string>;
	export default files;
}
