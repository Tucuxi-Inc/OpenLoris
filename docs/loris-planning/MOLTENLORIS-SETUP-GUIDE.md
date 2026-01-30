# MoltenLoris Setup Guide

**For End Users Setting Up Their Own MoltenLoris Instance**

This guide walks you through setting up MoltenLoris — an autonomous AI agent that monitors your Slack channels and answers questions using your organization's knowledge base.

---

## Overview

MoltenLoris runs in an isolated virtual machine on your computer. It:
- Monitors a Slack channel for questions
- Searches your knowledge files in Google Drive
- Answers questions it's confident about
- Escalates to human experts when uncertain
- Learns from expert responses over time

**Security Model:** MoltenLoris runs in complete isolation. It cannot access your host machine, and it only has access to the specific Slack channels and Google Drive folders you authorize via Zapier MCP.

---

## Prerequisites

Before you begin, you'll need:

1. **A Mac** running macOS 12 (Monterey) or later
2. **UTM** — Free virtual machine software for Mac ([download](https://mac.getutm.app/))
3. **A Zapier account** with MCP (Model Context Protocol) enabled
4. **Slack workspace access** — ability to create/manage apps
5. **Google Drive access** — to the `Loris-Knowledge` folder your team uses
6. **~2 hours** for initial setup

---

## Part 1: Create the Virtual Machine

### 1.1 Download and Install UTM

1. Go to [mac.getutm.app](https://mac.getutm.app/)
2. Download UTM
3. Move UTM to your Applications folder
4. Open UTM

### 1.2 Create a New VM

1. Click **"Create a New Virtual Machine"**
2. Select **"Virtualize"** (not Emulate)
3. Choose **"Linux"**
4. Download Ubuntu 24.04 LTS Desktop ISO from [ubuntu.com](https://ubuntu.com/download/desktop)
5. Select the downloaded ISO file
6. Configure the VM:
   - **Memory:** 8 GB (minimum 4 GB)
   - **CPU Cores:** 4 (minimum 2)
   - **Storage:** 40 GB
7. Name it **"MoltenLoris"**
8. Click **"Save"**

### 1.3 Install Ubuntu

1. Start the VM
2. Select **"Try or Install Ubuntu"**
3. Follow the installation wizard:
   - Language: English
   - Keyboard: Your preference
   - Installation type: Erase disk and install (this is the VM's virtual disk, not your Mac)
   - Your name: `moltenloris`
   - Computer name: `moltenloris-vm`
   - Username: `loris`
   - Password: Choose a secure password
4. Wait for installation to complete (~15 minutes)
5. Restart when prompted
6. Eject the ISO (UTM menu → CD/DVD → Eject)

### 1.4 Update the System

Open Terminal in the VM and run:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git python3-pip
```

---

## Part 2: Set Up Zapier MCP

Zapier MCP provides secure, limited access to external services. MoltenLoris will use it to read/write Slack and read Google Drive.

### 2.1 Create Zapier MCP Connection

1. Go to [zapier.com](https://zapier.com) and log in
2. Navigate to **MCP** (Model Context Protocol) settings
3. Click **"Create New MCP Server"**
4. Name it: `MoltenLoris-[YourTeam]`

### 2.2 Add Slack Tools

Add the following Slack tools to your MCP server:

#### Tool 1: Read Channel Messages
```yaml
Name: slack_read_channel
Service: Slack
Action: Find Messages
Configuration:
  - Channel: [Select your questions channel, e.g., #legal-questions]
  - Limit: 100
  - Include thread replies: No
Permissions: READ ONLY
```

#### Tool 2: Read Thread
```yaml
Name: slack_read_thread
Service: Slack
Action: Get Thread Replies
Configuration:
  - Channel: [Same channel]
Permissions: READ ONLY
```

#### Tool 3: Post Message
```yaml
Name: slack_post_message
Service: Slack
Action: Send Channel Message
Configuration:
  - Channel: [Same channel]
  - As Bot: Yes
  - Bot Name: MoltenLoris
  - Bot Icon: 🦥 (or upload custom icon)
Permissions: WRITE (to specified channel only)
```

#### Tool 4: Add Reaction
```yaml
Name: slack_add_reaction
Service: Slack
Action: Add Reaction to Message
Configuration:
  - Channel: [Same channel]
Permissions: WRITE (reactions only)
```

### 2.3 Add Google Drive Tools

Add these Google Drive tools:

#### Tool 1: List Files
```yaml
Name: gdrive_list_files
Service: Google Drive
Action: Find Files in Folder
Configuration:
  - Folder: /Loris-Knowledge
  - File Types: .md, .txt
Permissions: READ ONLY
```

#### Tool 2: Read File
```yaml
Name: gdrive_read_file
Service: Google Drive
Action: Get File Contents
Configuration:
  - Folder: /Loris-Knowledge (and subfolders)
Permissions: READ ONLY
```

**Important:** MoltenLoris should have READ-ONLY access to Google Drive. The Loris Web App handles writing knowledge files.

### 2.4 Get Your MCP Connection String

1. In Zapier MCP, click **"Get Connection String"**
2. Copy the connection string — it looks like:
   ```
   https://mcp.zapier.com/v1/servers/abc123xyz?token=your-secret-token
   ```
3. **Keep this secret!** It grants access to your configured tools.

---

## Part 3: Install Moltbot

Moltbot is the AI agent runtime that will become MoltenLoris.

### 3.1 Install Moltbot in the VM

Open Terminal in your Ubuntu VM and run:

```bash
# Install Moltbot
curl -fsSL https://moltbot.ai/install.sh | bash

# Verify installation
moltbot --version
```

### 3.2 Configure MCP Connection

```bash
# Create config directory
mkdir -p ~/.moltbot

# Add your Zapier MCP connection
moltbot config set mcp.url "https://mcp.zapier.com/v1/servers/abc123xyz"
moltbot config set mcp.token "your-secret-token"

# Test the connection
moltbot mcp test
```

You should see output like:
```
✓ Connected to MCP server
✓ Found 6 tools:
  - slack_read_channel
  - slack_read_thread
  - slack_post_message
  - slack_add_reaction
  - gdrive_list_files
  - gdrive_read_file
```

---

## Part 4: Create the SOUL.md Configuration

The SOUL.md file defines MoltenLoris's personality, behavior, and rules.

### 4.1 Create the Configuration File

```bash
nano ~/.moltbot/SOUL.md
```

### 4.2 Paste and Customize This Template

```markdown
# MoltenLoris SOUL Configuration

## Identity

name: MoltenLoris
role: [Your Department] Knowledge Assistant
organization: [Your Company Name]

## Communication Style

- Professional but approachable
- Concise answers (2-3 paragraphs max)
- Always cite sources
- Transparent about confidence levels

## Channels

### Monitor
channel: #[your-channel-name]
check_frequency: every 5 minutes

### Escalation Contacts
primary_expert: @[expert-slack-handle]
backup_expert: @[backup-slack-handle]

## Knowledge Sources

### Google Drive (Primary)
folder: /Loris-Knowledge
file_types: .md, .txt

## Confidence Thresholds

| Level | Threshold | Action |
|-------|-----------|--------|
| HIGH | ≥75% | Post answer, mark 🤖 |
| MEDIUM | 50-74% | Post tentative + tag expert, mark 🔶 |
| LOW | <50% | Escalate only, mark 🔴 |

## Response Templates

### High Confidence
```
Based on our knowledge base:

[Answer]

───────────────────────────
📚 Source: [filename]
🎯 Confidence: [X]%
───────────────────────────

Was this helpful? React with ✅ or ❌
```

### Medium Confidence
```
I found relevant information, but I'm not fully confident:

[Answer]

───────────────────────────
⚠️ Confidence: [X]% — An expert should verify.
───────────────────────────

@[expert] — Could you verify this?
```

### Low Confidence / Escalation
```
I don't have enough information for this one.

I've notified @[expert] to help.

───────────────────────────
🔍 Searched: [terms]
📊 Best match: [X]%
───────────────────────────
```

## Behavior Rules

### Always
- Mark messages with 👀 when detected
- Search all knowledge files before responding
- Include confidence percentage
- Cite sources by filename
- Offer escalation option

### Never
- Respond to bots (including yourself)
- Make up information
- Process the same message twice
- Answer questions outside your knowledge domain

## Message Processing

Skip if:
- Already has 👀, 🤖, 🔶, or 🔴 reaction
- From a bot
- Is a thread reply (only process top-level)
- Older than 1 hour

## Schedule

check_slack: every 5 minutes
```

Save the file: `Ctrl+O`, then `Enter`, then `Ctrl+X`

### 4.3 Customize for Your Organization

Replace these placeholders:
- `[Your Department]` → e.g., "Legal", "HR", "IT"
- `[Your Company Name]` → e.g., "Acme Corp"
- `[your-channel-name]` → e.g., "legal-questions"
- `[expert-slack-handle]` → e.g., "sarah.chen"
- `[backup-slack-handle]` → e.g., "bob.smith"

---

## Part 5: Start MoltenLoris

### 5.1 Test Mode First

Run MoltenLoris in test mode to verify everything works:

```bash
moltbot run --soul ~/.moltbot/SOUL.md --test
```

This will:
- Connect to Slack (read-only)
- Show what messages it would process
- Show what responses it would send
- **Not actually post anything**

### 5.2 Post a Test Question

In your Slack channel, post:
```
@channel Test question for MoltenLoris: What is our standard NDA confidentiality period?
```

In the VM terminal, you should see:
```
[TEST] Would process message: "What is our standard NDA confidentiality period?"
[TEST] Searching knowledge files...
[TEST] Found match in NDA-Guidelines.md (similarity: 0.87)
[TEST] Would post HIGH confidence answer
[TEST] Would add reaction: 🤖
```

### 5.3 Go Live

If the test looks good, start MoltenLoris for real:

```bash
moltbot run --soul ~/.moltbot/SOUL.md
```

You should see:
```
🦥 MoltenLoris is now active
   Monitoring: #legal-questions
   Check interval: 5 minutes
   Knowledge source: /Loris-Knowledge (6 files)
   
Press Ctrl+C to stop
```

### 5.4 Run as Background Service

To keep MoltenLoris running even when you close the terminal:

```bash
# Create a systemd service
sudo nano /etc/systemd/system/moltenloris.service
```

Paste:
```ini
[Unit]
Description=MoltenLoris Slack Agent
After=network.target

[Service]
Type=simple
User=loris
ExecStart=/usr/local/bin/moltbot run --soul /home/loris/.moltbot/SOUL.md
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable moltenloris
sudo systemctl start moltenloris

# Check status
sudo systemctl status moltenloris

# View logs
journalctl -u moltenloris -f
```

---

## Part 6: Verify It's Working

### 6.1 Post a Real Question

In your Slack channel:
```
What's the standard term for vendor contracts?
```

Within 5 minutes, MoltenLoris should:
1. React with 👀 (seen)
2. Search knowledge files
3. Post an answer (or escalate)
4. React with 🤖, 🔶, or 🔴

### 6.2 Test Escalation

Post a question MoltenLoris won't know:
```
What was decided in last week's board meeting?
```

MoltenLoris should:
1. React with 👀
2. Search and find low confidence
3. Post escalation message
4. Tag your expert
5. React with 🔴

### 6.3 Monitor the Logs

```bash
journalctl -u moltenloris -f
```

You'll see:
```
[2026-01-28 14:32:15] Checking #legal-questions...
[2026-01-28 14:32:16] Found 1 new message
[2026-01-28 14:32:16] Processing: "What's the standard term for vendor contracts?"
[2026-01-28 14:32:17] Searching 6 knowledge files...
[2026-01-28 14:32:18] Best match: Contracts.md (similarity: 0.91)
[2026-01-28 14:32:18] Confidence: 85% (HIGH)
[2026-01-28 14:32:19] Posted answer, added 🤖 reaction
[2026-01-28 14:37:15] Checking #legal-questions...
[2026-01-28 14:37:16] No new messages
```

---

## Part 7: Maintenance

### 7.1 Updating Knowledge

MoltenLoris reads from Google Drive's `/Loris-Knowledge` folder. When your Loris Web App exports new knowledge:
- Files are automatically available to MoltenLoris
- No restart needed
- Changes take effect on next check (within 5 minutes)

### 7.2 Stopping MoltenLoris

```bash
# If running in terminal
Ctrl+C

# If running as service
sudo systemctl stop moltenloris
```

### 7.3 Restarting After Config Changes

```bash
sudo systemctl restart moltenloris
```

### 7.4 Updating Moltbot

```bash
# Stop the service
sudo systemctl stop moltenloris

# Update
moltbot update

# Restart
sudo systemctl start moltenloris
```

### 7.5 VM Maintenance

Periodically update Ubuntu:
```bash
sudo apt update && sudo apt upgrade -y
```

---

## Troubleshooting

### MoltenLoris isn't responding

1. **Check it's running:**
   ```bash
   sudo systemctl status moltenloris
   ```

2. **Check the logs:**
   ```bash
   journalctl -u moltenloris --since "10 minutes ago"
   ```

3. **Test MCP connection:**
   ```bash
   moltbot mcp test
   ```

### "Permission denied" errors

Your Zapier MCP tools may not have the right permissions. Check:
- Slack tool has access to the correct channel
- Google Drive tool has access to `/Loris-Knowledge`

### MoltenLoris answers incorrectly

1. Check the knowledge files in Google Drive
2. The source file may be outdated or incorrect
3. Report to your Loris admin so they can update the knowledge base

### High confidence but wrong answer

This means the knowledge file matched but contained incorrect information. Flag this to your Loris admin — they need to correct the source file.

### VM runs slowly

- Increase RAM: UTM → Settings → Memory → 8GB+
- Increase CPU: UTM → Settings → CPU → 4+ cores
- Close other applications on your Mac

---

## Security Best Practices

1. **Keep the VM isolated** — Don't share files between the VM and your Mac
2. **Protect your MCP token** — It's stored in `~/.moltbot/config` inside the VM
3. **Limit Slack permissions** — Only give MoltenLoris access to specific channels
4. **Read-only Google Drive** — MoltenLoris should never write to Drive
5. **Regular updates** — Keep Ubuntu and Moltbot updated
6. **Monitor logs** — Periodically review what MoltenLoris is doing

---

## Getting Help

- **MoltenLoris issues:** Check logs first, then contact your Loris admin
- **Moltbot issues:** [moltbot.ai/docs](https://moltbot.ai/docs)
- **Zapier MCP issues:** [zapier.com/help](https://zapier.com/help)
- **VM issues:** [docs.getutm.app](https://docs.getutm.app)

---

## Quick Reference

| Task | Command |
|------|---------|
| Start MoltenLoris | `sudo systemctl start moltenloris` |
| Stop MoltenLoris | `sudo systemctl stop moltenloris` |
| Restart MoltenLoris | `sudo systemctl restart moltenloris` |
| Check status | `sudo systemctl status moltenloris` |
| View logs | `journalctl -u moltenloris -f` |
| Test MCP connection | `moltbot mcp test` |
| Edit configuration | `nano ~/.moltbot/SOUL.md` |
| Test mode (no posting) | `moltbot run --soul ~/.moltbot/SOUL.md --test` |

---

*Last updated: January 2026*
*Part of the Loris Knowledge Platform*
