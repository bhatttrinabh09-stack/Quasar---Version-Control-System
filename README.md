# QUASAR

### A Git-Inspired Version Control System Built from Scratch

> *“The fastest way to understand anything is to build it from scratch.”*

**Quasar** is a small, educational version control system written in Python. It recreates core ideas behind Git: storing file snapshots, tracking commits, maintaining branches, and inspecting changes through a custom command-line interface.

The goal is to understand how version control works internally by building its core components instead of treating Git as a black box.

> **Note:** Quasar is an independent learning project inspired by Git. It is not a drop-in replacement for Git and does not use Git’s repository format or command syntax.

---

## Features

- **Repository initialization:** Create a new Quasar repository.
- **File and directory staging:** Save individual files or recursively stage a directory.
- **Snapshots and commits:** Record staged content with a commit message and author.
- **Branch management:** List, create, and switch between branches.
- **Commit history:** Inspect commit hashes, authors, timestamps, and messages.
- **Repository status:** Compare the staging index, latest commit, and working directory.
- **Content-addressed storage:** Identify stored objects using SHA-1 hashes.
- **Compressed objects:** Compress stored resources using Python’s `zlib` module.
- **Nested directories:** Represent directory structures with tree objects.

---

## Built With

  Technology   Purpose
  ------------ ------------------------------------------------
  Python       Core implementation and command-line interface
  `argparse`   Parsing commands and options
  `pathlib`    Filesystem and path handling
  `hashlib`    SHA-1 object hashes
  `zlib`       Compressing stored objects
  `json`       Persisting the staging index
  `time`       Commit timestamps
  `colorama`   Colored terminal output

Install the external dependency with `python3 -m pip install colorama`.

---

## Getting Started

### Requirements

-   Python 3
-   The `colorama` Python package
-   A terminal
-   Basic familiarity with command-line tools

Check your Python installation:

```bash
python3 --version
python3 -m pip install colorama
```

### Get the project

If the project is already on your computer, navigate to its directory:

```bash
cd path/to/quasar
```

If you are cloning it from a remote repository, use the repository URL:

```bash
git clone <repository-url>
cd <repository-directory>
```

Replace the placeholders with the actual repository URL and directory name.

### Initialize a repository

```bash
python3 main.py ready
```

This creates the internal `.quasar` directory, which stores repository metadata, objects, branch references, and the staging index.

---

## Command Reference

Quasar uses its own command names. The table below maps them to familiar Git concepts.

| Git command / concept | Quasar command | Purpose |
|---|---|---|
| `git init` | `ready` | Initialize a repository |
| `git add` | `save` | Stage a file or directory |
| `git commit` | `done` | Create a commit |
| `git checkout` | `branch` | Switch branches; use `-b` to create and switch |
| `git branch` | `vers` | List branches or create a branch |
| `git status` | `state` | Show repository changes |
| `git log` | `history` | Display commit history |

### `ready` — Initialize a repository

```bash
python3 main.py ready
```

Creates a new Quasar repository in the current directory. If `.quasar` already exists, Quasar reports that the repository is already initialized.

### `save` — Stage files and directories

Stage one file:

```bash
python3 main.py save main.py
```

Stage multiple files:

```bash
python3 main.py save main.py fibb.c
```

Stage a directory recursively:

```bash
python3 main.py save "ML Concepts"
```

Quasar reads the selected files, creates blob objects, and records their hashes in the staging index.

**Tip:** Put quotation marks around paths that contain spaces, such as `"ML Concepts"`.

### `done` — Create a commit

```bash
python3 main.py done -m "Add initial ML examples"
```

Specify an author:

```bash
python3 main.py done -m "Add initial ML examples" --author "Your Name <you@example.com>"
```

A commit records a tree snapshot, its parent commit (when present),
author and committer metadata, a timestamp, and a message. After a
successful commit, Quasar keeps the index aligned with the new snapshot.
When you save a file later, the index starts with the current commit's
files, so saving one file does not mark the other committed files as
deleted.

### `vers` — List or create branches

List branches:

```bash
python3 main.py vers
```

Create a branch from the current branch’s commit:

```bash
python3 main.py vers experiment
```

The current branch is marked with `*`.

### `branch` — Switch branches

Switch to an existing branch:

```bash
python3 main.py branch experiment
```

Create a branch and switch to it:

```bash
python3 main.py branch -b experiment
```

Quasar uses branch references to identify the commit associated with each branch.

### `state` — Inspect repository changes

```bash
python3 main.py state
```

The status command compares Quasar's latest commit, staging index, and
working directory. It can report staged changes, unstaged modifications,
untracked files, and working-tree deletions. Quasar maintains its own
history in `.quasar`; `state` does not show the status of a separate Git
repository in `.git`. To start tracking a file with Quasar, stage it with
`save`.

### `history` — View commit history

Show the latest commits (10 by default):

```bash
python3 main.py history
```

Limit the output:

