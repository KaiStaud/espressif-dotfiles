# Sourced by ~/.bashrc. Keep existing aliases, functions and commands.
case $- in
    *i*) ;;
    *) return ;;
esac

command -v ll >/dev/null 2>&1 || alias ll='ls -alF'
command -v la >/dev/null 2>&1 || alias la='ls -A'
command -v .. >/dev/null 2>&1 || alias ..='cd ..'
command -v gs >/dev/null 2>&1 || alias gs='git status --short --branch'
command -v gd >/dev/null 2>&1 || alias gd='git diff'
command -v gl >/dev/null 2>&1 || alias gl='git log --graph --decorate --oneline -20'
. "$(dirname -- "${BASH_SOURCE[0]}")/git.sh"
# Sourcing an already-configured file must also return successfully.
:
