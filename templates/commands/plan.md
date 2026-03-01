---
description: Generate a research plan from the brief, with dual-agent ideation, cost estimate, and interactive angle approval.
handoffs:
  - label: Execute Research
    agent: mk.research
    prompt: Execute the approved research plan
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

1. **Run `marketkit context` from project root**: Parse JSON for `PROJECT_ROOT`, `RESEARCH_DIR`, `BRIEF`, `TEMPLATES_DIR`, `AVAILABLE_DOCS`.

2. **Gate check**: If `brief.md` is not in `AVAILABLE_DOCS`, stop and tell the user: "No brief found. Run `/mk.specify` first to define your research brief."

3. **Load brief**: Read `{BRIEF}` — extract ICPs (with language patterns and pain signals), competitors, hypothesis.

4. **Load plan template**: Read `{TEMPLATES_DIR}/plan-template.md` to understand the output format.

5. **Dual-agent ideation**: Spawn 2 parallel `general-purpose` agents. Give each the same brief context (hypothesis, ICPs with language patterns and pain signals, competitors) but with different creative lenses:

   **Agent A — Demand-side lens:**
   > You are a market researcher focused on **demand signals**. Given the brief context below, propose 6-8 research angles focused on: pain discovery, unmet needs, behavioral signals, workarounds people use, emotional patterns (frustration, resignation, excitement about alternatives).
   >
   > For each angle, provide:
   > - **Name**: Short descriptive name
   > - **What to investigate**: 2-3 sentences describing the investigation goal
   > - **Signals to find**: Bullet list of specific signals to look for
   > - **Related ICPs**: Which ICPs from the brief this angle targets
   > - **Suggested sources**: Which sources would yield the best signal (twitter, reddit)
   >
   > [Include full brief context: hypothesis, ICPs with language patterns and pain signals, competitors]

   **Agent B — Supply-side lens:**
   > You are a market researcher focused on **supply gaps**. Given the brief context below, propose 6-8 research angles focused on: competitor gaps, what people build when existing tools fail, switching patterns, ecosystem gaps, failed alternatives, DIY solutions.
   >
   > For each angle, provide the same structure as above.
   >
   > [Include full brief context: hypothesis, ICPs with language patterns and pain signals, competitors]

   Each agent returns its angles as structured text.

6. **Merge angles**: Review both agents' outputs. Cluster overlapping angles, pick the best formulation from each pair, keep unique ones, and select the top 5-8 by hypothesis relevance and expected signal density.

7. **Display angles**: Show each merged angle using this format:

   ---

   ### Angle N — [Name]
   `ICPs: ICP 1, ICP 3`

   **What to investigate:** [2-3 sentences]
   **Signals to find:** [bullet list]
   **Suggested sources:** `twitter` `reddit`

   ---

   After displaying ALL angles, show a summary: `N angles proposed`

8. **Angle selection**: Use `AskUserQuestion` with a single `multiSelect` question:

   ```
   AskUserQuestion:
     Question 1: "Which angles should we research? (max 8)"
       Header: "Angles"
       multiSelect: true
       Options: One per angle (max 4 per question — batch into multiple calls if >4 angles)
         - Label: Angle name
         - Description: One-sentence investigation goal + ICPs
   ```

   If more than 4 angles, batch into multiple `AskUserQuestion` calls (max 4 questions per call).

   "Other" lets the user type a custom angle to add.

9. **Source selection**: After angles are chosen, use `AskUserQuestion` to select WHERE to search. Single global `multiSelect` — selected sources apply to all angles.

   ```
   AskUserQuestion:
     Question 1: "Where should we search across all selected angles?"
       Header: "Sources"
       multiSelect: true
       Options:
         - "Twitter/X" — "Search tweets and conversations"
         - "Reddit" — "Subreddit posts and comments, full text + scores"
   ```

9b. **Twitter method** (only if Twitter/X was selected): Use `AskUserQuestion` to choose how to search Twitter.

   ```
   AskUserQuestion:
     Question 1: "How should we search Twitter/X?"
       Header: "Twitter"
       multiSelect: false
       Options:
         - "Playwright + Chrome login — free (Recommended)" — "Uses Playwright with your logged-in Chrome session. No API key needed."
         - "Paid API — ~$0.005/tweet" — "Uses X API v2 with bearer token. Structured data, higher volume."
   ```

   Map the choice to source identifiers:
   - Playwright + Chrome login → source `twitter` (uses Playwright MCP)
   - Paid API → source `twitter-api` (uses `marketkit search-x-paid-api`)

10. **Summary matrix**: Display the angle × source matrix:

    | Angle | Sources | ICPs |
    |-------|---------|------|
    | AI tool switching | twitter, reddit | ICP 1, ICP 2 |
    | Workflow workarounds | reddit | ICP 1, ICP 3 |

    Show cost estimate: Fixed per-source-per-angle assumptions:
    - `twitter-api`: ~25 tweets × $0.005 = ~$0.125 per angle
    - `twitter`: free (Playwright + Chrome login)
    - `reddit-scrape`: ~25 posts per angle (free)

    Format: `N angles × M sources. ~$X.XX API + N free source-angle pairs.`

11. **Final approval**: Use `AskUserQuestion`:

    ```
    AskUserQuestion:
      Question 1: "N angles × M sources. ~$X.XX API + N free. Approve?"
        Header: "Plan"
        multiSelect: false
        Options:
          - "Approve and save plan (Recommended)" — "Save to plan.md and proceed to /mk.research"
          - "Add a new angle" — "Describe a new research direction to add"
          - "Revise" — "Give feedback on angles, sources, or scope"
    ```

    If the user selects "Add a new angle" or "Revise", iterate (max 2 rounds), then re-present.

12. **Create plan directory**: Run `marketkit new-plan {slug}` from project root (derive slug from brief topic, e.g., `ai-travel`). Parse JSON for `PLAN_DIR`, `DATA_DIR`, `PLAN_NAME`.

13. **Save**: Write approved plan to `{PLAN_DIR}/plan.md` using the plan template format. Include:
    - Header with metadata (date, angles count, cost estimate)
    - Brief context section (hypothesis, ICPs with language patterns, competitors)
    - One section per angle: name, goal, signals, related ICPs, sources
    - Source summary table
    - **No query strings** — research agents craft their own queries at execution time

14. **Report**: Show saved path (`{PLAN_DIR}/plan.md`). Suggest running `/mk.research` next.

## Sources

Each angle is tagged with source identifiers. The `/mk.research` command routes execution based on these.

| Source | How it runs | Cost |
|--------|------------|------|
| `twitter` | Playwright with logged-in Chrome session | Free |
| `twitter-api` | X API v2 via `marketkit search-x-paid-api` | ~$0.005/tweet |
| `reddit-scrape` | Agent fetches Reddit .json endpoints | Free |

## Behavior Rules

- Use `AskUserQuestion` at three points: angle selection, source selection, final approval
- Angle selection is a single multiSelect (batched if >4 angles)
- Source selection is global (one multiSelect for all angles)
- Always put recommended options first with "(Recommended)" in the label
- Show cost estimate in the final approval question
- Display angles in the rich format with signals and ICPs
- Never use blockquotes — use tables, headers, and bullet lists only
- No query strings are generated during planning — research agents craft queries at execution time
