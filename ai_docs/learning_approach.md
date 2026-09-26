# Learning Approach

## How this knowledge base grows

- User teaches concepts **incrementally** — provides source file locations + examples

- I create one `.md` file per concept/feature in `ai_docs/`

- I link each new doc in `index.md` (Documented Concepts section)

- I move the item from Pending → Documented in `todo.md`

## Session startup (mandatory)

When a new session starts and someone asks about the code:

1. Read `ai_docs/index.md` first to orient

2. Check `todo.md` to know what's already documented

3. Read `glossary.md` if terminology is unclear

4. Read the relevant concept doc if it exists before exploring source

## Running things

- If the environment allows it, run `python3 -m pytest` from the repo root, or the app via `./run.sh` (see `dev_environment.md`)

- If it doesn't (no shell, no dataset in `Input/`), ask the user to run and paste results

## Teaching protocol

When the user teaches a concept:

1. Ask clarifying questions if intent is unclear

2. Create `ai_docs/<concept>.md` (short, dense, AI-readable)

3. Add entry to `index.md` → Documented Concepts

4. Move item in `todo.md` Pending → Documented

## Doc file format

```

# <Concept Name>



## What it is

One sentence.



## Key files / paths

- `path/to/file` — role



## How it works

Bullet points. No prose padding.



## Gotchas / conventions

- Anything non-obvious

```
