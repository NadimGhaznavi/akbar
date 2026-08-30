# Akbar

An LLM on a modest GPU.

See [https://akbar.osoyalce.com](https://akbar.osoyalce.com)

## Installation

Install the Akbar application in `/opt/akbar`:

```sh
sudo python3 scripts/install.py
```

By default, the installer creates the `akbar` service account, creates a virtual
environment, provisions an `akbar` MariaDB database and database account,
installs Python dependencies, and installs the model and experiment systemd
units. MariaDB server and
client must already be installed and running. It does not enable or start the
Akbar service unless requested:

```sh
sudo python3 scripts/install.py --enable --start
```

Use an alternate prefix without installing the systemd unit for testing:

```sh
python3 scripts/install.py \
    --prefix /tmp/akbar \
    --no-service \
    --skip-dependencies
```

## Updates

Reinstall the current checkout and restart the service:

```sh
sudo python3 scripts/reinstall.py
```

This replaces the installed application code, updates the virtual environment,
reinstalls both systemd units, and leaves their existing enablement state
unchanged.

## Uninstallation

Stop Akbar and remove its application files, systemd units, and service account:

```sh
sudo python3 scripts/uninstall.py
```

Database contents and credentials are retained by default. Remove them
explicitly when they are no longer needed:

```sh
sudo python3 scripts/uninstall.py --purge-data
```
