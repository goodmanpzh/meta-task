### Category: Games, Puzzles, and Strategy Programming

Tasks involving game AI, strategy programming, puzzle solving, game-tool building, and interactive fiction — all operating in a headless terminal environment via CLI tools, file I/O, and programmatic analysis (no GUI, no display server).

**The examples below are for inspiration only. Be creative and design your own unique task!**

**Task Pattern Ideas**:

*Board Game Analysis & Engine Tasks:*
- Solve chess puzzles by programmatically parsing board images (pixel analysis with Pillow/numpy) and finding best moves via CLI engines (Stockfish, GNU Chess)
- Analyze Go life-and-death problems using GnuGo or KataGo in CLI/GTP mode
- Solve endgame positions from tablebase lookups or engine analysis
- Implement a move validator or legal-move generator for a specific board game (chess, Go, Othello, Hex)
- Evaluate bridge hands using double-dummy solvers (libdds CLI)
- Parse game notation files (PGN, SGF, PDN) and extract statistics or specific positions

*Combat Programming & Bot Battles:*
- Write CoreWars warriors in Redcode to beat specified opponents at target win rates using pMARS
- Implement battle bots for programming games (BF Joust, CROBOTS, Robot Battle)
- Write a strategy program that competes against provided opponent bots via stdin/stdout protocol
- Design a multi-strategy warrior that adapts to different opponent types (bombers, replicators, scanners, vampires)

*Constraint Satisfaction & Logic Puzzles:*
- Solve Sudoku variants (standard, diagonal, killer, samurai) from text-format input
- Solve Nonogram/Picross puzzles given row and column clue files
- Solve logic grid puzzles (Einstein's riddle style) from structured clue files
- Encode puzzle problems as SAT instances and solve with a SAT solver (minisat, cadical)
- Solve Minesweeper boards deterministically from partial reveal state
- Generate valid puzzle instances with unique solutions meeting specific difficulty criteria

*Text Adventures & Interactive Fiction:*
- Play through a Z-machine game (Frotz/Bocfel interpreter) and achieve a target score or find a specific item
- Write a walkthrough script that solves an Infocom-style text adventure
- Extract a secret or flag hidden within an interactive fiction game by automated exploration
- Reverse engineer game mechanics from a provided Z-machine story file

*Game Tool Building & Compilation:*
- Build game simulators or engines from source without GUI dependencies (X11-free builds)
- Cross-compile game software for non-native architectures (MIPS, ARM)
- Patch and build legacy game tools from Debian/upstream source packages
- Port a game engine from one platform or language to another

*Cellular Automata & Simulation:*
- Engineer Game of Life patterns that produce specific behaviors (oscillators, spaceships, guns, breeders)
- Design Langton's Ant variants or Turmite programs that draw specific patterns
- Implement cellular automaton rules and verify emergent properties from initial conditions
- Write programs for other simulation systems (Wireworld, elementary automata, Lenia)

*Procedural Generation:*
- Generate solvable mazes meeting specific constraints (size, path length, branching factor)
- Create balanced game levels or maps from specification files
- Generate valid Sudoku puzzles with unique solutions at a target difficulty
- Design roguelike dungeon layouts satisfying connectivity and gameplay constraints

*Game Theory & Strategy:*
- Implement minimax/alpha-beta search for perfect-information games
- Solve combinatorial game theory problems (compute Sprague-Grundy values, nim-values)
- Find Nash equilibria or optimal mixed strategies for specified matrix games
- Implement Monte Carlo Tree Search (MCTS) for a provided game environment
- Solve multi-agent coordination problems with game-theoretic formulations

**Skills & Tools** (tag suggestions for your task):
- Core: `gaming`, `strategy`, `puzzle-solving`, `game-ai`, `competitive-programming`
- Board games: `chess`, `go`, `othello`, `hex`, `bridge`, `python-chess`, `stockfish`, `gnugo`
- Combat programming: `corewars`, `redcode`, `pmars`, `bf-joust`, `crobots`
- Puzzles: `sudoku`, `nonogram`, `sat-solver`, `constraint-satisfaction`, `logic-puzzle`
- Interactive fiction: `frotz`, `z-machine`, `text-adventure`, `inform`
- Simulation: `cellular-automata`, `game-of-life`, `procedural-generation`
- Theory: `minimax`, `mcts`, `game-theory`, `sprague-grundy`, `nash-equilibrium`
- Image analysis: `pillow`, `numpy`, `image-processing` (for parsing board images programmatically)
- Build: `compilation`, `build-tools`, `cross-compilation`, `make`

**Possible Input Data** (be creative with environment files!):
- Board images (PNG/PPM chess/Go board positions for programmatic pixel analysis)
- Game notation files (PGN for chess, SGF for Go, PDN for checkers/draughts)
- FEN/GTP position strings (text-based board state representations)
- Opponent programs (CoreWars warriors `.red`, bot scripts in various languages)
- Puzzle input files (Sudoku grids as text, Nonogram clues as CSV, SAT formulas as CNF/DIMACS)
- Z-machine story files (`.z3`, `.z5`, `.z8` for interactive fiction)
- Game simulator source code (C/C++ source tarballs requiring headless compilation)
- Cellular automaton initial states (RLE files for Game of Life, plain text grids)
- Game rule specifications (JSON/TOML defining custom game rules, board sizes, win conditions)
- Strategy tournament configurations (opponent lists, match parameters, scoring rules)
- Map/level specification files (JSON/text describing terrain, constraints, objectives)
- Game tree data (position databases, opening books, endgame tablebases)

**Verification Approaches**:
- Check output moves/solutions match known correct answers (exact match or set equality)
- Run competitive matches and verify win rate exceeds threshold (e.g., 75% over 100 rounds)
- Verify puzzle solutions satisfy all constraints (row/column uniqueness, clue compliance)
- Check compiled binaries work correctly (run test matches, verify no GUI/X11 linkage)
- Validate generated content (puzzles have unique solutions, mazes are solvable, levels are connected)
- Verify game scores or achievements in text adventure transcripts
- Check cellular automaton patterns reach expected states after N generations
- Integrity checks on opponent/input files (SHA256 hash verification, no tampering)
- Performance thresholds (move computation within time limits, search depth requirements)
- Statistical validation over multiple random runs (average win rate, solve rate)

**Remember**: All game tasks must work in a headless Docker container with no display server (no X11, no Wayland). Interactions with games must be through CLI tools, file I/O, or stdin/stdout protocols. When tasks involve images (e.g., board positions), the agent must use programmatic image analysis (Pillow, numpy, OpenCV) rather than visual inspection. Game simulators and engines should be pre-installed in the Dockerfile or buildable from source. Verification should be deterministic — use fixed seeds for randomized elements, run enough trials for statistical stability, and prefer exact output matching where possible.
