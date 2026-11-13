#!/bin/bash
set -euo pipefail

STUDENT_HOME="/home/student"
DOTFILES_SRC="/opt/dotfiles"
DOTFILES_DST="$STUDENT_HOME/.dotfiles"

# Copy dotfiles into the persistent volume if not already present
if [[ ! -d "$DOTFILES_DST" ]]; then
    cp -a "$DOTFILES_SRC" "$DOTFILES_DST"
fi

# Execute the requested command
exec "$@"
