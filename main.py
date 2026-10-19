import argparse, json, hashlib, zlib
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import time
from colorama import Fore


def print_success(message: str) -> None:
    print(Fore.GREEN + message + Fore.RESET)


def print_error(message: str) -> None:
    print(Fore.RED + message + Fore.RESET)


def print_notice(message: str) -> None:
    print(Fore.YELLOW + message + Fore.RESET)


class QuasarResource:
    def __init__(self, resource_type: str, content: bytes):
        self.type = resource_type
        self.content = content

    def hash(self) -> str:
        #(<type> <size> \0 <content>)
        header = f"{self.type} {len(self.content)}\0".encode()
        return hashlib.sha1(header + self.content).hexdigest()

    def serialize(self) -> bytes:
        header = f"{self.type} {len(self.content)}\0".encode()
        return zlib.compress(header + self.content)

    @classmethod
    def deserialize(cls, data: bytes) -> "QuasarResource":
        decompressed = zlib.decompress(data)
        null_index = decompressed.find(b"\0")
        if null_index < 0:
            raise ValueError("Invalid resource header: missing null separator")
        header = decompressed[:null_index].decode()
        content = decompressed[null_index + 1:]
        try:
            resource_type, size_text = header.rsplit(" ", 1)
            size = int(size_text)
        except (ValueError, TypeError) as exc:
            raise ValueError("Invalid resource header") from exc
        if size < 0 or size != len(content):
            raise ValueError("Resource size does not match its content")

        return cls(resource_type, content)


class BLOB(QuasarResource):
    def __init__(self, content: bytes):
        super().__init__('blob', content)

    def get_content(self) -> bytes:
        return self.content

class Trees(QuasarResource):
    def __init__(self, entries: Optional[List[Tuple[str, str, str]]] = None):
        self.entries = entries or []
        content = self.serialize_entries()
        super().__init__("tree", content)

    def serialize_entries(self) -> bytes:
        #<mode> <name>\0<hash>
        content = b""
        for mode, name, obj_hash in sorted(self.entries):
            content += f"{mode} {name}\0".encode()
            content += bytes.fromhex(obj_hash)

        return content

    def add_entries(self, mode: str, name: str, obj_hash: str):
        self.entries.append((mode, name, obj_hash))
        self.content = self.serialize_entries()

    @classmethod
    def from_content(cls, content: bytes) -> "Trees":
        tree = cls()
        i = 0
        while i < len(content):
            null_idx = content.find(b"\0", i)
            if null_idx == -1 or null_idx + 21 > len(content):
                raise ValueError("Invalid tree entry")

            try:
                mode_name = content[i:null_idx].decode()
                mode, name = mode_name.split(" ", 1)
            except (UnicodeDecodeError, ValueError) as exc:
                raise ValueError("Invalid tree entry header") from exc
            obj_hash = content[null_idx + 1:null_idx + 21].hex()
            tree.entries.append((mode, name, obj_hash))

            i = null_idx + 21

        return tree
    
class Commit(QuasarResource):
    def __init__(self, tree_hash: str, parent_hashes: List[str], author: str, committer: str, msg: str, timestamp: int = None):
        self.tree_hash = tree_hash
        self.parent_hashes = parent_hashes
        self.author = author
        self.committer = committer
        self.msg = msg
        self.timestamp = int(time.time()) if timestamp is None else timestamp

        content = self.serialize_commit()
        super().__init__("commit", content)

    def serialize_commit(self):
        lines = [f"Tree: {self.tree_hash}"]
        for parent in self.parent_hashes:
            lines.append(f"Parent: {parent}")
        lines.append(f"Author: {self.author} {self.timestamp} +0000")
        lines.append(f"Committer: {self.committer} {self.timestamp} +0000")
        lines.append("")
        lines.append(self.msg)

        #Appended causes O(n) but if we had to concatenate in string it would be o(n²)
        return "\n".join(lines).encode()

    @classmethod

    def deserialize_commit(cls, content: bytes) -> "Commit":
        lines = content.decode().split("\n")

        tree_hash = None
        parent_hashes = []
        author = None
        committer = None
        timestamp = None
        message_start = 0

        for i, line in enumerate(lines):
            if line.startswith("Tree: "):
                tree_hash = line[6:]
            elif line.startswith("Parent: "):
                parent_hashes.append(line[8:])
            elif line.startswith("Author: "):
                author_parts = line[8:].rsplit(" ", 2)
                if len(author_parts) != 3:
                    raise ValueError(f"Invalid author metadata: {line!r}")
                author = author_parts[0]
                timestamp = int(author_parts[1])
            elif line.startswith("Committer: "):
                committer_parts = line[11:].rsplit(" ", 2)
                if len(committer_parts) != 3:
                    raise ValueError(f"Invalid committer metadata: {line!r}")
                committer = committer_parts[0]
            elif line == "":
                message_start = i + 1
                break

        if tree_hash is None:
            raise ValueError("Commit is missing tree metadata")
        if author is None or committer is None or timestamp is None:
            raise ValueError("Commit is missing author or committer metadata")
        message = "\n".join(lines[message_start:])
        return cls(
            tree_hash=tree_hash,
            parent_hashes=parent_hashes,
            author=author,
            committer=committer,
            msg=message,
            timestamp=timestamp,
        )

class Repository:
    def __init__(self, path="."):
        self.path = Path(path).resolve()        #copy of git init
        self.quasar_dir = self.path / ".quasar"

        # .git/object
        self.resources_dir = self.quasar_dir / "resources"

        # .git/refs
        self.features_dir = self.quasar_dir / "features"
        self.heads_dir = self.features_dir / "heads"

        # HEAD File
        self.head_file = self.quasar_dir / "HEAD"

        # .git/index
        self.index_file = self.quasar_dir / "index"

    @staticmethod
    def _is_internal_path(path: str) -> bool:
        """Keep VCS metadata out of the files managed by this repository."""
        parts = Path(path).parts
        return bool(parts and parts[0] in {".git", ".quasar"})

    def ready(self) -> bool:

        if self.quasar_dir.exists():
            return False
        
        self.heads_dir.mkdir(parents=True)

        #Creating HEAD file pointing to an initial branch
        self.head_file.write_text("ref: refs/heads/main_repository\n")
        
        self.save_index({})

        print_success(
            f"An empty Quasar Repository is ready in "
            f"{Fore.WHITE}{self.quasar_dir}{Fore.GREEN}"
        )
        return True

    def store_resource(self, resource: QuasarResource):
        resource_hash = resource.hash()

        resource_dir = self.resources_dir / resource_hash[:2]
        resource_file = resource_dir / resource_hash[2:]

        if not resource_file.exists():
            resource_dir.mkdir(parents=True, exist_ok=True)
            resource_file.write_bytes(resource.serialize())

        return resource_hash

    def load_index(self) -> Dict[str, str]:
        if not self.index_file.exists():
            return {}
        try:
            index = json.loads(self.index_file.read_text())
        except (json.JSONDecodeError, OSError) as e:
            raise ValueError(f"Failed to load index: {e}") from e
        if not isinstance(index, dict) or any(
            not isinstance(path, str) or not isinstance(blob_hash, str)
            for path, blob_hash in index.items()
        ):
            raise ValueError("Index must map file paths to resource hashes")
        return {
            path: blob_hash
            for path, blob_hash in index.items()
            if not self._is_internal_path(path)
        }

    def save_index(self, index: Dict[str, str]):
        self.index_file.write_text(json.dumps(index, indent=2))

    def get_committed_index(self) -> Dict[str, str]:
        """Return the current branch snapshot as a path-to-blob mapping."""
        commit_hash = self.get_branch_commit(self.get_current_branch())
        if not commit_hash:
            return {}
        commit_obj = self.load_resource(commit_hash)
        if commit_obj.type != "commit":
            raise ValueError("Branch reference does not point to a commit")
        commit = Commit.deserialize_commit(commit_obj.content)
        return self.build_index_from_tree(commit.tree_hash)

    def get_staging_index(self) -> Dict[str, str]:
        """Load the staged snapshot, including files from the current commit.

        Older versions cleared the index after a commit. Merge the current
        snapshot back in so staging one new file cannot stage old files for
        deletion accidentally.
        """
        index = self.get_committed_index()
        index.update(self.load_index())
        return index

    def save_file(self, path: str):
        if self._is_internal_path(path):
            raise ValueError(f"Cannot save repository metadata: {path}")
        full_path = (self.path / path).resolve()
        if not full_path.is_relative_to(self.path):
            raise ValueError(f"Path {path!r} is outside the repository")
        if not full_path.exists():
            raise FileNotFoundError(f"Path {path} not found!")

        #read file content
        content = full_path.read_bytes()
        #create BLOB {binary large object} from content
        blob = BLOB(content)
        '''
        4 types of objects in .git/object:
            1) BLOB: Binary Large Object
            2) commit
            3) trees
            4) tags
        '''
        #store the blob object in .git/object
        blob_hash = self.store_resource(blob)
        #update index to include file
        index = self.get_staging_index()
        index[path] = blob_hash

        self.save_index(index)

        print_success(f"Saved the {Fore.WHITE}{path}{Fore.GREEN}")

    def save_dir(self, path: str):
        full_path = (self.path / path).resolve()
        if not full_path.is_relative_to(self.path):
            raise ValueError(f"Path {path!r} is outside the repository")

        if not full_path.exists():
            raise FileNotFoundError(f"Directory {path} not found!")
        if not full_path.is_dir():
            raise ValueError(f"{path} is not a directory")

        index = self.get_staging_index()
        file_cnt = 0

        for file in full_path.rglob("*"):
            if not file.is_file():
                continue
            relative_path = file.relative_to(self.path)
            if self._is_internal_path(str(relative_path)):
                continue

            relative_path = str(relative_path)
            content = file.read_bytes()
            blob = BLOB(content)
            blob_hash = self.store_resource(blob)
            index[relative_path] = blob_hash
            file_cnt += 1

        self.save_index(index)
        if file_cnt:
            print_success(
                f"Added {file_cnt} files from directory "
                f"{Fore.WHITE}{path}{Fore.GREEN}"
            )
        else:
            print_notice(
                f"Directory {Fore.WHITE}{path}{Fore.YELLOW} contains no files"
            )

    def save_path(self, path: str) -> None:
        full_path = self.path / path
        if not full_path.exists():
            raise FileNotFoundError(f"Path {path} not found!")
        if full_path.is_file():
            self.save_file(path)
        elif full_path.is_dir():
            self.save_dir(path)
        else:
            raise ValueError(f"{path} is neither a file nor a directory.")

    def load_resource(self, res_hash: str) -> QuasarResource:
        if len(res_hash) != 40 or any(c not in "0123456789abcdef" for c in res_hash):
            raise ValueError(f"Invalid resource hash: {res_hash!r}")
        res_dir = self.resources_dir / res_hash[:2]
        res_file = res_dir / res_hash[2:]

        if not res_file.exists():
            raise FileNotFoundError(f"Resource {res_hash} not found")

        return QuasarResource.deserialize(res_file.read_bytes())

    def create_tree_from_index(self):
        index = self.load_index()
        index = {
            path: blob_hash
            for path, blob_hash in index.items()
            if not self._is_internal_path(path)
        }
        if not index:
            tree = Trees()
            return self.store_resource(tree)

        dirs = {}
        files = {}

        for file_path, blob_hash in index.items():
            parts = file_path.split("/")

            if len(parts) == 1:
                #root folder
                files[parts[0]] = blob_hash
            else:
                dir_name = parts[0]
                if dir_name not in dirs:
                    dirs[dir_name] = {}

                current = dirs[dir_name]
                for part in parts[1:-1]:
                    if part not in current:
                        current[part] = {}

                    current = current[part]

                current[parts[-1]] = blob_hash

        def create_recursive_tree(entries_dict: Dict):
            tree = Trees()

            for name, blob_hash in entries_dict.items():
                if isinstance(blob_hash, str):
                    tree.add_entries("10064", name, blob_hash) #100644: Regular, non-executable file

                if isinstance(blob_hash, dict):
                    subtree_hash = create_recursive_tree(blob_hash)
                    tree.add_entries("40000", name, subtree_hash) #40000: Directory, represented by another tree

            return self.store_resource(tree)

            
        root_entries = {**files}        #kwargs :)
        for dir_name, dir_content in dirs.items():
            root_entries[dir_name] = dir_content

        return create_recursive_tree(root_entries)

    def get_current_branch(self) -> str:
        if not self.head_file.exists():
            return "main_repository"
        head_content = self.head_file.read_text().strip()
        if head_content.startswith("ref: refs/heads/"):
            return head_content[16:]

        return "HEAD"

    def get_branch_commit(self, current_branch: str):
        branch_file = self._branch_file(current_branch)
        if branch_file.exists():
            return branch_file.read_text().strip()

        return None

    def set_branch_commit(self, current_branch: str, commit_hash: str):
        branch_file = self._branch_file(current_branch)
        branch_file.parent.mkdir(parents=True, exist_ok=True)
        branch_file.write_text(commit_hash + "\n")

    def _branch_file(self, branch: str) -> Path:
        """Return a safe ref path for a branch name."""
        branch_path = Path(branch)
        if (not branch or branch_path.is_absolute()
                or any(part in ("", ".", "..") for part in branch.split("/"))
                or "\\" in branch or branch.startswith("-") or branch.endswith(".lock")):
            raise ValueError(f"Invalid branch name: {branch!r}")
        target = (self.heads_dir / branch_path).resolve()
        if not target.is_relative_to(self.heads_dir.resolve()):
            raise ValueError(f"Invalid branch name: {branch!r}")
        return target

    def done(self, message:str, author: str = "Quasar User <add_email_of_author@quasar.com>"):
        #create a tree object
        index = self.load_index()
        if not index:
            print_notice("Nothing to commit: index is empty")
            return None

        tree_hash = self.create_tree_from_index()

        current_branch = self.get_current_branch()
        parent_commit = self.get_branch_commit(current_branch)
        parent_hashes = [parent_commit] if parent_commit else []

        if parent_commit:
            parent_resource = self.load_resource(parent_commit)
            if parent_resource.type != "commit":
                raise ValueError("Branch reference does not point to a commit")
            parent_data = Commit.deserialize_commit(parent_resource.content)
            if tree_hash == parent_data.tree_hash:
                print_notice("Nothing to commit: no changes detected")
                return None
        

        commit = Commit(
            tree_hash=tree_hash,
            parent_hashes=parent_hashes,
            author=author,
            committer=author,
            msg=message,
        )

        commit_hash = self.store_resource(commit)
        self.set_branch_commit(current_branch, commit_hash)
        # Keep the index aligned with the committed snapshot. Clearing it
        # makes every file in the new commit look like a staged deletion.
        self.save_index(index)
        print_success(f"Created commit {commit_hash} on branch {current_branch}")
        return commit_hash

    def get_files_from_tree_rec(self, tree_hash: str, prefix: str=""):
        files = set()

        try: 
            tree_obj = self.load_resource(tree_hash)
            tree = Trees.from_content(tree_obj.content)
            for mode, name, obj_hash in tree.entries:
                full_name = f"{prefix}{name}" if prefix else name
                if mode.startswith("100"):
                    files.add(full_name)
                elif mode.startswith("400"):
                    subtree_files = self.get_files_from_tree_rec(obj_hash, f"{full_name}/")
                    files.update(subtree_files)
        except Exception as e:
            print_notice(f"Warning: Could not read the tree {tree_hash}: {e}")

        return files

    def branch(self, mbranch: str, create_branch: bool):
        branch_file = self._branch_file(mbranch)
        prev_branch = self.get_current_branch()
        prev_commit_hash = self.get_branch_commit(prev_branch)
        files_to_clr = set()

        if prev_commit_hash:
            prev_commit_obj = self.load_resource(prev_commit_hash)
            if prev_commit_obj.type != "commit":
                raise ValueError("Branch reference does not point to a commit")
            prev_commit = Commit.deserialize_commit(prev_commit_obj.content)
            if prev_commit.tree_hash:
                files_to_clr = self.get_files_from_tree_rec(
                    prev_commit.tree_hash
                )
                files_to_clr = {
                    path for path in files_to_clr
                    if not self._is_internal_path(path)
                }
        if create_branch:
            if branch_file.exists():
                print_error(f"Branch '{mbranch}' already exists.")
                return
            if not prev_commit_hash:
                print_error("No commits yet, cannot create a new branch.")
                return
        elif not branch_file.exists():
            print_error(f"Branch '{mbranch}' not found.")
            return
        if mbranch == prev_branch:
            print_notice(f"Already on branch '{mbranch}'.")
            return
        # Protect tracked edits and untracked files from checkout overwrites.
        current_index = {}
        if prev_commit_hash:
            current_index = {
                path: blob_hash
                for path, blob_hash in self.build_index_from_tree(prev_commit.tree_hash).items()
                if not self._is_internal_path(path)
            }
        staged_index = self.load_index()
        if staged_index and staged_index != current_index:
            print_error("Cannot switch branches: staged changes would be lost.")
            return

        if prev_commit_hash:
            for rel_path in files_to_clr:
                file_path = self.path / rel_path
                if not file_path.is_file() or BLOB(file_path.read_bytes()).hash() != current_index.get(rel_path):
                    print_error("Cannot switch branches: working tree has local changes.")
                    return
        target_commit_hash = (
            prev_commit_hash if create_branch
            else self.get_branch_commit(mbranch)
        )
        target_index = {}
        if target_commit_hash:
            target_resource = self.load_resource(target_commit_hash)
            if target_resource.type != "commit":
                raise ValueError("Branch reference does not point to a commit")
            target_commit = Commit.deserialize_commit(target_resource.content)
            target_index = {
                path: blob_hash
                for path, blob_hash in self.build_index_from_tree(target_commit.tree_hash).items()
                if not self._is_internal_path(path)
            }
        current_tracked = {
            path: blob_hash
            for path, blob_hash in (
                self.build_index_from_tree(prev_commit.tree_hash).items()
                if prev_commit_hash else []
            )
            if not self._is_internal_path(path)
        }
        for rel_path in set(target_index) - set(current_tracked):
            if (self.path / rel_path).exists():
                print_error(
                    "Cannot switch branches: untracked file would be overwritten: "
                    f"{Fore.WHITE}{rel_path}{Fore.RED}"
                )
                return
        if create_branch:
            self.set_branch_commit(mbranch, prev_commit_hash)
            print_success(f"Created new branch '{mbranch}'")
        self.head_file.write_text(f"ref: refs/heads/{mbranch}\n")
        self.resources_working_dir(mbranch, files_to_clr)

        print_success(f"Switched to branch: {mbranch}")

    def restore_tree(self, tree_hash: str, path: Path):
        tree_obj = self.load_resource(tree_hash)
        tree = Trees.from_content(tree_obj.content)
        for mode, name, obj_hash in tree.entries:
            abs_path = path / name
            if mode.startswith("100"):
                abs_path.parent.mkdir(parents=True, exist_ok=True)
                blob_obj = self.load_resource(obj_hash)
                if blob_obj.type != "blob":
                    raise ValueError(f"Resource {obj_hash} is not a blob")
                abs_path.write_bytes(blob_obj.content)
            elif mode.startswith("400"):
                abs_path.mkdir(parents=True, exist_ok=True)
                self.restore_tree(obj_hash, abs_path)
        

    def resources_working_dir(self, branch: str, files_to_clr: set[str]):
        target_commit_hash = self.get_branch_commit(branch)
        if not target_commit_hash:
            return

        #remove the files tracked by prev branch
        for rel_path in sorted(files_to_clr):
            file_path = self.path / rel_path
            try:
                if file_path.is_file():
                    file_path.unlink()
            except Exception:
                pass

        target_commit_obj = self.load_resource(target_commit_hash)
        target_commit = Commit.deserialize_commit(target_commit_obj.content)

        if target_commit.tree_hash:
            self.restore_tree(target_commit.tree_hash, self.path)
            # A checkout leaves the index matching the checked-out commit.
            self.save_index(self.build_index_from_tree(target_commit.tree_hash))

    def vers(self, branch_name: str, delete: bool = False):
        if delete and branch_name:
            branch_file = self._branch_file(branch_name)
            if branch_name == self.get_current_branch():
                print_error("Cannot delete the current branch.")
                return
            if branch_file.exists():
                branch_file.unlink()
                print_success(f"Deleted {branch_name} branch")
            else:
                print_error(f"Branch {branch_name} not found")

            return
        
        current_branch = self.get_current_branch()

        if branch_name:
            self._branch_file(branch_name)
            current_commit = self.get_branch_commit(current_branch)
            if current_commit:
                self.set_branch_commit(branch_name, current_commit)
                print_success(f"Created branch {branch_name}")
            else:
                print_error("No commits yet, cannot create a new branch")
        else:
            branches = []
            for branch_file in self.heads_dir.iterdir():
                if branch_file.is_file() and not branch_file.name.startswith("."):
                    branches.append(branch_file.name)

            for branch in sorted(branches):
                current_marker = "* " if branch == current_branch else "  "
                print(f"{current_marker}{branch}")

    def history(self, max_cnt: int = 10):
        current_branch = self.get_current_branch()
        commit_hash = self.get_branch_commit(current_branch)

        if not commit_hash:
            print_notice("No commits yet")
            return

        count = 0
        while commit_hash and count < max_cnt:
            commit_obj = self.load_resource(commit_hash)
            commit = Commit.deserialize_commit(commit_obj.content)

            print(f"Commit: {commit_hash}")
            print(f"Author: {commit.author}")
            print(f"Time: {time.ctime(commit.timestamp)}")
            print(f"\n     {commit.msg}")
            print("\n")

            commit_hash = commit.parent_hashes[0] if commit.parent_hashes else None
            count += 1

    def build_index_from_tree(self, tree_hash: str, prefix: str = ""):
        index = {}

        try:
            tree_obj = self.load_resource(tree_hash)
            tree = Trees.from_content(tree_obj.content)
            for mode, name, obj_hash in tree.entries:
                full_name = f"{prefix}{name}" if prefix else name
                if mode.startswith("100"):
                    index[full_name] = obj_hash
                elif mode.startswith("400"):
                    subindex = self.build_index_from_tree(obj_hash, f"{full_name}/")
                    index.update(subindex)
        except Exception as e:
            print_notice(f"Warning: Could not read tree {tree_hash}: {e}")

        return index

    def get_all_files(self):
        files = []
        for item in self.path.rglob("*"):
            if not item.is_file():
                continue
            relative_path = item.relative_to(self.path)
            if self._is_internal_path(str(relative_path)):
                continue
            files.append(item)
        return files


    def state(self):
        current_branch = self.get_current_branch()
        print(f"On branch: {current_branch}")
        index = {
            path: blob_hash
            for path, blob_hash in (self.load_index() or {}).items()
            if not self._is_internal_path(path)
        }
        current_commit_hash = self.get_branch_commit(current_branch)
        last_index_file = {}

        if current_commit_hash:
            try:
                commit_obj = self.load_resource(current_commit_hash)
                if commit_obj.type != "commit":
                    raise ValueError("Branch reference does not point to a commit")
                commit = Commit.deserialize_commit(commit_obj.content)

                if commit.tree_hash:
                    last_index_file = {
                        path: blob_hash
                        for path, blob_hash in self.build_index_from_tree(commit.tree_hash).items()
                        if not self._is_internal_path(path)
                    }
            except Exception as e:
                print_error(f"Error loading latest commit: {e}")
                return

        # Older Quasar versions cleared the index after committing. Merge
        # the commit snapshot so existing repositories do not report staged
        # additions as deletions of every previously committed file.
        index = {**last_index_file, **index}

        working_files = {}
        for item in self.get_all_files():
            file_path = str(item.relative_to(self.path))

            try:
                blob = BLOB(item.read_bytes())
                working_files[file_path] = blob.hash()
            except OSError:
                continue

        staged_files = []
        unstaged_files = []
        untracked_files = []
        deleted_files = []

        # Compare index against the latest commit.
        all_tracked_files = set(index) | set(last_index_file)

        for file_path in sorted(all_tracked_files):
            index_hash = index.get(file_path)
            commit_hash = last_index_file.get(file_path)

            if index_hash == commit_hash:
                continue

            if commit_hash is None:
                staged_files.append(("New File", file_path))
            elif index_hash is None:
                staged_files.append(("Deleted", file_path))
            else:
                staged_files.append(("Modified", file_path))

        # Compare working directory against the index.
        for file_path in sorted(set(working_files) | set(index)):
            working_hash = working_files.get(file_path)
            index_hash = index.get(file_path)

            if working_hash == index_hash:
                continue
            if working_hash is None and index_hash is not None:
                deleted_files.append(file_path)
            elif working_hash is not None and index_hash is not None:
                unstaged_files.append(file_path)
            elif working_hash is not None and index_hash is None:
                if file_path not in last_index_file:
                    untracked_files.append(file_path)

        if staged_files:
            print(Fore.YELLOW + "\nChanges to be committed:" + Fore.RESET)
            for status, file_path in staged_files:
                print(f"    {status}: {file_path}")

        if unstaged_files:
            print(Fore.YELLOW + "\nChanges not staged for commit:" + Fore.RESET)
            for file_path in unstaged_files:
                print(f"    Modified: {file_path}")

        if deleted_files:
            print(Fore.YELLOW + "\nChanges not staged for commit:" + Fore.RESET)
            for file_path in deleted_files:
                print(f"    Deleted: {file_path}")

        if untracked_files:
            print(Fore.RED + "\nUntracked files:" + Fore.RESET)
            for file_path in untracked_files:
                print(f"    {file_path}")

        if not (
            staged_files
            or unstaged_files
            or deleted_files
            or untracked_files
        ):
            print_success("\nWorking tree clean.")


