# QUASAR

### A Git-Inspired Version Control System Built from Scratch

> *"The fastest way to understand anything is to build it from
> scratch."*

**Quasar** is a small, educational version control system written in
Python. It recreates the core ideas behind Git: storing file snapshots,
tracking commits, maintaining branches, and inspecting changes---all
through a custom command-line interface.

The project is designed to make version control easier to understand by
implementing its underlying concepts rather than treating Git as a black
box.

> **Note:** Quasar is an independent learning project inspired by Git.
> It is not a drop-in replacement for Git and does not use Git's
> repository format or command syntax.

------------------------------------------------------------------------

## Features

-   **Repository initialization** --- create a new Quasar repository.
-   **File and directory staging** --- save files or recursively stage a
    directory.
-   **Snapshots and commits** --- record the staged state with a commit
    message and author.
-   **Branch management** --- list branches, create branches, and switch
    between them.
-   **Commit history** --- inspect previous commits, authors,
    timestamps, and messages.
-   **Repository status** --- compare the staging index, latest commit,
    and working directory.
-   **Content-addressed storage** --- identify stored objects using
    SHA-1 hashes.
-   **Compressed objects** --- compress stored resources with Python's
    `zlib` module.
-   **Nested directory support** --- represent directory structures
    using tree objects.

------------------------------------------------------------------------

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

No external Python packages are required by the implementation shown in
this project.

------------------------------------------------------------------------

## Getting Started

### 1. Requirements

-   Python 3
-   A terminal
-   Basic familiarity with command-line tools

Check that Python is installed:

``` bash
python3 --version
```

### 2. Get the project

If you already have the project locally, open a terminal and move into
its directory:

``` bash
cd path/to/quasar
```

If you are cloning the project from a remote repository, use its
repository URL:

``` bash
git clone <repository-url>
cd <repository-directory>
```

Replace the placeholders with the actual URL and directory name.

### 3. Initialize a repository

Run:

``` bash
python3 main.py ready
```

Quasar creates its internal `.quasar` directory, which stores repository
metadata, objects, references, and the staging index.

------------------------------------------------------------------------

## Quasar Commands

Quasar uses its own command names. The table below maps them to their
familiar Git counterparts.

  -----------------------------------------------------------------------
  Git concept / command   Quasar command          Purpose
  ----------------------- ----------------------- -----------------------
  `git init`              `ready`                 Initialize a repository

  `git add`               `save`                  Stage a file or
                                                  directory

  `git commit`            `done`                  Create a commit

  `git switch` /          `branch`                Switch branches; use
  checkout-like operation                         `-b` to create and
                                                  switch

  `git branch`            `vers`                  List branches or create
                                                  a branch

  `git status`            `state`                 Show repository changes

  `git log`               `history`               Display commit history
  -----------------------------------------------------------------------

### Initialize: `ready`

``` bash
python3 main.py ready
```

Creates a new Quasar repository in the current directory. If a `.quasar`
directory already exists, Quasar reports that the repository is already
initialized.

### Stage files: `save`

Stage one file:

``` bash
python3 main.py save main.py
```

Stage several paths:

``` bash
python3 main.py save main.py fibb.c
```

Stage a directory recursively:

``` bash
python3 main.py save "ML Concepts"
```

Quasar reads the selected file contents, creates blob objects, and
records their hashes in the staging index.

**Tip:** Quote paths containing spaces, such as `"ML Concepts"`.

### Create a commit: `done`

``` bash
python3 main.py done -m "Add initial ML examples"
```

Specify an author:

``` bash
python3 main.py done -m "Add initial ML examples" --author "Your Name <you@example.com>"
```

A commit records a tree snapshot, its parent commit (when present),
author and committer metadata, a timestamp, and a message. After a
successful commit, Quasar clears the staging index.

### Branches: `vers`

List branches:

``` bash
python3 main.py vers
```

Create a branch from the current branch's commit:

``` bash
python3 main.py vers experiment
```

The current branch is marked with `*`.

### Switch branches: `branch`

Switch to an existing branch:

``` bash
python3 main.py branch experiment
```

Create a new branch and switch to it:

``` bash
python3 main.py branch -b experiment
```

Quasar uses branch references to identify the commit associated with
each branch.

### Inspect changes: `state`

``` bash
python3 main.py state
```

The status command compares the latest commit, staging index, and
working directory. Depending on the current state of the repository, it
can report staged changes, unstaged modifications, untracked files, and
deletions.

### View commit history: `history`

Show the latest commits (up to 10 by default):

``` bash
python3 main.py history
```

Limit the output:

``` bash
python3 main.py history -n 5
```

The history includes commit hashes, authors, timestamps, and commit
messages.

------------------------------------------------------------------------

## 🔁 Example Workflow

