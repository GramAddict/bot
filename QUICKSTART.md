# GramAddict Plug & Play Quick Start 🚀

GramAddict is now **plug and play**! Get started in minutes with our interactive setup wizard.

## Prerequisites

- **Python 3.6+** installed (Python 3.10 currently not supported)
- **Android device or emulator** with Instagram app installed
- **USB cable** (for physical devices) or emulator running

## Installation

### Step 1: Install GramAddict

```bash
pip3 install GramAddict
```

### Step 2: Run the Setup Wizard

```bash
gramaddict setup
```

The wizard will guide you through:

1. **Python Version Check** - Verifies you have Python 3.6+
2. **ADB Setup** - Automatically downloads and configures Android Debug Bridge
3. **Device Detection** - Finds your connected Android device
4. **UIAutomator2 Setup** - Installs automation framework on your device
5. **Account Configuration** - Gets your Instagram username
6. **Bot Behavior Preset** - Choose your preferred automation level:
   - **Conservative** (Safest): 10-20 actions/hour, longer delays
   - **Balanced** (Recommended): 30-40 actions/hour, natural delays
   - **Aggressive** (Risky): 50-70 actions/hour, shorter delays
7. **Config Generation** - Creates optimized configuration files

### Step 3: Start the Bot

After setup completes, run:

```bash
gramaddict run --config accounts/yourusername/config.yml --interact @instagram
```

Replace `yourusername` with your actual Instagram username.

## Verify Your Setup

At any time, check if everything is working:

```bash
gramaddict health-check
```

This will verify:
- ✓ Python version
- ✓ Required packages installed
- ✓ ADB installed and accessible
- ✓ Device connected
- ✓ UIAutomator2 working
- ✓ Instagram app on device
- ✓ Config files present

## Configuration Presets

The setup wizard creates optimized configurations based on your chosen preset:

### Conservative (Safest)
```yaml
speed: 1
total_likes_limit: 50
total_follows_limit: 30
total_comments_limit: 15
```
Best for new accounts or maximum safety.

### Balanced (Recommended)
```yaml
speed: 2
total_likes_limit: 150
total_follows_limit: 100
total_comments_limit: 30
```
Good balance between growth and safety.

### Aggressive (Higher Risk)
```yaml
speed: 3
total_likes_limit: 300
total_follows_limit: 200
total_comments_limit: 50
```
Faster growth but higher detection risk. Not recommended for new accounts.

## Next Steps

### 1. Customize Your Bot (Optional)

Edit configuration files in `accounts/yourusername/`:
- `config.yml` - Main bot settings
- `filters.yml` - Profile filtering rules
- `comments_list.txt` - Comments to post
- `whitelist.txt` - Accounts to keep when unfollowing
- `blacklist.txt` - Accounts to skip

### 2. Add Interactions

The bot can interact with:

```bash
# Interact with a user's followers
gramaddict run --config accounts/yourusername/config.yml --interact @username

# Interact with hashtag likers
gramaddict run --config accounts/yourusername/config.yml --interact #hashtag

# Interact with place likers
gramaddict run --config accounts/yourusername/config.yml --interact place123456

# Multiple interactions
gramaddict run --config accounts/yourusername/config.yml \
  --interact @user1 @user2 #hashtag1 #hashtag2
```

### 3. Unfollow Non-Followers

```bash
# Unfollow people who don't follow back
gramaddict run --config accounts/yourusername/config.yml \
  --unfollow non-followers

# Unfollow all
gramaddict run --config accounts/yourusername/config.yml \
  --unfollow any
```

### 4. Enable Telegram Reports (Optional)

Get bot activity reports via Telegram:

1. Edit `accounts/yourusername/telegram.yml`
2. Add your bot token and chat ID
3. Follow [this guide](https://docs.gramaddict.org/#/configuration?id=telegram-reports)

## Troubleshooting

### Device Not Detected

1. Enable **USB Debugging** on your device:
   - Settings → About Phone → Tap "Build Number" 7 times
   - Settings → Developer Options → Enable USB Debugging

2. Accept the "Allow USB debugging" prompt on your device

3. Run `adb devices` to verify connection

### ADB Not Found

If automatic download fails:
1. Manually download [platform-tools](https://developer.android.com/studio/releases/platform-tools)
2. Extract to a permanent location
3. Add to PATH environment variable
4. Run `gramaddict setup` again

### UIAutomator2 Fails

```bash
# Manually initialize UIAutomator2
python3 -m uiautomator2 init
```

### Instagram Not in English

The bot requires Instagram to be in English:
1. Open Instagram app
2. Profile → Settings → Language
3. Select English

### Still Having Issues?

Run the health check to diagnose:
```bash
gramaddict health-check
```

Or join our [Discord community](https://discord.gg/NK8PNEFGFF) for help!

## Advanced Usage

### Multiple Accounts

Run setup for each account:
```bash
gramaddict setup  # Follow prompts for account1
gramaddict setup  # Follow prompts for account2
```

### Custom Config

For advanced users, skip the wizard:
```bash
gramaddict init yourusername
```
Then manually edit the config files.

### Schedule Bot Sessions

Use cron (Linux/Mac) or Task Scheduler (Windows) to automate:
```bash
# Example cron job (runs every 2 hours)
0 */2 * * * cd /path/to/gramaddict && gramaddict run --config accounts/user/config.yml
```

## Safety Tips

- ⚠️ Start with **Conservative** preset for new accounts
- ⚠️ Don't run 24/7 - act like a human!
- ⚠️ Gradually increase activity over time
- ⚠️ Use filters to target relevant accounts
- ⚠️ Monitor for action blocks or bans
- ⚠️ Never share your Instagram password

## What's Different from Manual Setup?

The plug-and-play wizard automates:
- ✓ ADB download and configuration
- ✓ PATH environment variable setup
- ✓ UIAutomator2 installation
- ✓ Config file generation with smart defaults
- ✓ Preset-based optimization

Old way: **7+ manual steps, 45-90 minutes**
New way: **2 commands, 5-15 minutes**

## Documentation

Full documentation: [docs.gramaddict.org](https://docs.gramaddict.org)

## Support

- [Discord Community](https://discord.gg/NK8PNEFGFF)
- [GitHub Issues](https://github.com/GramAddict/bot/issues)
- [Documentation](https://docs.gramaddict.org)

---

**Disclaimer**: This project comes with no guarantee or warranty. You are responsible for whatever happens from using this project. It is possible to get soft or hard banned by using this project if you are not careful.
