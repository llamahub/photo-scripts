## Dev Container SSH Setup

The dev container is configured to use your host machine's SSH keys for connecting to remote servers (like your Immich server).

### How it works:

1. **SSH keys are mounted** from `~/.ssh` on your host to `/root/.ssh-host` in the container (read-only)
2. **Post-create script copies keys** to `/root/.ssh` with proper permissions
3. **SSH client** is installed via `setup-system-deps.sh`

### Initial Setup:

After rebuilding the container, your host SSH keys will be automatically available.

### Testing SSH Connection:

```bash
# Test connection to your server
ssh root@tigerserver

# Or with the script
. run fix_deleted --dry-run
```

### Troubleshooting:

**If SSH keys aren't working:**

1. **Check keys are mounted:**
   ```bash
   ls -la /root/.ssh-host
   ```

2. **Check keys copied correctly:**
   ```bash
   ls -la /root/.ssh
   ```

3. **Test SSH manually:**
   ```bash
   ssh -vvv root@tigerserver
   ```

4. **Add server to known_hosts:**
   ```bash
   ssh-keyscan tigerserver >> /root/.ssh/known_hosts
   ```

**If you don't have SSH keys on host:**

Generate them on your host machine first:
```bash
# On your host (Mac)
ssh-keygen -t ed25519 -C "your_email@example.com"

# Copy to server
ssh-copy-id root@tigerserver
```

### Rebuild Container:

After making changes to devcontainer.json:
- Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Linux/Windows)
- Select: "Dev Containers: Rebuild Container"
