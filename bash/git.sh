# Interactive Bash integration. No downloads, package installs or prompt hooks.
case $- in
    *i*) ;;
    *) return ;;
esac
command -v git >/dev/null 2>&1 || return 0

__espressif_dotfiles_git_prompt() {
    local status line branch commit ahead=+0 behind=-0 dirty=
    status=$(git --no-optional-locks status --porcelain=v2 --branch --ahead-behind 2>/dev/null) || return 0

    while IFS= read -r line; do
        case $line in
            '# branch.oid '*) commit=${line#'# branch.oid '} ;;
            '# branch.head '*) branch=${line#'# branch.head '} ;;
            '# branch.ab '*)
                read -r ahead behind <<< "${line#'# branch.ab '}"
                ;;
            '1 '*|'2 '*|'u '*) [[ -z $GIT_PS1_SHOWDIRTYSTATE ]] || dirty=' [dirty]' ;;
            '? '*) [[ -z $GIT_PS1_SHOWUNTRACKEDFILES ]] || dirty=' [dirty]' ;;
        esac
    done <<< "$status"

    [[ $branch != '(detached)' ]] || branch='detached HEAD'
    if [[ $commit == '(initial)' ]]; then
        commit='no commit'
    else
        commit=$(git rev-parse --short "$commit" 2>/dev/null) || return 0
    fi
    printf ' on %s [%s]%s' "$branch" "$commit" "$dirty"
    if [[ -n $GIT_PS1_SHOWUPSTREAM && ( $ahead != +0 || $behind != -0 ) ]]; then
        printf ' [%s|%s]' "$ahead" "$behind"
    fi
}

__espressif_dotfiles_git_setup() {
    local script_dir candidate hooks name expansion
    local -a completion_files
    script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
    completion_files=()
    if [[ ${DOTFILES_GIT_USE_BUNDLED:-0} != 1 ]]; then
        completion_files+=(
            /usr/share/bash-completion/completions/git
            /usr/share/git/completion/git-completion.bash
            /usr/share/git-core/contrib/completion/git-completion.bash
            /etc/bash_completion.d/git
        )
    fi
    completion_files+=("$script_dir/vendor/git-completion.bash")

    if [[ ${DOTFILES_GIT_COMPLETION:-1} != 0 ]]; then
        if ! complete -p git >/dev/null 2>&1; then
            if ! declare -F __git_complete >/dev/null; then
                for candidate in "${completion_files[@]}"; do
                    if [[ -r $candidate ]]; then
                        . "$candidate"
                        declare -F __git_complete >/dev/null && break
                    fi
                done
            fi
            if ! complete -p git >/dev/null 2>&1 && declare -F __git_complete >/dev/null; then
                __git_complete git __git_main
            fi
        fi
        # Register only our exact alias expansions; never replace user completions.
        if declare -F __git_complete >/dev/null; then
            for name in gs gd gl; do
                case $name in
                    gs) expansion='git status --short --branch' ;;
                    gd) expansion='git diff' ;;
                    gl) expansion='git log --graph --decorate --oneline -20' ;;
                esac
                if [[ $(alias "$name" 2>/dev/null) == "alias $name='$expansion'" ]] &&
                    ! complete -p "$name" >/dev/null 2>&1; then
                    case $name in
                        gs) __git_complete gs git_status ;;
                        gd) __git_complete gd git_diff ;;
                        gl) __git_complete gl git_log ;;
                    esac
                fi
            done
        fi
    fi

    [[ ${DOTFILES_GIT_PROMPT:-1} != 0 ]] || return 0
    shopt -q promptvars || return 0
    [[ -n ${PS1-} ]] || return 0
    hooks=$(declare -p PROMPT_COMMAND 2>/dev/null || :)
    # Recognize existing Git prompts and common prompt managers. Their PS1 and
    # PROMPT_COMMAND remain untouched (including array-valued PROMPT_COMMAND).
    case "${PS1-} $hooks" in
        *__espressif_dotfiles_git_prompt*|*__git_ps1*|*starship*|*oh_my_posh*|*powerline*|*liquidprompt*) return 0 ;;
    esac
    : "${GIT_PS1_SHOWDIRTYSTATE=1}"
    : "${GIT_PS1_SHOWUNTRACKEDFILES=1}"
    : "${GIT_PS1_SHOWUPSTREAM=auto}"
    PS1='$(pwd)$(__espressif_dotfiles_git_prompt) \$ '
    return 0
}
__espressif_dotfiles_git_setup
unset -f __espressif_dotfiles_git_setup