def main():
    parser = argparse.ArgumentParser(
        description='QUASAR - Simple Version Control Interface'
    )
    subparser = parser.add_subparsers(
        dest="command",
        help="Available Commands"
    )

    #INIT Command (ready)
    ready_parser = subparser.add_parser("ready", help=Fore.BLUE + "Initialize a new repository" + Fore.RESET)

    #ADD Command (save)
    save_parser = subparser.add_parser("save", help=Fore.BLUE + "Add files and directories" + Fore.RESET)
    save_parser.add_argument("paths", nargs='+', help=Fore.BLUE + "Files and directories to save" + Fore.RESET)

    #COMMIT Command (done)
    done_parser = subparser.add_parser("done", help=Fore.BLUE + "Commit your changes" + Fore.RESET)
    done_parser.add_argument("-m", "--message", help=Fore.BLUE + "Commit Message" + Fore.RESET, required=True)
    done_parser.add_argument("--author", "-a", help=Fore.BLUE + "Author name and email" + Fore.RESET)

    #CHECKOUT Command (branch)
    branch_parser = subparser.add_parser("branch", help=Fore.BLUE + "Create another branch or move to one" + Fore.RESET)
    branch_parser.add_argument("mbranch", help=Fore.BLUE + "Branch to switch to" + Fore.RESET)
    branch_parser.add_argument("-b", "--create-branch", action="store_true", help=Fore.BLUE + "Manage Branch" + Fore.RESET)

    #BRANCH Command (vers)
    vers_parser = subparser.add_parser("vers", help=Fore.BLUE + "List/Manage Branches" + Fore.RESET)
    vers_parser.add_argument("-b", "--branch", action="store_true", help=Fore.BLUE + "create new branch" + Fore.RESET)
    vers_parser.add_argument("-d", "--delete", action="store_true", help=Fore.BLUE + "delete the branch" + Fore.RESET)
    vers_parser.add_argument("name", nargs="?", help=Fore.BLUE + "list the branch" + Fore.RESET)

    #LOG Command (history)
    history_parser = subparser.add_parser("history", help=Fore.BLUE + "History of all commits" + Fore.RESET)
    history_parser.add_argument("-n", "--max-count", type=int, default=10, help=Fore.BLUE + "Limits commits shown" + Fore.RESET)

    #STATUS Command (state)
    state_parser = subparser.add_parser("state", help=Fore.BLUE + "Show repository status" + Fore.RESET)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return
            
    repo = Repository()

    try:
        if args.command == "ready":
            if not repo.ready():
                print_notice("Repository already exists.")
                return

        elif args.command == "save":
            if not repo.quasar_dir.exists():
                print_error("Not a Quasar Directory")
                return

            for path in args.paths:
                repo.save_path(path)

        elif args.command == "done":
            if not repo.quasar_dir.exists():
                print_error("Not a Quasar Directory")
                return
            author = args.author or "Quasar User <user@quasar.com>"
            repo.done(args.message, author=author)

        elif args.command == "branch":
            if not repo.quasar_dir.exists():
                print_error("Not a Quasar Directory")
                return
            repo.branch(args.mbranch, args.create_branch)

        elif args.command == "vers":
            if not repo.quasar_dir.exists():
                print_error("Not a Quasar Directory")
                return
            repo.vers(args.name, args.delete)

        elif args.command == "history":
            if not repo.quasar_dir.exists():
                print_error("Not a Quasar Directory")
                return
            repo.history(args.max_count)

        elif args.command == "state":
            if not repo.quasar_dir.exists():
                print_error("Not a Quasar Directory")
                return
            repo.state()
            
    except (OSError, ValueError, zlib.error, json.JSONDecodeError) as exc:
        parser.exit(1, f"{Fore.RED}quasar: {exc}{Fore.RESET}\n")


if __name__ == "__main__":
    main()
