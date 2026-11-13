# LPIC-1 Practice Environment

Docker Compose setup for practicing Linux administration skills toward the [LPIC-1 certification](https://www.lpic.org/).

Six Linux distributions run simultaneously on a shared Docker network, each with your dotfiles and scripts mounted for live practice.

## Distributions Included

| Service | Image | Package Manager | Special Tools |
|---|---|---|---|
| `debian` | Debian 12 | `apt` | — |
| `ubuntu` | Ubuntu 24.04 LTS | `apt` | — |
| `fedora` | Fedora 41 | `dnf` | — |
| `arch` | Arch Linux | `pacman` | Rolling release |
| `opensuse` | openSUSE Tumbleweed | `zypper` | YaST (yast2) |
| `alpine` | Alpine 3.21 | `apk` | musl libc, busybox |

## Quick Start

```bash
# Navigate to the docker directory
cd scripts/docker

# (Optional) Customize settings
cp .env.example .env
# Edit .env to change UID, GID, dotfiles repo, or SSH ports

# Build and start all distros (containers stay alive in the background)
docker compose up -d --build

# Enter any container
docker compose exec debian bash
docker compose exec ubuntu bash
docker compose exec fedora bash
docker compose exec arch bash
docker compose exec opensuse bash
docker compose exec alpine bash
```

## What's Inside Each Container

Every container comes pre-installed with tools covering all LPIC-1 objectives:

| LPIC-1 Objective | Tools & Practice |
|---|---|
| **100-101** Linux Installation & Hardware | `curl`, `wget`, `gpg` |
| **100-103** Shells | `bash`, `vim`, `less`, `tree`, `jq` |
| **100-104** FS & Disk Management | `e2fsprogs`, `fdisk`, `lvm2`, `util-linux` |
| **100-105** Users & Groups | `sudo`, user/group management commands |
| **100-106** Applications | `apt` / `dnf` / `zypper` (per distro) |
| **100-107** Networking | `iproute2`, `ping`, `net-tools`, `dnsutils`, `nmap` |
| **100-108** System Startup & Boot | `systemd`, `systemctl` |
| **100-109** Dev Basics | `gcc`, `make`, `git` |
| **100-110** Security | `procps`, `sysstat`, `htop`, `strace`, `ltrace` |

Plus: `tar`, `gzip`, `bzip2`, `xz`, `zip`, `unzip`, `cron`, `openssh-server`, `man` (man pages).

The openSUSE container additionally includes **YaST** modules (`yast2`, `yast2-network`, `yast2-users`, `yast2-firewall`) for practicing SUSE-specific administration.

The Alpine container uses **musl libc** and **busybox** instead of glibc/coreutils — useful for understanding minimal Linux environments and how commands differ from standard distributions.

## Your Environment

- **User**: `student` (UID 1000, passwordless sudo)
- **Dotfiles**: Cloned from your repo at `/home/student/.dotfiles`
- **Scripts**: Your scripts repo is mounted at `/home/student/scripts` (read-only, live updates)
- **Persistent Home**: Each distro has its own Docker volume for the home directory
- **Shared Network**: All containers are on `lpic1-network` — they can reach each other by hostname

## Common Commands

```bash
# Start all distros (containers stay alive via `sleep infinity`)
docker compose up -d

# Start a single distro
docker compose up -d debian

# Enter a running container
docker compose exec fedora bash

# Check container status
docker compose ps

# Stop all containers
docker compose down

# Stop and remove all volumes (resets all home directories)
docker compose down -v

# Rebuild a specific image
docker compose build --no-cache ubuntu

# View logs for a specific container
docker compose logs -f opensuse
```

## Cross-Container Networking

All containers share the `lpic1-network` bridge. You can practice networking between distros:

```bash
# From inside any container, ping another
ping debian-practice
ping ubuntu-practice
ping fedora-practice
ping arch-practice
ping opensuse-practice
ping alpine-practice
```

## SSH Practice

Each container exposes SSH on a different host port:

| Distro | Host Port |
|---|---|
| Debian | 2222 |
| Ubuntu | 2223 |
| Fedora | 2224 |
| Arch | 2225 |
| openSUSE | 2226 |
| Alpine | 2227 |

```bash
# Inside any container, start the SSH service
sudo service ssh start

# From your host, connect via SSH
ssh student@localhost -p 2222   # Debian
ssh student@localhost -p 2224   # Fedora
ssh student@localhost -p 2225   # Arch
ssh student@localhost -p 2227   # Alpine
# Password: (none — use sudo or set one with 'passwd')
```

## Systemd Practice

By default, containers keep running via `sleep infinity` so you can attach with `docker compose exec`. To practice with systemd services, override the command:

```bash
# Start Debian with systemd as PID 1
docker compose run --rm debian /lib/systemd/systemd &
docker compose exec debian bash
```

## Package Manager Comparison

Practice with five different package manager families:

```bash
# apt (Debian/Ubuntu)
sudo apt update && sudo apt install htop

# dnf (Fedora)
sudo dnf install htop

# pacman (Arch)
sudo pacman -S --noconfirm htop

# zypper (openSUSE)
sudo zypper install htop

# apk (Alpine)
sudo apk add htop
```

## Tmux Workflow

The containers are designed to stay alive in the background, making them ideal for tmux multi-pane workflows:

```bash
# Start all containers in the background
docker compose up -d

# In tmux, create panes for each distro:
tmux new-session -d -s lpic1
tmux split-window -h -t lpic1
tmux split-window -v -t lpic1:0
tmux split-window -v -t lpic1:1
tmux split-window -v -t lpic1:2

# Attach each pane to a different distro
tmux send-keys -t lpic1:0 'docker compose exec debian bash' C-m
tmux send-keys -t lpic1:1 'docker compose exec ubuntu bash' C-m
tmux send-keys -t lpic1:2 'docker compose exec fedora bash' C-m
tmux send-keys -t lpic1:3 'docker compose exec arch bash' C-m
tmux send-keys -t lpic1:4 'docker compose exec opensuse bash' C-m
tmux send-keys -t lpic1:5 'docker compose exec alpine bash' C-m

# Join the session
tmux attach -t lpic1
```

Or simply open six terminal windows/tabs and run `docker compose exec <distro> bash` in each.

## Notes

- Containers run `sleep infinity` as their main process to stay alive — use `docker compose exec` to get an interactive shell.
- Containers run in `privileged` mode to allow disk partitioning, LVM, and systemd practice.
- Scripts are mounted read-only — edit on the host and changes appear instantly in all containers.
- Each distro has its own persistent home volume. Remove a specific volume with `docker volume rm lpic1_<distro>-home`.
