---
description: Execute the approved research plan by spawning parallel subagents for each angle.
handoffs:
  - label: Synthesize Report
    agent: mk.report
    prompt: Synthesize findings from the latest research session
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

1. **Run `marketkit context` from project root**: Parse JSON for `PROJECT_ROOT`, `RESEARCH_DIR`, `BRIEF`, `AVAILABLE_DOCS`, `PLANS`.

2. **Gate check**: If `brief.md` is not in `AVAILABLE_DOCS`, stop and tell the user: "No brief found. Run `/mk.specify` first." If `PLANS` is empty or no plan has `has_plan: true`, stop and tell the user: "No plan found. Run `/mk.plan` first."

3. **Find latest plan**: From `PLANS`, find the most recent entry with `has_plan: true`. Set `PLAN_NAME` to its `name`. Set `PLAN_DIR` to `{RESEARCH_DIR}/plans/{PLAN_NAME}` and `DATA_DIR` to `{PLAN_DIR}/data`.

4. **Brief quality gate**: Read `{BRIEF}` and scan for `[TODO]`, `[NEEDS CLARIFICATION]`, or empty required sections. If any are found, use `AskUserQuestion`:
   - Question: "Your brief has unresolved items: [list them]. How should we proceed?"
   - Options: "Proceed anyway — research with what we have", "Fix brief first — run /mk.specify"

5. **Load plan**: Read `{PLAN_DIR}/plan.md`. Parse the new plan format:
   - Extract the **Context** section (hypothesis, ICPs with language patterns and pain signals, competitors)
   - Extract each **Angle** section: name, investigation goal, signals to find, related ICPs, sources

6. **Select angles to execute**: First ask whether to run all angles or pick specific ones:

   ```
   AskUserQuestion:
     Question 1: "Your plan has N angles. Run all of them?"
       Header: "Scope"
       multiSelect: false
       Options:
         - "Run all N angles (Recommended)" — "Execute every angle in the plan"
         - "Let me pick" — "Choose specific angles to run"
   ```

   If the user picks "Let me pick", then show a `multiSelect` with individual angles:
   - Header: "Angles"
   - Question: "Which angles should we execute?"
   - Options: One per angle (label = angle name, description = investigation goal summary + sources)

7. **Execution mode**: Use `AskUserQuestion`:

   ```
   AskUserQuestion:
     Question 1: "How should agents run?"
       Header: "Mode"
       multiSelect: false
       Options:
         - "Teammates — visible (Recommended)" — "Agents appear as named teammates in your UI. You can see their progress and messages in real time."
         - "Sub-agents — background" — "Agents run as hidden sub-processes. Faster, but you only see results when they finish."
   ```

   **If Teammates mode:**
   - Use `TeamCreate` to create a team (e.g., team name `research-{PLAN_NAME}`)
   - Create tasks with `TaskCreate` — one per angle
   - Spawn each agent using the `Agent` tool with `team_name` and a descriptive `name` (e.g., `angle-1-pain-signals`)
   - Assign tasks to teammates with `TaskUpdate`
   - Teammates mark tasks completed and go idle when done
   - After all teammates finish, send `shutdown_request` to each, then `TeamDelete`

   **If Sub-agents mode:**
   - Spawn agents directly with the `Agent` tool (no team, no tasks)
   - All run in parallel as background sub-processes
   - Collect results when all complete

8. **Chrome check** (only if any selected angle uses `twitter` source): Playwright cannot launch Chrome if it's already running. Run:

   ```bash
   pgrep -x "Google Chrome" > /dev/null 2>&1 && echo "RUNNING" || echo "NOT_RUNNING"
   ```

   If Chrome is running, use `AskUserQuestion`:
   ```
   AskUserQuestion:
     Question 1: "Chrome is currently open. Playwright needs Chrome closed to scrape Twitter. Please close Chrome and confirm."
       Header: "Chrome"
       multiSelect: false
       Options:
         - "Done — Chrome is closed" — "I've closed Chrome, proceed with Twitter scraping"
         - "Skip Twitter — use other sources only" — "Run research without Twitter for now"
   ```

   If the user says "Done", re-check with `pgrep`. If still running, warn once more. If the user says "Skip Twitter", remove `twitter` from all angles' source lists for this run.

