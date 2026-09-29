# Setup details

The quick start is in the [README](../README.md#run-it-yourself). This page
covers the macOS mount workaround and running CI locally.

## If the Multipass mount fails (macOS)

If mounting reports privileged mounts are disabled:

```bash
multipass set local.privileged-mounts=true
multipass mount "$PWD" tradeops:/home/ubuntu/tradeops-watch
```

On the author's Mac (repository under `~/Desktop`), the mount was created but
reads failed with `Operation not permitted` because of macOS Desktop privacy
protection ([evidence](evidence/mount-permission-failure.txt)). The tested
fallback below copies the source into the VM without changing global privacy
permissions. Run it from the repository folder:

```bash
multipass umount tradeops:/home/ubuntu/tradeops-watch
COPYFILE_DISABLE=1 tar --exclude=.git --exclude=__pycache__ --exclude=.venv --exclude=.pytest_cache --exclude=.ruff_cache --exclude=.env --exclude=secrets --exclude=generated -czf /tmp/tradeops-watch-source.tar.gz .
multipass transfer /tmp/tradeops-watch-source.tar.gz tradeops:/home/ubuntu/tradeops-watch-source.tar.gz
multipass exec tradeops -- bash -lc 'mkdir -p /home/ubuntu/tradeops-watch && tar --no-same-owner -xzf /home/ubuntu/tradeops-watch-source.tar.gz -C /home/ubuntu/tradeops-watch'
multipass exec tradeops -- sudo bash /home/ubuntu/tradeops-watch/scripts/install.sh
```

Repeat the archive/transfer/extract steps after editing source on the Mac, then
rerun install. This is a copy, so VM evidence must also be copied back with
`multipass transfer`. If you prefer a live mount, grant Multipass access in
macOS System Settings → Privacy & Security → Full Disk Access, restart Multipass,
and retry mounting; that broader permission was not changed for this project.

Alternatively, clone the repository inside the VM at `/home/ubuntu/tradeops-watch`
and run the same installer there.

## Run CI locally inside the VM

```bash
cd /home/ubuntu/tradeops-watch
sudo apt-get install -y shellcheck
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
PATH="$PWD/.venv/bin:$PATH" bash scripts/ci_check.sh
```

The GitHub Actions workflow runs the same script on pushes and pull requests.
It validates shell/Python code, 39 Python test cases, Compose, ten alert rules,
eleven Prometheus rule cases, and Alertmanager configuration. Real chaos tests
stay outside ordinary CI because they require this disposable VM and
deliberately disrupt services. A saved local run is in
[step9-ci.txt](evidence/phase2/step9-ci.txt).

Credentials live only in ignored files; never commit `.env`, tokens or chat IDs.
