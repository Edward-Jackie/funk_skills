# OpenAI Presentations Skill

Create, edit, render, verify, and export PowerPoint or Google Slides decks.

## Source

- Provider: OpenAI
- Package: Codex primary runtime `presentations`
- Version: `26.802.11031`
- Upstream repository: https://github.com/openai/openai
- License: MIT

This directory contains the complete `skills/presentations` payload from the
bundled plugin, including the Codex Grid layout library, rendering helpers,
template-following tools, and Artifact Tool documentation.

## Runtime requirements

The skill requires `@oai/artifact-tool` for PPTX authoring. Codex supplies the
runtime through its workspace dependencies. Other agents such as OpenCode must
provide a compatible package and Node.js runtime before generation workflows
can execute successfully.
