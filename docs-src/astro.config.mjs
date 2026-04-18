// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
	site: 'https://paperwise.dev',
	base: '/docs',
	outDir: '../website/docs',
	integrations: [
		starlight({
			title: 'Paperwise Docs',
			social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/zellux/paperwise' }],
			head: [
				{
					tag: 'script',
					attrs: {
						defer: true,
						src: 'https://cloud.umami.is/script.js',
						'data-website-id': '425d11c9-640e-4d9e-8319-3e4cd0914958',
					},
				},
			],
			components: {
				Header: './src/components/DocsHeader.astro',
			},
			sidebar: [
				{
					label: 'Start Here',
					items: [
						{ label: 'Getting Started', slug: 'getting-started' },
						{ label: 'Model Config', slug: 'model-config' },
					],
				},
				{
					label: 'Development',
					items: [
						{ label: 'Dev Environment Setup', slug: 'reference/local-development' },
						{ label: 'Repository Layout', slug: 'reference/repository-layout' },
					],
				},
				{
					label: 'Q&A',
					items: [{ label: 'Common Questions', slug: 'support' }],
				},
			],
		}),
	],
});
