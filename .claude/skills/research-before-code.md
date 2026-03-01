---
name: research-before-code
description: Research libraries, APIs, and services before implementing code. Use when about to integrate an external dependency, implement a new feature using a third-party library, or when the user says "implement", "integrate", or "add support for" something that involves external docs.
---

# Research-Before-Code Workflow

## When This Triggers

Before writing implementation code that touches an external library, API, or service you haven't verified docs for in this session.

## Steps

1. **Spawn a research teammate** with this prompt structure:

   > Research [library/service name]. Read current docs for [specific feature needed].
   > Focus on: integration patterns, required configuration, common pitfalls.
   > Report: recommended approach + minimal code example + version-specific gotchas.

2. **Wait for research results** before writing any implementation code.

3. **Validate the approach** — cross-reference at least two sources (official docs + examples/changelog) when available.

4. **Implement using verified patterns only.** No "likely" or "probably" assumptions about API behavior.

## Anti-Pattern: Guess-and-Patch

Never do this:
- Assume a config value "is probably X"
- Remove a validation check "to unblock"
- Ship code with a TODO to "tighten later"

If you don't know the correct value or behavior, research it. The 2 minutes spent reading docs saves hours of debugging wrong assumptions.
