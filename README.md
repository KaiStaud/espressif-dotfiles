# Persönliche Dotfiles für Dev Containers

Dieses Repository ergänzt Bash-Aliases, Git-Tabvervollständigung, Git-Anzeige im
Prompt und persönliche Git-Defaults im
Home-Verzeichnis des Containerbenutzers. Es installiert keine Pakete und benötigt
weder `sudo` noch Netzwerkzugriff während der Installation.

ESP-IDF-Version, Toolchain, Dockerfile, USB-Zuordnung, Firmware und
projektspezifische VS-Code-Tasks bleiben im Smartscale-Repository. Insbesondere
werden weder `IDF_PATH` noch Python-Umgebungen oder PATH geändert. Der bestehende
Bash-Prompt erhält bei Bedarf eine Git-Anzeige als Präfix.

## Native VS-Code-Integration

1. Im lokalen VS Code das Profil **Smartscale** auswählen bzw. erstellen und
   die Erweiterung **Dev Containers** (`ms-vscode-remote.remote-containers`) aktivieren.
2. Über **Preferences: Open User Settings (JSON)** die folgenden Einstellungen
   in die vorhandenen Benutzereinstellungen dieses Profils einfügen:

   ```json
   {
     "dotfiles.repository": "KaiStaud/espressif-dotfiles",
     "dotfiles.targetPath": "~/dotfiles",
     "dotfiles.installCommand": "install.sh"
   }
   ```

   Vorhandene Einstellungen ergänzen. Die Datei nicht vollständig ersetzen.
   Diese persönlichen Einstellungen gehören weder in die Projekt-Tasks noch
   in die `devcontainer.json`. Ein exportiertes `.code-profile` ist nicht nötig.
3. Änderungen an diesem Dotfiles-Repository selbst committen und zum angegebenen
   Remote pushen, damit VS Code sie beim Klonen erhält. Lokale, uncommittete
   Änderungen unter `/work/Projects/vscode/smartscale/espressif-dotfiles` werden
   durch die Repository-Einstellung nicht automatisch in den Container übertragen.
4. Smartscale mit diesem Profil öffnen und **Dev Containers: Reopen in Container**
   ausführen. Bei einem bestehenden Container **Dev Containers: Rebuild Container**
   verwenden. Bei privaten Repositories muss der Git-Zugriff für VS Code funktionieren.

Die Erweiterung klont das Repository bei der Container-Einrichtung nach
`~/dotfiles` und führt dessen `install.sh` als Containerbenutzer aus. Das Profil
verwaltet die Einstellungen; die Dev-Containers-Erweiterung führt die Integration
aus. Das ist keine fortlaufende Synchronisierung von Dotfiles oder Profilen.

