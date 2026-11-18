#!/usr/bin/env python3
"""Run against temporary homes only; no host Git or shell settings are loaded."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dotfiles-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home with spaces"
        self.home.mkdir()
        self.cwd = self.root / "unrelated directory"
        self.cwd.mkdir()
        self.repo = REPO
        self.env = {
            key: value for key, value in os.environ.items()
            if not key.startswith("GIT_")
            and not key.startswith("DOTFILES_GIT_")
            and key not in {"BASH_ENV", "ENV", "CDPATH", "BASHOPTS", "SHELLOPTS"}
            and not key.startswith("BASH_FUNC_")
        }
        self.env.update(HOME=str(self.home),
                        XDG_CONFIG_HOME=str(self.home / ".config"),
                        GIT_CONFIG_NOSYSTEM="1", TERM="dumb")

    def run_command(self, *args, check=True):
        result = subprocess.run(args, cwd=self.cwd, env=self.env,
                                capture_output=True, text=True)
        if check:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def install(self, check=True):
        return self.run_command(str(self.repo / "install.sh"), check=check)

    def get(self, key):
        return self.run_command("git", "config", "--includes",
                                "--get", key).stdout.strip()

    def snapshot(self):
        return {
            str(path.relative_to(self.home)):
                ("link", os.readlink(path)) if path.is_symlink()
                else ("file", path.read_bytes(), path.stat().st_mode)
            for path in self.home.rglob("*") if path.is_file() or path.is_symlink()
        }

    def assert_repeatable(self):
        before = self.snapshot()
        self.install()
        self.assertEqual(before, self.snapshot())
        self.assertEqual((self.home / ".bashrc").read_text().count(
            "# >>> espressif-dotfiles >>>"), 1)

    def test_clean_home_and_real_git_alias(self):
        self.install()
        self.assertEqual(self.get("alias.st"), "status --short --branch")
        self.assertEqual(self.get("pull.ff"), "only")
        self.assertEqual(self.get("init.defaultBranch"), "main")
        self.run_command("git", "init", "--quiet")
        self.assertIn("main", self.run_command("git", "st").stdout)
        self.assertFalse(list(self.home.glob("*.dotfiles-backup.*")))
        self.assert_repeatable()

    def test_existing_config_includes_and_aliases(self):
        bashrc = "# My shell\nalias ll='printf personal'\ngs() { printf function; }\n"
        original = ('# My Git settings\n[user]\n name = Existing User\n'
                    ' email = existing@example.test\n[credential]\n helper = personal\n'
                    '[fetch]\n prune = false\n[pull]\n ff =\n'
                    '[include]\n path = personal.gitconfig\n')
        (self.home / ".bashrc").write_text(bashrc)
        (self.home / ".gitconfig").write_text(original)
        included = self.home / "personal.gitconfig"
        included.write_text('[alias]\n st = status --porcelain\n')
        self.install()
        self.assertTrue((self.home / ".bashrc").read_text().startswith(bashrc))
        self.assertEqual(self.get("user.name"), "Existing User")
        self.assertEqual(self.get("user.email"), "existing@example.test")
        self.assertEqual(self.get("credential.helper"), "personal")
        self.assertEqual(self.get("alias.st"), "status --porcelain")
        self.assertEqual(self.get("fetch.prune"), "false")
        self.assertEqual(self.get("pull.ff"), "")
        self.assertEqual(included.read_text(), '[alias]\n st = status --porcelain\n')
        self.assertEqual(next(self.home.glob(".bashrc.dotfiles-backup.*")).read_text(), bashrc)
        self.assertEqual(next(self.home.glob(".gitconfig.dotfiles-backup.*")).read_text(), original)
        shell = self.run_command("bash", "--noprofile", "--norc", "-ic",
            'before=$PATH; . "$HOME/.bashrc"; . "$HOME/.bashrc"; '
            'alias ll; declare -f gs; alias gd; [[ $before == "$PATH" ]]')
        self.assertIn("printf personal", shell.stdout)
        self.assertIn("printf function", shell.stdout)
        self.assertIn("git diff", shell.stdout)
        self.assert_repeatable()

    def test_xdg_config_is_preserved(self):
        xdg = self.home / ".config/git/config"
        xdg.parent.mkdir(parents=True)
        original = '[alias]\n st = status --porcelain\n[pull]\n ff = false\n'
        xdg.write_text(original)
        self.install()
        self.assertEqual(xdg.read_text(), original)
        self.assertEqual(self.get("pull.ff"), "false")
        self.assertEqual(self.get("alias.st"), "status --porcelain")
        self.assertEqual(self.get("alias.last"), "log -1 --stat")
        self.assert_repeatable()

    def test_inactive_conditional_include_skips_git_changes(self):
        original = '[includeIf "gitdir:/does/not/match/"]\n path = other.gitconfig\n'
        (self.home / ".gitconfig").write_text(original)
        (self.home / "other.gitconfig").write_text('[pull]\n ff = false\n')
        result = self.install()
        self.assertIn("includeIf", result.stdout)
        self.assertEqual((self.home / ".gitconfig").read_text(), original)
        self.assertFalse(list(self.home.glob(".gitconfig.dotfiles-backup.*")))
        self.assert_repeatable()

    def test_symlinks_are_retained(self):
        for name, content in ((".bashrc", "# custom\n"),
                              (".gitconfig", "[user]\n name = Existing\n")):
            target = self.home / (name + ".actual")
            target.write_text(content)
            (self.home / name).symlink_to(target.name)
        self.install()
        self.assertTrue((self.home / ".bashrc").is_symlink())
        self.assertTrue((self.home / ".gitconfig").is_symlink())
        self.assertEqual(self.get("user.name"), "Existing")
        self.assert_repeatable()

    def test_checkout_path_with_shell_metacharacters(self):
        self.repo = self.root / "dot files ' \" $(); [x]"
        shutil.copytree(REPO, self.repo, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        self.install()
        shell = self.run_command("bash", "--noprofile", "--norc", "-ic",
                                 '. "$HOME/.bashrc"; alias ll; alias gd')
        self.assertIn("ls -alF", shell.stdout)
        self.assertIn("git diff", shell.stdout)
        self.assert_repeatable()

    def test_existing_program_is_not_shadowed(self):
        binaries = self.root / "bin"
        binaries.mkdir()
        program = binaries / "gs"
        program.write_text("#!/bin/sh\nprintf existing-program\\n\n")
        program.chmod(0o755)
        self.env["PATH"] = str(binaries) + os.pathsep + self.env["PATH"]
        self.install()
        shell = self.run_command("bash", "--noprofile", "--norc", "-ic",
            '. "$HOME/.bashrc"; ! alias gs >/dev/null 2>&1; command -v gs')
        self.assertEqual(shell.stdout.strip(), str(program))

    def test_explicit_global_config(self):
        custom = self.home / "custom gitconfig"
        custom.write_text('[user]\n name = Custom\n')
        self.env["GIT_CONFIG_GLOBAL"] = str(custom)
        self.install()
        self.assertFalse((self.home / ".gitconfig").exists())
        self.assertEqual(self.get("user.name"), "Custom")
        self.assertEqual(self.get("alias.st"), "status --short --branch")
        self.assert_repeatable()

    def test_invalid_git_config_leaves_home_unchanged(self):
        (self.home / ".bashrc").write_text("# existing\n")
        (self.home / ".gitconfig").write_text("[invalid\n")
        before = self.snapshot()
        self.assertNotEqual(self.install(check=False).returncode, 0)
        self.assertEqual(before, self.snapshot())

    def test_modified_loader_leaves_home_unchanged(self):
        (self.home / ".bashrc").write_text(
            "# >>> espressif-dotfiles >>>\n# personal edit\n# <<< espressif-dotfiles <<<\n")
        before = self.snapshot()
        self.assertNotEqual(self.install(check=False).returncode, 0)
        self.assertEqual(before, self.snapshot())

    def test_dangling_symlink_leaves_home_unchanged(self):
        (self.home / ".bashrc").symlink_to("missing")
        before = self.snapshot()
        self.assertNotEqual(self.install(check=False).returncode, 0)
        self.assertEqual(before, self.snapshot())

    def test_noninteractive_shell_gets_no_aliases(self):
        shell = self.run_command("bash", "--noprofile", "--norc", "-c",
            'PS1=original; . "$1"; ! alias ll >/dev/null 2>&1; '
            '! declare -F __git_ps1; ! declare -F __git_complete; [[ $PS1 == original ]]',
            "test", str(REPO / "bash/aliases.sh"))
        self.assertEqual(shell.stdout, "")

    def git_shell(self, script):
        self.env["DOTFILES_GIT_USE_BUNDLED"] = "1"
        return self.run_command("bash", "--noprofile", "--norc", "-ic", script,
                                "test", str(self.repo / "bash/git.sh"))

    def create_git_repo(self):
        self.run_command("git", "init", "--quiet", "--initial-branch=main")
        (self.cwd / "tracked").write_text("original\n")
        self.run_command("git", "add", "tracked")
        self.run_command("git", "-c", "user.name=Test", "-c",
                         "user.email=test@example.test", "commit", "--quiet", "-m", "Initial")

    def test_real_branch_and_subcommand_completion(self):
        self.create_git_repo()
        self.run_command("git", "branch", "feature/example")
        shell = self.git_shell(
            '. "$1"; COMP_WORDS=(git switch fe); COMP_CWORD=2; '
            'COMP_LINE="git switch fe"; COMP_POINT=${#COMP_LINE}; '
            '__git_wrap__git_main; printf "%s\\n" "${COMPREPLY[@]}"; '
            'COMP_WORDS=(git che); COMP_CWORD=1; COMP_LINE="git che"; '
            'COMP_POINT=${#COMP_LINE}; __git_wrap__git_main; '
            'printf "%s\\n" "${COMPREPLY[@]}"')
        self.assertIn("feature/example", shell.stdout)
        self.assertIn("checkout", shell.stdout)

    def test_prompt_status_preserves_array_hooks(self):
        self.create_git_repo()
        (self.cwd / "tracked").write_text("changed\n")
        (self.cwd / "staged").write_text("staged\n")
        (self.cwd / "untracked").write_text("new\n")
        self.run_command("git", "add", "staged")
        shell = self.git_shell(
            'PS1="custom> "; PROMPT_COMMAND=(":" "printf hook"); '
            'hooks=$(declare -p PROMPT_COMMAND); . "$1"; first=$PS1; . "$1"; '
            '[[ $first == "$PS1" && $(declare -p PROMPT_COMMAND) == "$hooks" ]] || exit 1; '
            'printf "%s" "${PS1@P}"')
        commit = self.run_command("git", "rev-parse", "--short", "HEAD").stdout.strip()
        self.assertEqual(shell.stdout, f"{self.cwd} on main [{commit}] [dirty] $ ")

    def test_prompt_detached_head_with_changes(self):
        self.create_git_repo()
        commit = self.run_command("git", "rev-parse", "--short", "HEAD").stdout.strip()
        self.run_command("git", "switch", "--quiet", "--detach")
        (self.cwd / "tracked").write_text("changed\n")
        shell = self.git_shell('PS1="custom> "; . "$1"; printf "%s" "${PS1@P}"')
        self.assertEqual(shell.stdout, f"{self.cwd} on detached HEAD [{commit}] [dirty] $ ")

    def test_prompt_shows_ahead_and_behind_counts(self):
        self.create_git_repo()
        self.run_command("git", "switch", "-qc", "upstream")
        self.run_command("git", "-c", "user.name=Test", "-c", "user.email=test@example.test",
                         "commit", "--quiet", "--allow-empty", "-m", "Upstream")
        self.run_command("git", "switch", "--quiet", "main")
        self.run_command("git", "-c", "user.name=Test", "-c", "user.email=test@example.test",
                         "commit", "--quiet", "--allow-empty", "-m", "Local")
        self.run_command("git", "branch", "--set-upstream-to=upstream")
        commit = self.run_command("git", "rev-parse", "--short", "HEAD").stdout.strip()
        shell = self.git_shell('PS1="custom> "; . "$1"; printf "%s" "${PS1@P}"')
        self.assertEqual(shell.stdout, f"{self.cwd} on main [{commit}] [+1|-1] $ ")

    def test_prompt_outside_git_repo(self):
        shell = self.git_shell('PS1="custom> "; . "$1"; printf "%s" "${PS1@P}"')
        self.assertEqual(shell.stdout, f"{self.cwd} $ ")

    def test_existing_completion_and_git_prompt_are_preserved(self):
        shell = self.git_shell(
            'mine() { :; }; complete -F mine git; complete -W keep gd; '
            '__git_ps1() { printf custom; }; PS1=\'$(__git_ps1)> \'; '
            'before=$PS1; . "$1"; '
            '[[ $PS1 == "$before" ]] || exit 1; '
            'complete -p git; complete -p gd; __git_ps1')
        self.assertIn("-F mine git", shell.stdout)
        self.assertIn("-W 'keep' gd", shell.stdout)
        self.assertTrue(shell.stdout.endswith("custom"))

    def test_prompt_manager_is_preserved(self):
        shell = self.git_shell(
            'PS1="managed> "; PROMPT_COMMAND="starship_precmd"; '
            '. "$1"; [[ $PS1 == "managed> " && $PROMPT_COMMAND == starship_precmd ]]')
        self.assertEqual(shell.stdout, "")

    def test_feature_opt_outs(self):
        shell = self.git_shell(
            'DOTFILES_GIT_COMPLETION=0; DOTFILES_GIT_PROMPT=0; PS1=original; '
            '. "$1"; [[ $PS1 == original ]] || exit 1; '
            '! complete -p git >/dev/null 2>&1; ! declare -F __git_ps1; '
            '! declare -F __git_complete')
        self.assertEqual(shell.stdout, "")

    def test_existing_status_preferences_are_preserved(self):
        shell = self.git_shell(
            'GIT_PS1_SHOWDIRTYSTATE=; GIT_PS1_SHOWUNTRACKEDFILES=; '
            'GIT_PS1_SHOWUPSTREAM=verbose; . "$1"; '
            '[[ -z $GIT_PS1_SHOWDIRTYSTATE && -z $GIT_PS1_SHOWUNTRACKEDFILES && '
            '$GIT_PS1_SHOWUPSTREAM == verbose ]]')
        self.assertEqual(shell.stdout, "")

    def test_our_aliases_receive_completion_once(self):
        self.install()
        shell = self.git_shell(
            '. "$HOME/.bashrc"; first=$(complete -p gd gl); '
            '. "$HOME/.bashrc"; [[ $(complete -p gd gl) == "$first" ]] || exit 1; '
            'complete -p gd gl')
        self.assertIn("__git_wrap_git_diff gd", shell.stdout)
        self.assertIn("__git_wrap_git_log gl", shell.stdout)

    def test_vendor_checksums(self):
        vendor = REPO / "bash/vendor"
        manifest = json.loads((vendor / "upstream.json").read_text())
        self.assertEqual(manifest["commit"], "c44beea485f0f2feaf460e2ac87fdd5608d63cf0")
        for name, info in manifest["files"].items():
            self.assertEqual(hashlib.sha256((vendor / name).read_bytes()).hexdigest(),
                             info["sha256"], name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
