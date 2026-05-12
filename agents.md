# AGENTS.md

## Main working rule

Be conservative. Make the smallest correct change.

This project must stay clear, understandable, and easy to navigate. Do not create unnecessary files, services, abstractions, wrappers, or helper layers.

## Before changing code

Before editing, briefly analyze the existing structure.

Always check whether the requested change can be done by:
1. editing an existing file,
2. deleting or simplifying existing code,
3. moving logic to an already responsible module,
4. reusing an existing service/function/class.

Only create a new file when there is a clear architectural reason.

## Change-size limits

Default limits for one task:

- Change no more than 3 files unless clearly necessary.
- Do not add new directories unless explicitly requested.
- Do not add new dependencies unless explicitly requested.
- Do not add new architecture layers unless explicitly requested.
- Do not rewrite whole modules when a local edit is enough.

If a task seems to require more than 3 changed files, first explain why and propose the minimal file list.

## Output style

Keep answers short and practical.

Do not write long essays.
Do not repeat obvious explanations.
Do not describe every tiny internal step.
Do not produce huge summaries.

Use this format:

1. What I found
2. What I will change
3. Files affected
4. Final diff summary

Each section should be short.

## Coding style

Prefer simple code over clever code.

Avoid:
- duplicated logic,
- unnecessary abstractions,
- premature optimization,
- large refactors,
- hidden side effects,
- creating files just to make the change look organized.

Prefer:
- clear names,
- existing project patterns,
- small functions,
- removing dead code,
- reducing complexity,
- improving existing files instead of spawning new ones.

## Refactoring rules

Refactor only when it directly helps the requested task.

Do not refactor unrelated code.
Do not rename files/classes unless needed.
Do not move code unless the current location is clearly wrong.
Do not introduce new patterns if the project already has a pattern.

When deleting code, verify it is unused or replaced.

## Mental health app safety rules

This project is a mental health support app.

Do not add local clinical decision logic on the frontend if the backend already owns the decision pipeline.

Keep safety-critical logic centralized.

Do not let the LLM invent:
- crisis resources,
- phone numbers,
- diagnoses,
- clinical certainty,
- emergency instructions not supplied by backend.

Prefer backend-curated safety resources and validated response flow.

## Testing and validation

After changing code, mention the exact tests/checks that should be run.

Do not claim tests passed unless they were actually run.

If tests are not run, say:
"Not run: <reason>"

## Hard stop rules

Stop and ask before doing any of these:

- changing more than 3 files,
- adding a new dependency,
- adding a database migration,
- changing public API contracts,
- changing routing structure,
- creating a new service layer,
- deleting large blocks of code,
- rewriting a whole module.