---
title: Installation
author_profile: true
layout: single
---

![Akbar]({{ '/pages/images/akbar.png' | relative_url }})

## Overview

Akbar is installed from a source checkout by a Python installer. A production
installation places the application in `/opt/akbar`, runs it as a dedicated
system account, and stores durable state in MariaDB.

The installer does not install the operating-system packages for Python,
MariaDB, `llama.cpp`, or the model itself. These must already be available, and
the MariaDB service must be running.

## Install Akbar

From the root of the Akbar source checkout, run:

```sh
sudo python3 scripts/install.py
```

Installation is destructive. Before creating the new deployment, it stops and
removes the existing services, installation tree, service account, MariaDB
database and account, and generated credentials. Existing experiment records
cannot be recovered unless they were backed up separately.

The installer then performs the following operations:

1. Creates the `akbar` system user and group when they do not exist.
2. Copies the Akbar runtime into `/opt/akbar`.
3. Creates `/opt/akbar/.venv` and installs the Python requirements.
4. Creates the `akbar` MariaDB database using `utf8mb4`.
5. Creates the `'akbar'@'localhost'` database account and grants it privileges
   only on `akbar.*`.
6. Generates and stores the database connection credentials.
7. Installs the Akbar model and experiment systemd services and reloads
   systemd.

Installation alone does not enable or start Akbar. To do both during
installation, run:

```sh
sudo python3 scripts/install.py --enable --start
```

## Installed files

The application and its virtual environment are installed under `/opt/akbar`:

```text
/opt/akbar/
├── .venv/
├── constants/
├── server/
├── requirements.txt
└── tools.py
```

The systemd units are installed separately:

```text
/etc/systemd/system/akbar.service
/etc/systemd/system/akbar-experimentd.service
```

## Database credentials

The generated database settings are stored in:

```text
/etc/akbar/database.env
```

The file contains the database host, port, name, user, and generated password.
It is owned by `root:akbar` with mode `0640`. The systemd unit loads it as an
environment file, so credentials are not stored in the source tree or embedded
in application code.

Every install generates a new database password.

## Update Akbar

Run the reinstall command from the updated source checkout:

```sh
sudo python3 scripts/reinstall.py
```

This invokes the same destructive installation path, then starts the recreated
services. It deletes the existing database, experiments, credentials, virtual
environment, application files, and service enablement state.

## Uninstall Akbar

To stop Akbar and permanently remove its application files, systemd units,
operating-system account, MariaDB database and account, and credentials, run:

```sh
sudo python3 scripts/uninstall.py
```

This operation is destructive and the removed database cannot be recovered
without a separate backup.

## Test installation

The application layout and virtual-environment creation can be tested without
root access, MariaDB provisioning, or systemd changes:

```sh
python3 scripts/install.py \
    --prefix /tmp/akbar \
    --no-service \
    --skip-dependencies
```

The alternate prefix is erased before the test installation is created.
