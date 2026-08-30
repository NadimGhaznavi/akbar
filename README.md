# Akbar

An LLM on a modest GPU.

See [https://akbar.osoyalce.com](https://akbar.osoyalce.com)

## Installation

Install the Akbar application in `/opt/akbar`:

```sh
sudo python3 scripts/install.py
```

The installer first destroys any existing Akbar deployment and data. It then
creates the `akbar` service account, creates a virtual environment, provisions
an `akbar` MariaDB database and database account,
installs Python dependencies, and installs the model and experiment systemd
units. MariaDB server and
client must already be installed and running. It does not enable or start the
Akbar service unless requested:

```sh
sudo python3 scripts/install.py --enable --start
```

Use the trusted menu-driven experiment interface after installation:

```sh
/opt/akbar/scripts/akbar-cli.py
```

The CLI talks directly to the experiment service, displays only the final four
characters of experiment IDs, and provides DB-backed experiment counts and
completed results without language-model interpretation.

Use an alternate prefix without installing the systemd unit for testing:

```sh
python3 scripts/install.py \
    --prefix /tmp/akbar \
    --no-service \
    --skip-dependencies
```

## Upgrades

Upgrade from the current checkout and restart the services:

```sh
sudo python3 scripts/upgrade.py
```

Upgrade replaces the installed runtime and updates its dependencies and systemd
units. The MariaDB database, experiment records, database account, credentials,
virtual environment, service account, and service enablement state are
preserved.

## Uninstallation

Stop Akbar and permanently remove its application files, systemd units, service
account, MariaDB database, database account, and credentials:

```sh
sudo python3 scripts/uninstall.py
```

Uninstallation is always destructive. Back up anything you need beforehand.