```bash
python3 main.py history -n 5
```

The history includes commit hashes, authors, timestamps, and messages.

---

## Example Workflow

A typical workflow looks like this:

```bash
# Initialize the repository
python3 main.py ready

# Stage files
python3 main.py save main.py
python3 main.py save "ML Concepts"

# Record a snapshot
python3 main.py done -m "Add initial project files"

# Inspect the repository
python3 main.py state

# Create and switch to a feature branch
python3 main.py branch -b feature-work

# List branches and inspect history
python3 main.py vers
python3 main.py history
```

Run these commands from the directory you want Quasar to manage. Before experimenting with branch switching, commit or back up any important working changes.

---

## How Quasar Works

Quasar follows a simplified, Git-inspired object model.

### 1. Blob objects

A **blob** stores a file’s contents. Quasar hashes the resource type, content length, and content using SHA-1 to produce an object identifier.

Conceptually, the hash input is:

```text
blob <content-size>\0<file-content>
```

Identical content produces the same blob hash when the resource type is also identical.

### 2. Tree objects

A **tree** describes a directory snapshot. Each entry contains a file or directory mode, a name, and an object hash.

- File entries point to blob objects.
- Directory entries point to other tree objects.
- Nested trees represent nested directories.

This structure allows Quasar to reconstruct a directory hierarchy from stored objects.

### 3. Commit objects

A **commit** points to a root tree and records metadata such as:

- Tree hash
- Parent commit hash or hashes
- Author
- Committer
- Timestamp
- Commit message

Parent links connect commits into a history.

### 4. The staging index

The staging index maps repository-relative file paths to blob hashes.
It represents the snapshot being prepared for the next commit and begins
with the current commit's files. The `save` command adds or updates paths
in this snapshot; `done` builds a tree from it and records a commit. The
index remains aligned with that snapshot after a successful commit.

### 5. Branch references and `HEAD`

Branch references store commit hashes. The `HEAD` file identifies the currently selected branch, allowing new commits to advance that branch’s reference.

### 6. Object storage

Quasar stores resources under `.quasar/resources`, organized by hash prefix. Serialized resources are compressed with `zlib`, while the staging index is stored as JSON.

---

## Repository Layout

A Quasar repository has an internal structure similar to this once you run the 'python3 main.py' and other quasar commands:

```text
project/
├── .quasar/
│   ├── HEAD
│   ├── index
│   ├── features/
│   │   └── heads/
│   │       └── main_repository
│   └── resources/
│       └── <hash-prefix>/
│           └── <remaining-hash>
├── main.py
├── README.md
└── your-project-files...
```

The exact branch names and stored resource files depend on how the repository is used.

| Path | Responsibility |
|---|---|
| `.quasar/HEAD` | Identifies the currently selected branch |
| `.quasar/index` | Stores staged file paths and blob hashes |
| `.quasar/features/heads/` | Stores branch references |
| `.quasar/resources/` | Stores compressed blob, tree, and commit resources |

**Keep `.quasar` intact.** It contains the metadata and objects needed to understand the repository’s history.

---

## Project Goals

Quasar explores the fundamental ideas behind version control:

- How file contents can be stored as immutable objects.
- How hashes identify content.
- How trees represent directory snapshots.
- How commits form a history.
- How branches point to commits.
- How a staging area separates intended changes from the working directory.
- How a status command compares different representations of a project.

Building these components from scratch connects data structures, filesystem operations, hashing, and command-line programming.

---

## Scope and Limitations

Quasar is a learning-oriented implementation. It should not be assumed to provide every feature or safety guarantee offered by Git.

The project focuses on basic local version-control operations. Remote repositories, network push/pull, merging, conflict resolution, and Git-format compatibility are not part of the command set documented here.

As with any custom version-control system, test branch switching and deletion carefully, and keep backups of important files while developing.

---

## Possible Future Improvements

Potential extensions include:

- More robust handling of staged and unstaged deletions.
- More comprehensive tests for nested directories and branch switching.
- Ignore rules for generated files and repository metadata.
- Merge support and conflict detection.
- Tags and detached-`HEAD` support.
- Remote repositories and synchronization.
- Improved error messages and command help.
- Automated tests for object hashing, tree serialization, and commit history.

These are ideas for future development, not claims about features already implemented.

---

## Contributing

Suggestions, bug reports, and improvements are welcome.

Useful contributions could include a test case, a clearer error message, an improvement to the object model, or documentation explaining a version-control concept.

Before reporting an issue, describe the expected behavior and include the command or small example that reproduces it.

---

## License

No license is specified in this README. Add a license file and update this section if you intend to publish or distribute the project.

[Refrence Tutorial: "I Built My Own Git From Scratch (And Here's How You Can) | Git Tutorial" by Rivaan Ranawat]("https://youtu.be/g2cfjDENSyw?si=p54mYxdfs65CCyGe")

---

**Quasar: understand version control by building it, one object at a time.**
