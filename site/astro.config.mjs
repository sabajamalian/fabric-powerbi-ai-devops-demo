// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import starlightLinksValidator from 'starlight-links-validator';
import { unified } from '@astrojs/markdown-remark';
import repoFiles from './src/plugins/vite-repo-files.mjs';
import { fileURLToPath } from 'node:url';
import rehypeStepAnchors, { rehypeBaseLinks } from './src/plugins/rehype-step-anchors.mjs';

// Pages passes these from actions/configure-pages, so a copy of the template that turns on
// Pages gets working URLs without editing this file.
const origin = process.env.SITE_ORIGIN || 'https://sabajamalian.github.io';
const base = process.env.SITE_BASE ?? '/fabric-powerbi-ai-devops-demo';
const repo = process.env.SITE_REPO || 'sabajamalian/fabric-powerbi-ai-devops-demo';

export default defineConfig({
	site: origin,
	base,
	trailingSlash: 'always',
	markdown: {
		processor: unified({ rehypePlugins: [rehypeStepAnchors, [rehypeBaseLinks, { base }]] }),
	},
	vite: {
		plugins: [repoFiles({ repoRoot: fileURLToPath(new URL('..', import.meta.url)) })],
		define: {
			__REPO__: JSON.stringify(repo),
		},
	},
	integrations: [
		starlight({
			title: 'Contoso Pharmacy Copilot Lab',
			description:
				'A self-paced lab for GitHub Copilot agent customization on a Power BI semantic model. Synthetic data only.',
			logo: { src: './src/assets/logo.svg', alt: '' },
			favicon: '/favicon.svg',
			social: [{ icon: 'github', label: 'GitHub', href: `https://github.com/${repo}` }],
			editLink: { baseUrl: `https://github.com/${repo}/edit/main/site/` },
			customCss: ['./src/styles/custom.css'],
			lastUpdated: false,
			tableOfContents: { minHeadingLevel: 2, maxHeadingLevel: 3 },
			plugins: [starlightLinksValidator({ errorOnLocalLinks: true })],
			sidebar: [
				{
					label: 'Start here',
					items: [
						{ label: 'How this lab works', slug: 'start/how-this-lab-works' },
						{ label: 'Choose a track', slug: 'start/choose-a-track' },
						{ label: 'Prerequisites', slug: 'start/prerequisites' },
						{ label: 'Glossary', slug: 'start/glossary' },
						{ label: 'My progress', slug: 'progress' },
					],
				},
				{ label: 'Labs', items: [{ autogenerate: { directory: 'labs' } }] },
				{
					label: 'Present this demo',
					collapsed: true,
					items: [
						{ label: '30-minute demo', slug: 'present/30-minute-demo' },
						{ label: '60-minute demo', slug: 'present/60-minute-demo' },
						{ label: 'Facilitator checklist', slug: 'present/facilitator-checklist' },
						{ label: 'Fallbacks and reset', slug: 'present/fallbacks-and-reset' },
						{ label: 'Expected results', slug: 'present/expected-results' },
					],
				},
				{
					label: 'Reference',
					collapsed: true,
					items: [
						{ label: 'Architecture', slug: 'reference/architecture' },
						{ label: 'Copilot customization', slug: 'reference/copilot-customization' },
						{ label: 'Copilot surfaces', slug: 'reference/copilot-surfaces' },
						{ label: 'Agents', slug: 'reference/agents' },
						{ label: 'Skills', slug: 'reference/skills' },
						{ label: 'Prompts', slug: 'reference/prompts' },
						{ label: 'Hooks', slug: 'reference/hooks' },
						{ label: 'MCP servers', slug: 'reference/mcp' },
						{ label: 'APM and plugins', slug: 'reference/apm-and-plugins' },
						{ label: 'Synthetic data model', slug: 'reference/synthetic-data-model' },
						{ label: 'Business questions', slug: 'reference/business-questions' },
						{ label: 'Evaluation method', slug: 'reference/evaluation-methodology' },
						{ label: 'AI readiness checklist', slug: 'reference/ai-readiness-checklist' },
						{ label: 'Scripts', slug: 'reference/scripts' },
						{ label: 'CI workflows', slug: 'reference/ci-workflows' },
						{ label: 'Branches and pull requests', slug: 'reference/branching-and-pull-requests' },
					],
				},
				{
					label: 'Help',
					collapsed: true,
					items: [
						{ label: 'Troubleshooting', slug: 'help/troubleshooting' },
						{ label: 'FAQ', slug: 'help/faq' },
						{ label: 'Known limitations', slug: 'help/known-limitations' },
						{ label: 'Security and synthetic data', slug: 'help/security-and-synthetic-data' },
						{ label: 'Clean up', slug: 'help/clean-up' },
					],
				},
				{ label: 'Roadmap', slug: 'roadmap' },
			],
		}),
	],
});
