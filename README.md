# QUASAR

A small, educational version-control project. This repository currently contains only a single file:

- `main.py` — the Quasar implementation and command-line interface.

This README has been simplified because the repository's current structure only includes `main.py`. The full project (object model, CLI commands, and examples) is implemented inside that file.

Quick start
-----------

Install the dependency:

```bash
python3 -m pip install colorama
```

Run the main script to see usage and available commands:

```bash
python3 main.py --help
```

Common commands (use `--help` for details):

- Initialize a new Quasar repository:

```bash
python3 main.py ready
```

- Stage files or directories:

```bash
python3 main.py save <path1> [<path2> ...]
```

- Create a commit:

```bash
python3 main.py done -m "Commit message" [--author "Name <email>"]
```

- Switch or create branches:

```bash
python3 main.py branch <branch-name> [-b]
```

- List branches or create from current branch:

```bash
python3 main.py vers [<branch-name>]
```

- Show repository status:

```bash
python3 main.py state
```

- Show commit history:

```bash
python3 main.py history
```

Notes
-----

- The project is packaged as a single Python file for ease of exploration. If you plan to expand the repository, consider splitting the implementation into modules and adding tests and documentation.
- If you expected other files or a full example project layout, they are not present in this repository at the moment.

If you'd like, I can also:

- Restore a more detailed README documenting the internal object model, or
- Add a simple example script and basic tests, or
- Split `main.py` into a package layout and update this README with usage examples.
