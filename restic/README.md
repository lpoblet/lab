# Restic Backup Template

Restic is a modern backup program that is fast, efficient, and secure. This section serves as a template and guide for setting up restic backups on Linux.

#### Security Best Practices

To avoid hardcoding passwords or exposing them in process lists/environment variables, we use `RESTIC_PASSWORD_FILE`.

*   **Credential Storage:** Store sensitive configuration in `/etc/restic/`.
    *   `*.repo.env`: Contains repository-specific environment variables (e.g., `RESTIC_REPOSITORY`).
    *   `*.repo.key`: Contains the repository password.
*   **Permissions:** 
    *   Ensure `.key` files are owned by the user running the backup and have `600` permissions.
    *   Ensure `.env` files are secured with `600` or `640` permissions.
*   **No Passwords in Repo:** Never commit password files or plain-text passwords to version control.

#### Configuration Strategy

For a clean and manageable setup, split backups into logical units:
1.  **Home Backup:** Focused on user data with specific exclusions (cache, downloads, etc.).
2.  **System Backup:** Focused on system configuration and binaries, excluding `/home`.

#### Automation

We use **systemd timers** for reliable, logged, and manageable backup schedules. This allows for:
*   Easy monitoring via `journalctl`.
*   Dependency management (e.g., ensuring a mount point is available).
*   Resource control (CPU/IO scheduling).

#### Retention Policy (Pruning)

Standard retention policy for this template:
*   Daily: 7
*   Weekly: 4
*   Monthly: 12

This ensures a good balance between history and storage usage.

#### Systemd Integration

To automate backups, we use a template-based systemd approach. This allows us to use the same service definition for different backup sets (e.g., `home`, `system`).

**1. Service Template (`restic-backup@.service`)**
Located in `restic/systemd/`. This service uses `EnvironmentFile` to load the repository configuration from `/etc/restic/%i.repo.env`. 
*Important:* The `ExecStart` command uses `--exclude-file=/etc/restic/%i.exclude`, so ensure an exclusion file exists (even if empty).

**2. Timer Template (`restic-backup@.timer`)**
Located in `restic/systemd/`. Controls when the backup runs. Default is daily.

**Example Setup for 'home':**
1.  Copy `restic/systemd/*.service` and `*.timer` to `/etc/systemd/system/`.
2.  Create `/etc/restic/home.repo.env` (use `restic/templates/repo.env.example` as guide).
3.  Create `/etc/restic/home.repo.key` (600 permissions).
4.  Create `/etc/restic/home.exclude` (use `restic/templates/home.exclude.example` as guide).
5.  Enable the timer: `systemctl enable --now restic-backup@home.timer`.

#### Manual Operations

Use the `restic/bin/restic-run` script to perform manual operations (like checking snapshots or restoring) using the same environment as the automated backups:

```bash
# List snapshots for the home repository
./restic/bin/restic-run home snapshots

# Manually trigger a backup for the system repository
./restic/bin/restic-run system backup / --exclude-file=/etc/restic/system.exclude
```

#### Implementation Details

All scripts and templates for this setup are located in the `restic/` directory of this repository.

*   `restic/bin/`: Wrapper scripts for restic commands.
*   `restic/systemd/`: Service and Timer unit files.
*   `restic/templates/`: Template `.env` and exclusion files.
