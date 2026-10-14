# AGENTS.md

Instructions for AI coding agents working in this repository. Human-facing workflow is in [SETUP.md](SETUP.md); follow it as well.

## Project

University group project (CSC14003 Intro to AI, HCMUS): reimplement the puzzle game **Bloxorz** in Python with a GUI, and solve stages with **BFS, DFS/IDS, UCS, A\***. Deadline: before 2026-11-01.

- Requirements (source of truth): [docs/AI - Project 1.md](docs/AI%20-%20Project%201.md)
- Task owners and schedule: [docs/PHAN_CONG.md](docs/PHAN_CONG.md)

## Who you are working for

Five members share this repo. At the start of a session, find out which member you are working for (ask if unclear) and read their row in `docs/PHAN_CONG.md`. Stay inside that member's area:

| Member | Area |
|---|---|
| Cao (leader) | `bloxorz/core/`: state, orientation transition table, `Problem` interface, level loader |
| Long | `bloxorz/core/`: advanced tiles: fragile, bridges, soft/heavy/split switches, split/merge |
| Đức | `bloxorz/gui/`, `main.py`, `Source/README.md` |
| Nghĩa | `bloxorz/solvers/`: BFS, DFS/IDS, metrics; `benchmark/` |
| Minh | `bloxorz/solvers/`: UCS, A\*, heuristics, cost function; `levels/` |

If the task needs changes outside that area, say so and let the member coordinate with the owner instead of editing silently.

Talk to the member in **Vietnamese**. Write code, identifiers, comments, commit messages and PR titles in **English**.

## Hard constraints

- Python 3.10+. Code lives under `Source/`; run all commands from `Source/` with the project venv.
- **Search algorithms must be implemented by hand.** Do not use libraries that perform search or pathfinding (`networkx`, `simpleai`, `aima`, `pathfinding`, etc.). Standard data structures are fine: `collections.deque`, `heapq`, `dict`, `set`.
- `core/` and `solvers/` must not import `pygame` or anything from `gui/`. The GUI depends on core and solvers, never the reverse. This keeps solvers testable and benchmarkable headless.
- Do not add dependencies without the member's approval. If one is approved, add it to `Source/requirements.txt`.
- Do not edit `docs/AI - Project 1.*`.

## Core contract

The core interface (state representation, `successors`, `is_goal`, level JSON format) is owned by Cao. **Read the existing code in `bloxorz/core/` and use it as-is.** If it does not exist yet or lacks what you need, stop and tell the member. Do not invent a parallel representation.

Invariants every implementation must respect, taken from the spec:

- A state is **immutable and hashable**: tuples or frozen dataclasses, no lists or dicts inside.
- A state includes the block placement **and the open/closed status of every bridge**. Two states with the same block placement but different bridge configurations are different states.
- In split mode, the state includes both cube positions and which cube is currently controlled.
- A move is illegal if any occupied cell is outside the board, a void, or a closed bridge, or if the block **stands** on a fragile tile.
- Goal: whole block, standing, on the goal cell. A single cube never wins.
- Successor generation is deterministic. Use the fixed action order **Up, Down, Left, Right**, then switch-cube when in split mode. This keeps experiments reproducible.

Rule decisions the spec leaves open are recorded by Long in the tiles code and docs. Follow those decisions; do not re-decide them.

## Solvers

- All solvers share one entry signature and return the path plus a metrics record: `search_time` (seconds, `time.perf_counter`), `peak_memory` (bytes, `tracemalloc`), `expanded_nodes`, `solution_length` (number of moves). Reuse the shared metrics module rather than measuring ad hoc.
- A node counts as **expanded** when it is popped from the frontier and its successors are generated. Count it the same way in every solver.
- Every solver handles repeated states (visited/closed set keyed by the hashable state).
- DFS uses an explicit stack, not recursion.
- UCS and A\* use the same cost function. A\*'s heuristic must stay **admissible for that cost function**: scale it by the minimum step cost, and account for split-switch teleports, which can move the block far in one action.
- Solvers must not mutate the problem or level objects and must not use global state.

## Levels

- JSON files in `Source/levels/`, named `g<group>_<theme>_<nn>.json`. Groups: `g1_basic`, `g2_fragile`, `g3_switch`, `g4_combined`.
- Every committed level must be solvable. Verify this with BFS before committing.

## Testing

- `python -m pytest tests` must pass before any commit.
- Add tests with every change to `core/` or `solvers/`. Priorities: the orientation transition table (every orientation × direction), each tile/switch rule, and solvers on tiny hand-checked levels. For BFS, assert the solution length is optimal.
- Do not delete or weaken an existing test to make it pass. If a test looks wrong, raise it with the member.

## Git

- Never commit to `main`, never force-push, never rewrite pushed history. Work on a branch named `feat/…`, `fix/…`, `test/…` or `docs/…`.
- Commit message format: `type(scope): summary`, for example `feat(solvers): add BFS solver`. Types: feat, fix, test, docs, refactor, chore. Scopes: core, tiles, gui, solvers, levels, benchmark, docs.
- Stage files explicitly. Never commit `.venv/`, `__pycache__/`, benchmark result dumps or large binaries.
- Commit and push only when the member asks. Show them the diff summary first.
- Open PRs with the template in `.github/pull_request_template.md`.

## Understanding, not just output

The course may hold random oral interviews, and each member must be able to explain their own code. After implementing something non-trivial:

- Give the member a short Vietnamese explanation of how it works and why: state shape, algorithm steps, edge cases.
- Point out anything they should be ready to defend, such as the cost-function choice, heuristic admissibility, or how expanded nodes are counted.

Prefer clear code over clever code.

## AI usage log (required by the report)

The report must include an appendix describing how AI was used and which prompts were used. After each significant task, append an entry to `docs/ai-log/<member>.md` using the format in [docs/ai-log/README.md](docs/ai-log/README.md): date, tool, the member's prompt(s), quoted or faithfully summarized, what was produced, and what the member changed or verified. If you cannot write the file, remind the member to do it.
