// Two small rehype plugins for lab content.
import { visit } from 'unist-util-visit';

const STEP = /^Step (\d+)\./;

function text(node) {
	if (node.type === 'text') return node.value;
	return (node.children || []).map(text).join('');
}

// Gives every "### Step N. Title" heading the id "step-N", so lab check hints can link to
// /labs/<lab>/#step-N. Runs before Astro assigns heading ids, which keeps an existing id.
export default function rehypeStepAnchors() {
	return (tree) => {
		visit(tree, 'element', (node) => {
			if (node.tagName !== 'h3') return;
			const match = STEP.exec(text(node).trim());
			if (match) node.properties = { ...node.properties, id: `step-${match[1]}` };
		});
	};
}

// Content links are written from the site root ("/labs/07-.../"). This adds the deploy base path
// (for example "/fabric-powerbi-ai-devops-demo"), so copies of the template with another repo
// name still get working links.
export function rehypeBaseLinks({ base = '/' } = {}) {
	const prefix = base.replace(/\/$/, '');
	return (tree) => {
		if (!prefix) return;
		visit(tree, 'element', (node) => {
			const href = node.tagName === 'a' ? node.properties?.href : undefined;
			if (typeof href === 'string' && href.startsWith('/') && !href.startsWith('//') && !href.startsWith(`${prefix}/`)) {
				node.properties.href = prefix + href;
			}
		});
	};
}
