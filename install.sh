#!/usr/bin/env bash
# Personal configuration only; run as the container's remoteUser, without sudo.
set -euo pipefail

die() { printf 'dotfiles: %s\n' "$*" >&2; exit 1; }
command -v git >/dev/null 2>&1 || die 'Git wird benötigt.'
[[ -n ${HOME:-} && -d $HOME ]] || die 'HOME muss ein vorhandenes Verzeichnis sein.'
repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
aliases_file="$repo_dir/bash/aliases.sh"
defaults_file="$repo_dir/git/.gitconfig"
bashrc="$HOME/.bashrc"
gitconfig=${GIT_CONFIG_GLOBAL:-"$HOME/.gitconfig"}
global_configs=()
if [[ ${GIT_CONFIG_GLOBAL+x} ]]; then
    [[ -n $GIT_CONFIG_GLOBAL ]] || die 'GIT_CONFIG_GLOBAL darf nicht leer sein.'
    global_configs+=("$GIT_CONFIG_GLOBAL")
else
    global_configs+=("${XDG_CONFIG_HOME:-$HOME/.config}/git/config" "$HOME/.gitconfig")
fi

for file in "$aliases_file" "$defaults_file" "$repo_dir/bash/git.sh" \
    "$repo_dir/bash/vendor/git-completion.bash" "$repo_dir/bash/vendor/git-prompt.sh"; do
    [[ -f $file && -r $file ]] || die "Datei nicht lesbar: $file"
done
for file in "$bashrc" "$gitconfig"; do
    if [[ -e $file || -L $file ]]; then
        [[ -f $file && -r $file && -w $file ]] || die "Keine beschreibbare reguläre Datei: $file"
    fi
done
# Read both global files explicitly. Some Git versions select only one file
# with --global, and --global --list may fail when no config exists yet.
for file in "${global_configs[@]}"; do
    if [[ -e $file || -L $file ]]; then
        git config --file "$file" --includes --list >/dev/null
    fi
done
git config --file "$defaults_file" --list >/dev/null

begin='# >>> espressif-dotfiles >>>'
end='# <<< espressif-dotfiles <<<'
printf -v loader 'if [ -r %q ]; then . %q; fi' "$aliases_file" "$aliases_file"
install_loader=true
if [[ -f $bashrc ]] && { grep -Fqx -- "$begin" "$bashrc" || grep -Fqx -- "$end" "$bashrc"; }; then
    # Do not silently replace a block from a different checkout or a user's edit.
    existing_block=$(sed -n '/^# >>> espressif-dotfiles >>>$/,/^# <<< espressif-dotfiles <<<$/p' "$bashrc")
    expected_block=$(printf '%s\n%s\n%s' "$begin" "$loader" "$end")
    [[ $existing_block == "$expected_block" ]] || die 'Abweichender Dotfiles-Block in ~/.bashrc. Alten Block prüfen und vor einer Neuinstallation entfernen.'
    install_loader=false
fi

keys=()
values=()
# Inactive includeIf files may contain preferences for other projects. Appending
# defaults could override them later, so leave all Git settings alone in this case.
conditional_includes=false
for file in "${global_configs[@]}"; do
    if [[ -f $file ]] && git config --file "$file" --includes --get-regexp '^includeif\.' >/dev/null; then
        conditional_includes=true
    fi
done
if "$conditional_includes"; then
    printf 'Git-Defaults übersprungen: bestehende includeIf-Konfiguration.\n'
fi
key_is_configured() {
    local config_file status
    for config_file in "${global_configs[@]}"; do
        [[ -f $config_file ]] || continue
        if git config --file "$config_file" --includes --get "$1" >/dev/null; then
            return 0
        else
            status=$?
            [[ $status == 1 ]] || die "Git-Einstellung konnte nicht gelesen werden: $1"
        fi
    done
    return 1
}
while IFS= read -r -d '' entry; do
    if "$conditional_includes"; then continue; fi
    key=${entry%%$'\n'*}
    value=${entry#*$'\n'}
    if key_is_configured "$key"; then
        continue
    fi
    keys+=("$key")
    values+=("$value")
done < <(git config --file "$defaults_file" --null --list)

backup() {
    local original=$1 saved
    if [[ -f $original ]]; then
        saved=$(mktemp "${original}.dotfiles-backup.XXXXXX")
        cp -pL -- "$original" "$saved"
        printf 'Sicherung: %s\n' "$saved"
    fi
}

if "$install_loader"; then
    backup "$bashrc"
    printf '\n%s\n%s\n%s\n' "$begin" "$loader" "$end" >> "$bashrc"
fi
if ((${#keys[@]})); then
    backup "$gitconfig"
    for ((i = 0; i < ${#keys[@]}; i++)); do
        # Explicit file: never overwrite an existing XDG Git config.
        git config --file "$gitconfig" "${keys[i]}" "${values[i]}"
    done
fi
printf 'Dotfiles eingerichtet. Neues Bash-Terminal öffnen.\n'