Siehe die [offizielle VS-Code-Dokumentation zur Dotfiles-Integration](https://code.visualstudio.com/docs/devcontainers/containers#_personalizing-with-dotfile-repositories).

## Dateien und Voraussetzungen

```text
install.sh          Idempotente Installation
bash/aliases.sh     Bash-Aliases mit Vorrang für vorhandene Definitionen
bash/git.sh         Git-Completion und Branch-/Statusanzeige im Bash-Prompt
bash/vendor/        Offizielle Git-Helfer als Offline-Fallback, mit Lizenz
git/.gitconfig      Vorlage für fehlende globale Git-Einstellungen
tests/test_install.py  Integrationstests mit isolierten Home-Verzeichnissen
```

Vorausgesetzt werden Linux, Bash 4.4 oder neuer, Git und übliche Basiswerkzeuge
(`grep`, `sed`, `mktemp`, `cp`). Python 3 wird nur für die Tests benötigt.
Installation ohne `sudo` im Container:

```bash
~/dotfiles/install.sh
```

Das Skript kann aus jedem Arbeitsverzeichnis gestartet werden. Manuell auf dem
Host ausgeführt, konfiguriert es dessen Benutzerkonto statt des Containers.

## Bestehende Konfiguration und Wiederholungen

- `~/.bashrc` erhält genau einen markierten Block am Ende. Vorheriger Inhalt
  bleibt erhalten. Der Block lädt die Alias-Datei direkt aus diesem Checkout;
  das Repository muss deshalb an diesem Ort bleiben. Vorhandene Aliases,
  Funktionen und gleichnamige Programme haben Vorrang. Unterstützt wird Bash;
  Zsh und Fish werden nicht verändert.
- Git-Defaults werden einzeln nur für Schlüssel ergänzt, die in der globalen
  Konfiguration einschließlich aktiver Includes fehlen. Bestehende Werte,
  auch `false` oder leere Werte, bleiben bestehen. Geschrieben wird nach
  `~/.gitconfig` bzw. in die explizit gesetzte Datei `GIT_CONFIG_GLOBAL`.
  Eine vorhandene XDG-Konfiguration (`$XDG_CONFIG_HOME/git/config` bzw.
  `~/.config/git/config`) wird berücksichtigt und nicht verändert.
- Bei vorhandenen bedingten Git-Includes (`includeIf`) werden sämtliche
  Git-Defaults vorsorglich übersprungen: Einstellungen für andere Projekte
  können während der Installation inaktiv sein und sollen auch später Vorrang
  behalten. Die Bash-Installation läuft weiter.
- Git-Identität, Zugangsdaten, Signierung und `safe.directory` werden nicht
  gesetzt. Lokale Git-Einstellungen eines Projekts behalten ihren Vorrang.
- Vor einer Änderung wird eine vorhandene Zieldatei als
  `<Dateiname>.dotfiles-backup.<Zufall>` gesichert; der Pfad wird ausgegeben.
  Bei unveränderter Wiederholung entstehen weder neue Einträge noch Sicherungen.
  Bestehende Symlinks auf reguläre, beschreibbare Dateien bleiben erhalten.
- Ungültige globale Git-Konfigurationen, kaputte Symlinks, Verzeichnisse statt
  Konfigurationsdateien und abweichende markierte Bash-Blöcke führen zum Abbruch
  vor Änderungen. Das Skript ist für aufeinanderfolgende, nicht gleichzeitige
  Ausführungen gedacht. Bei späteren Schreibfehlern kann es erneut gestartet werden.

Shell-Aliases: `ll`, `la`, `..`, `gs`, `gd`, `gl`.
Git-Aliases: `git st`, `git lg`, `git last`.
Neue Git-Defaults: Hauptbranch `main`, `fetch.prune=true`, `pull.ff=only`
(Pull bricht bei auseinanderlaufenden Branches ab) und `color.ui=auto`.

## Git-Unterstützung für Bash

Nach der Einrichtung werden in jedem neuen interaktiven Bash-Terminal automatisch
Git-Befehle, Optionen, Branches und Dateinamen mit der Tab-Taste vervollständigt.
Auch die hier definierten Aliase `gs`, `gd` und `gl` erhalten passende Completion,
sofern ihre Namen nicht bereits anders belegt sind.

Der Bash-Prompt zeigt den vollständigen Pfad, den Branch und den kurzen Commit-Hash.

```text
/workspaces/smartscale/retrofit on main [3588a1f] [dirty] [+4|-4] $
```

`[dirty]` zeigt lokale Änderungen einschließlich neuer Dateien an. `[+4|-4]`
bedeutet vier Commits vor und vier Commits hinter dem lokalen Upstream-Stand.
Bei Gleichstand oder ohne Upstream entfallen die Zähler. Bei einem Detached HEAD
erscheint `detached HEAD`, vor dem ersten Commit `no commit`.
Außerhalb eines Git-Repositorys zeigt der Prompt nur den Pfad und das Eingabezeichen.
Bestehende `PROMPT_COMMAND`-Hooks laufen weiter.
Vorhandene Git-Completions und Git-Prompts haben Vorrang. Erkannte Prompt-Manager
wie Starship, Oh My Posh, Powerline und Liquidprompt werden nicht ergänzt.
Ein bewusst leerer Prompt oder deaktiviertes Bash-`promptvars` bleiben erhalten.
Eigene Prompt-Hooks können `PS1` bei jedem Prompt neu aufbauen; in diesem Fall die
Git-Anzeige im vorhandenen Prompt-System konfigurieren.

Für die Git-Completion verwendet die Einrichtung vorhandene Helfer oder sucht
sie in üblichen Systempfaden. Als Fallback dient die mitgelieferte Completion
aus Git **v2.51.0**. Installation und Shell-Start benötigen
dadurch keine Downloads oder zusätzlichen Pakete. Quelle, Commit, Prüfsummen und
GPL-v2-Lizenz stehen unter [bash/vendor](bash/vendor/README.md).

Optionen bei Bedarf **vor** dem Dotfiles-Block in `~/.bashrc` setzen:

```bash
# Einzelne Funktionen deaktivieren:
DOTFILES_GIT_COMPLETION=0
DOTFILES_GIT_PROMPT=0

# Optional: mitgelieferte statt noch nicht geladener System-Helfer verwenden:
# DOTFILES_GIT_USE_BUNDLED=1

# Optional: Anzeige unversionierter Dateien deaktivieren (leerer Wert):
# GIT_PS1_SHOWUNTRACKEDFILES=
```

Ohne diese Optionen sind Completion und Prompt-Anzeige aktiv. Bereits gesetzte
`GIT_PS1_*`-Werte bleiben erhalten, auch leere Werte. Das erneute Laden der
Integration verdoppelt weder Completion-Einträge noch die Prompt-Anzeige.

## Aktualisieren und prüfen

Im Container:

```bash
git -C ~/dotfiles pull --ff-only
~/dotfiles/install.sh
bash -n ~/dotfiles/install.sh ~/dotfiles/bash/aliases.sh ~/dotfiles/bash/git.sh
git config --includes --get alias.st
```

Danach ein neues Bash-Terminal öffnen und dort `alias ll` und `alias gd` prüfen.
Aliase mit bereits belegten Namen werden ausgelassen, z. B. `gs` bei installiertem
Ghostscript.
Mit `complete -p git` die Completion prüfen. In einem Git-Verzeichnis sollten
`git switch <Tab>` Branches und der Prompt den aktuellen Branch anzeigen.
Bestehende Terminals laden neue Aliases nicht automatisch. Git-Werte werden
nicht mit der Vorlage synchronisiert: Bereits gesetzte Werte bleiben auch bei
späteren Änderungen der Vorlage erhalten. Gewünschte Anpassungen bewusst mit
`git config --global <Schlüssel> <Wert>` vornehmen.

Automatische Verifikation, auch auf dem Host ohne Änderung seiner Dotfiles:

```bash
python3 tests/test_install.py
```

Die Tests verwenden temporäre Benutzerverzeichnisse und prüfen Wiederholbarkeit,
vorhandene Einstellungen, Includes, XDG, Symlinks, Fehlerfälle sowie Pfade mit
Leerzeichen und Shell-Sonderzeichen. Zusätzliche Tests prüfen echte Branch-
Vervollständigung, Prompt-Status und den Erhalt eigener Prompt-/Completion-Regeln.

## Entfernen oder Checkout verschieben

Den Block zwischen `# >>> espressif-dotfiles >>>` und
`# <<< espressif-dotfiles <<<` aus `~/.bashrc` entfernen und ein neues Terminal
öffnen. Danach kann das Checkout verschoben und `install.sh` erneut ausgeführt
werden. Das Skript ersetzt einen vorhandenen Block mit einem anderen Pfad nicht
automatisch.

Ergänzte Git-Schlüssel bei Bedarf einzeln nach Prüfung entfernen, beispielsweise
mit `git config --global --unset alias.st`. Die Sicherungen enthalten den Zustand
vor der jeweiligen Änderung; eine vollständige Wiederherstellung würde auch
spätere eigene Anpassungen zurücknehmen. Es gibt deshalb keine automatische
Deinstallation. Zugangsdaten und persönliche Sicherungen nicht committen.