Here is a typical end-to-end workflow:

``` bash
# Initialize the repository
python3 main.py ready

# Stage files or a directory
python3 main.py save main.py
python3 main.py save "ML Concepts"

# Record a snapshot
python3 main.py done -m "Add initial project files"

# Inspect the repository
python3 main.py state

# Create and switch to a feature branch
python3 main.py branch -b feature-work

# View available branches and commit history
python3 main.py vers
python3 main.py history
```

Run commands from the project directory that should be managed by
Quasar. Before experimenting with branch switching, commit or back up
any important working changes.

------------------------------------------------------------------------

## 🧠 How Quasar Works

Quasar follows a simplified, Git-inspired object model.

### 1. Blob objects

A **blob** stores the contents of a file. Quasar hashes the resource
type, content length, and content using SHA-1 to obtain an object
identifier.

Conceptually, the hash input is:

``` text
blob <content-size>\0<file-content>
```

The same content produces the same blob hash when the resource type and
content are identical.

### 2. Tree objects

A **tree** describes a directory snapshot. Its entries contain a file or
directory mode, a name, and an object hash.

-   File entries point to blob objects.
-   Directory entries point to other tree objects.
-   Nested trees represent nested directories.

This allows Quasar to reconstruct a directory hierarchy from stored
objects.

### 3. Commit objects

A **commit** points to a root tree and records metadata such as:

-   The tree hash
-   Parent commit hash or hashes
-   Author
-   Committer
-   Timestamp
-   Commit message

The parent link connects commits into a history.

### 4. The staging index

The staging index maps repository-relative file paths to blob hashes.
The `save` command updates this index; `done` builds a tree from the
staged entries and records a commit.

### 5. Branch references and `HEAD`

Branch references store commit hashes. The `HEAD` file identifies the
currently selected branch, allowing new commits to advance that branch's
reference.

### 6. Object storage

Quasar stores resources under `.quasar/resources`, organized by hash
prefix. Serialized resources are compressed using `zlib`, while the
index is stored as JSON.

------------------------------------------------------------------------

## 📁 Repository Layout

A Quasar repository has an internal structure similar to this:

``` text
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

The exact branch names and stored resource files depend on how the
repository is used.

  -----------------------------------------------------------------------
  Path                                Responsibility
  ----------------------------------- -----------------------------------
  `.quasar/HEAD`                      Identifies the currently selected
                                      branch

  `.quasar/index`                     Stores staged file paths and blob
                                      hashes

  `.quasar/features/heads/`           Stores branch references

  `.quasar/resources/`                Stores compressed blob, tree, and
                                      commit resources
  -----------------------------------------------------------------------

**Keep `.quasar` intact.** It contains the metadata and objects needed
to understand the repository's history.

------------------------------------------------------------------------

## 🎯 Project Goals

Quasar is intended to explore the fundamental ideas behind version
control:

-   How file contents can be stored as immutable objects.
-   How hashes identify content.
-   How trees represent directory snapshots.
-   How commits form a history.
-   How branches point to commits.
-   How a staging area separates intended changes from the working
    directory.
-   How a status command compares multiple representations of the same
    project.

Building these pieces from scratch is a practical way to connect data
structures, filesystem operations, hashing, and command-line
programming.

------------------------------------------------------------------------

## ⚠️ Scope and Limitations

Quasar is a learning-oriented implementation. It should not be assumed
to provide every feature or safety guarantee offered by Git.

The implementation currently focuses on basic local version-control
operations. Features such as remote repositories, network push/pull,
merging, conflict resolution, and Git-format compatibility are not part
of the documented command set.

As with any custom version-control system, test branch switching and
deletion carefully, and keep backups of important files while
developing.

------------------------------------------------------------------------

## Possible Future Improvements

Potential extensions include:

-   Safer handling of staged and unstaged deletions.
-   More comprehensive tests for nested directories and branch
    switching.
-   Ignore rules for generated files and repository metadata.
-   Merge support and conflict detection.
-   Tags and detached-HEAD support.
-   Remote repositories and synchronization.
-   Improved error messages and command help.
-   Automated tests for object hashing, tree serialization, and commit
    history.

These are ideas for future development, not claims about features
already implemented.

------------------------------------------------------------------------

##  Contributing

Suggestions, bug reports, and improvements are welcome.

A useful contribution could be a test case, a clearer error message, an
improvement to the object model, or documentation explaining one of the
version-control concepts.

Before contributing, reproduce the issue, describe the expected
behavior, and include the command or small example that demonstrates it.

------------------------------------------------------------------------

## License

No license is specified in this README. Add a license file and update
this section if you intend to publish or distribute the project.

------------------------------------------------------------------------

**Quasar: understand version control by building it, one object at a
time.** 