9. **Confirm execution**: Use `AskUserQuestion`:
   - Question: "Ready to execute N angles across M sources? Estimated cost: $X.XX"
   - Options: "Execute (Recommended)", "Cancel — go back to plan"

10. **Spawn agents**: For each selected angle, spawn an Agent (subagent_type: "general-purpose") using the mode chosen in step 7. Each agent receives:

   - The angle's full definition (name, investigation goal, signals to find)
   - Brief context from the plan (hypothesis, related ICPs with their full language patterns and pain signals, competitors)
   - Assigned sources for this angle
   - Instructions to **craft 2-4 queries per source** using ICP language patterns as vocabulary
   - Permission to adapt: if a query returns low signal, rephrase and retry (up to 3 rounds per source)
   - The Source Execution Reference (see below)
   - File naming: save results to `{DATA_DIR}/{angle_slug}-{source}.json` (one file per source per angle)

   **Agent prompt template:**

   > You are a market research agent. Your task is to investigate a specific research angle by searching across assigned sources.
   >
   > ## Your Angle
   > **[Angle name]**
   > **What to investigate:** [Investigation goal from plan]
   > **Signals to find:** [Signals list from plan]
   >
   > ## Brief Context
   > **Hypothesis:** [From plan context section]
   >
   > **Related ICPs:**
   > [For each related ICP, include name, language patterns, and pain signals from the plan]
   >
   > **Competitors:** [From plan context section]
   >
   > ## Your Sources
   > [List of assigned sources for this angle]
   >
   > ## Scoring
   > Score every post immediately after extraction. Total score = relevancy + popularity bonus (1-5).
   >
   > **Relevancy (1-3) — judge against this angle's investigation goal and signals:**
   > - **1** = Tangentially related — mentions the topic but no direct pain/insight
   > - **2** = Relevant — real pain, experience, or opinion on the topic
   > - **3** = Highly relevant — specific pain point, switching story, detailed complaint, actionable insight
   >
   > **Popularity bonus (+0-2) — mechanical threshold check:**
   > - **+0** = Low engagement (< 10 likes/upvotes)
   > - **+1** = Moderate (10-100 likes/upvotes)
   > - **+2** = High (100+ likes/upvotes)
   >
   > Include `"score": N` in each post's JSON output.
   >
   > ## Instructions
   > For each assigned source:
   > 1. Craft 2-4 search queries using the ICP language patterns as vocabulary. Use their actual words and phrases.
   > 2. Execute each query using the appropriate method (see Source Execution Reference below).
   > 3. If a query returns <5 relevant results, rephrase and retry (up to 3 rounds per source).
   > 4. Score each post using the scale above.
   > 5. Save all results to `{DATA_DIR}/{angle_slug}-{source}.json`
   >
   > When crafting queries:
   > - Use ICP language patterns verbatim — these are the actual words customers use
   > - Use quotes for exact phrases: `"switching from cursor"`
   > - Keep queries focused — one concept per query
   > - Adapt based on what you find — follow promising threads
   >
   > [Include Source Execution Reference for assigned sources]

   Launch all agents using the chosen mode (teammates or sub-agents).

11. **Wait for all agents** to complete.

12. **Generate session report**: Run `marketkit gather --plan {PLAN_NAME}` to merge all JSON files.
    Write `{PLAN_DIR}/report.md` with:
    - Total posts collected per angle and per source
    - Top posts by engagement per angle
    - Cost summary (twitter-api posts × $0.005, rest free)
    - Any errors or empty results

13. **Report**: Show session summary. Use `AskUserQuestion`:
    - Question: "Research session complete. What's next?"
    - Options: "Synthesize report — run /mk.report (Recommended)", "Run another session — collect more data", "Done for now"

## Source Execution Reference

Each angle in the plan has sources that determine how to execute searches.

### `twitter`

Search X/Twitter using Playwright with the user's logged-in Chrome session. Free, no API key needed.

