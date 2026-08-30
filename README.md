# Akbar

An LLM on a modest GPU.

See [https://akbar.osoyalce.com](https://akbar.osoyalce.com)

## Installation

Install the Akbar application in `/opt/akbar`:

```sh
sudo python3 scripts/install.py
```

By default, the installer creates the `akbar` service account, creates a virtual
environment, installs Python dependencies, and installs the systemd unit. It
does not enable or start the service unless requested:

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
and leaves the existing systemd enablement state unchanged.

## Uninstallation

Stop Akbar and remove its application files, systemd unit, and service account:

```sh
sudo python3 scripts/uninstall.py
```
