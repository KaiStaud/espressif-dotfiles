# Git Bash helpers

Unmodified source files from [Git v2.51.0](https://github.com/git/git/tree/v2.51.0),
commit `c44beea485f0f2feaf460e2ac87fdd5608d63cf0`:

- `git-completion.bash`: `contrib/completion/git-completion.bash`
- `git-prompt.sh`: `contrib/completion/git-prompt.sh`
- `COPYING`: upstream license, GNU GPL version 2

Copyright notices remain in the original files. These files are supplied as
source, under their upstream license. `upstream.json` records immutable source
paths and SHA-256 checksums. System-provided helpers and already configured
completions/prompts take precedence. No helper is downloaded during installation
or shell startup.

To update, review a Git release, resolve its tag to a commit, copy these three
files from that commit without modification and update this document and
`upstream.json`. Then run `python3 tests/test_install.py`. Do not replace the
helpers with unpinned downloads from a moving branch.