Use the Playwright MCP tools to:
1. Navigate to `https://x.com/search?q={query}&src=typed_query&f=top`
2. Take a snapshot of the results
3. Extract tweets: author, text, engagement metrics, URL
4. **Scroll down to load more posts.** Twitter lazy-loads content — you must scroll and take new snapshots to see additional results. After each scroll, verify that new posts appeared that weren't in previous snapshots.
5. Repeat scroll → snapshot → extract until you have ~25-50 tweets or no new posts load.
6. **Before saving, critically evaluate:** Did you extract enough posts? Some pages require multiple scrolls to surface meaningful volume. If you only have <10 posts, scroll more. If scrolling yields no new results after 2 attempts, move on.

Score each post (relevancy 1-3 + popularity bonus 0-2) and include `"score": N` in the post dict.
Save results using `write_collection` with `source='twitter'`.

### `twitter-api` (paid)

Paid X API v2 collector. Costs ~$0.005/tweet. Only used when the user explicitly chose "Paid API" during `/mk.plan` source selection.

```bash
marketkit search-x-paid-api '{query}' \
  --output '{DATA_DIR}/{angle_slug}-twitter-api.json' \
  --angle '{angle}'
```

The command outputs JSON to stdout: `{"posts_collected": N, "output": "/abs/path"}`. On error (missing token, rate limit, HTTP), it prints to stderr and exits 1.

### `reddit-scrape`

Scrape Reddit via `.json` endpoints. Free, no auth, no API key.

**Rules:**
- Always set User-Agent header: `marketkit/1.0`
- Rate limit: 100 requests/min (plenty for research sessions)
- WebFetch does NOT work with Reddit — use `curl` via Bash tool

**Search a subreddit:**
```bash
curl -s -A "marketkit/1.0" \
  "https://www.reddit.com/r/{subreddit}/search.json?q={query}&sort=top&t=month&limit=25&restrict_sr=on"
```

**Search multiple subreddits:**
```bash
curl -s -A "marketkit/1.0" \
  "https://www.reddit.com/r/sub1+sub2+sub3/search.json?q={query}&sort=top&t=month&limit=25&restrict_sr=on"
```

**Search all of Reddit:**
```bash
curl -s -A "marketkit/1.0" \
  "https://www.reddit.com/search.json?q={query}&sort=relevance&t=month&limit=25"
```

**Get comments on a post:**
```bash
curl -s -A "marketkit/1.0" \
  "https://www.reddit.com/r/{subreddit}/comments/{post_id}.json?limit=25"
```

**Parameters:**

| Param | Values |
|-------|--------|
| `q` | search terms, `+` for spaces |
| `sort` | `relevance`, `hot`, `top`, `new`, `comments` |
| `t` | `hour`, `day`, `week`, `month`, `year`, `all` |
| `limit` | 1-100 |
| `restrict_sr` | `on` to restrict to specified subreddit(s) |
| `after` / `before` | pagination cursors (e.g., `t3_abc123`) |

**Data returned:** `title`, `selftext` (full body), `score`, `upvote_ratio`, `num_comments`, `author`, `created_utc`, `url`, `subreddit`, `permalink`.

Score each post (relevancy 1-3 + popularity bonus 0-2) and include `"score": N` in the post dict.
Parse the JSON response, extract posts from `data.children[].data`, and save using `write_collection` with `source='reddit-scrape'`.

## Important

- All agents run in parallel — one per angle for maximum speed
- Each agent writes one JSON file per source (no write conflicts): `{angle_slug}-{source}.json`
- Posts are tagged with `angle` and `source` at collection time
- Agents craft their own queries at execution time using ICP language patterns
- Agents can adapt: if a query returns low signal, they rephrase and retry
- Actual ICP classification happens in `/mk.report`
- If an agent fails, report the error but don't block other agents
- Display cost after collection completes

## Behavior Rules

- Use `AskUserQuestion` for every gate and decision point
- Always put your recommended option first with "(Recommended)" in the label
- Show progress as agents complete (not just final results)
