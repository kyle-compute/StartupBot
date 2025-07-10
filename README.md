# MLH Elobot

Competitive discord bot that gives community to founders who don't have a circle yet.

Create a weekly task, peers will vote on the difficulty. (You get to vote too!) 

The more technically challenging a task, the higher your rank will jump when you complete it (with proof, no larps allowed here...)


## Core Concept

Building alone sucks, many statup accelerators are performative. This provides a unified ecosystem without needing to deal with annoying narratives.

## Weekly Sprint Cycle

1. **Challenge Phase**: Users issue public challenges with custom categories and difficulty ratings
2. **Execution Phase**: Users work on their challenges throughout the week
3. **Proof & Review Phase**: Users submit proof of completion; peers review and vote
4. **Rating & Leaderboard Phase**: ELO calculations update rankings and leaderboards

## Game Commands

### Challenge Management
```
!challenge <category> <difficulty> <description>
```
Issue a new challenge with custom difficulty (100-2000 ELO)
- Example: `!challenge Backend 1300 Implement JWT authentication with refresh tokens`

```
!challenges [status]
```
List active, pending, completed, or failed challenges
- Example: `!challenges pending_review`

```
!complete <challenge_id> <proof_link_or_description>
```
Submit completed challenge for peer review
- Example: `!complete CHL-101 https://github.com/user/repo/pull/42`

### Peer Review System
```
!approve <challenge_id> [comment]
```
Approve a peer's challenge submission
- Example: `!approve CHL-101 Great implementation, clean code!`

```
!reject <challenge_id> [reason]
```
Reject a challenge submission
- Example: `!reject CHL-101 Missing test coverage`

### Categories & Configuration
```
!category add <name> [description]
```
Create custom challenge categories
- Example: `!category add "Machine Learning" "AI/ML projects and research"`

```
!categories
```
List all available challenge categories

### Leaderboards & Stats
```
!leaderboard [weekly|alltime]
```
View current sprint or all-time ELO rankings
- Aliases: `!lb`, `!lb weekly`, `!lb alltime`

```
!profile [@user]
```
View detailed user stats, ELO history, and recent challenges

```
!sprint status
```
Check current sprint information and remaining time

## Admin Commands

### Sprint Management
```
!sprint start    # Start new sprint cycle
!sprint end      # End current sprint
!sprint status   # Check sprint information
```

### Configuration
```
!config set <key> <value>
```
Configure ELO system parameters:
- `k_factor_new`: K-factor for new users (default: 40)
- `k_factor_stable`: K-factor for experienced users (default: 20)
- `approvals_needed`: Votes needed to approve challenges (default: 2)
- `sprint_duration_days`: Sprint length in days (default: 7)
- `stable_user_threshold`: Challenges needed to be "stable" (default: 10)

```
!config channel review #channel-name
```
Set dedicated channel for challenge reviews

```
!config show
```
Display current guild configuration

## ELO System

### How It Works
- **Starting ELO**: 1000 for all new users
- **Expected Score**: Calculated using standard ELO formula based on your rating vs challenge difficulty
- **Rating Changes**: Higher difficulty challenges = bigger ELO swings
- **K-Factor**: Determines rating volatility (high for new users, lower for experienced)

### Strategic Gameplay
- **Play It Safe**: Take challenges below your ELO for small, consistent gains
- **Take Risks**: Challenge yourself with high-difficulty tasks for massive ELO boosts (I reccomend this one)
- **Peer Pressure**: Community validates your work, maintaining quality standards

### Example ELO Scenarios
- **1000 ELO user** vs **800 difficulty**: Small gain if successful (~15 points)
- **1000 ELO user** vs **1400 difficulty**: Large gain if successful (~45 points)
- **1500 ELO user** vs **1200 difficulty**: Minimal gain (~8 points)

## Deployment Guide

### Prerequisites
1. Discord Developer Account
2. Docker and Docker Compose installed
3. Server with internet access (local machine, VPS, or cloud instance)

### Step-by-Step Deployment

#### Step 1: Create Discord Bot
1. Go to https://discord.com/developers/applications
2. Click "New Application" and give it a name
3. Navigate to "Bot" section in the left sidebar
4. Click "Add Bot"
5. Copy the bot token (keep this secure)
6. Under "Privileged Gateway Intents", enable:
   - Message Content Intent
   - Server Members Intent (optional)

#### Step 2: Set Bot Permissions
1. Go to "OAuth2" > "URL Generator"
2. Select "bot" scope
3. Select these bot permissions:
   - Send Messages
   - Read Message History
   - Use Slash Commands
   - Embed Links
   - Add Reactions
   - Manage Messages (optional)
4. Copy the generated URL and use it to invite the bot to your Discord server

#### Step 3: Download and Configure
```bash
# Clone or download the bot files
git clone <repository-url>
cd discordbot

# Create environment file
cp .env.example .env

# Edit .env file with your bot token
nano .env
```

Add your Discord bot token to the .env file:
```env
DISCORD_BOT_TOKEN=your_bot_token_here
POSTGRES_PASSWORD=choose_a_secure_password
```

#### Step 4: Deploy Options

**Option A: Local Deployment**
```bash
# Start the bot and database
docker-compose up -d

# Check if running
docker-compose ps

# View logs
docker-compose logs -f discord-bot
```

**Option B: VPS/Cloud Deployment**
```bash
# On your server (Ubuntu/Debian)
sudo apt update && sudo apt install docker.io docker-compose git

# Clone and deploy
git clone <repository-url> /opt/discord-bot
cd /opt/discord-bot
cp .env.example .env
nano .env  # Add your bot token

# Start services
docker-compose up -d

# Optional: Set up systemd service for auto-restart
sudo cp discord-bot.service /etc/systemd/system/
sudo systemctl enable discord-bot
sudo systemctl start discord-bot
```

**Option C: Digital Ocean (Automated)**
```bash
# Configure deployment script
nano deploy.sh
# Set DROPLET_IP to your server's IP address

# Run deployment
chmod +x deploy.sh
./deploy.sh
```

#### Step 5: Verify Deployment
1. Check bot is online in Discord (green status)
2. Test basic command: `!categories`
3. Create a test challenge: `!challenge Testing 1000 Test challenge`
4. Check logs: `docker-compose logs discord-bot`

### Network Configuration

**Local Hosting:**
- Bot runs on localhost, no port forwarding needed
- Discord connects to your bot via Discord's API
- Database runs internally in Docker network

**VPS/Cloud Hosting:**
- Ensure ports 80/443 are open for web traffic (optional)
- Docker handles internal networking
- No special firewall configuration needed for Discord bot

### Maintenance Commands

```bash
# Update bot
git pull && docker-compose up --build -d

# Restart services
docker-compose restart

# View database
docker-compose exec postgres psql -U botuser -d accountability

# Backup database
docker-compose exec postgres pg_dump -U botuser accountability > backup.sql

# View real-time logs
docker-compose logs -f
```

### Troubleshooting

**Bot not responding:**
```bash
# Check if containers are running
docker-compose ps

# Check bot logs
docker-compose logs discord-bot

# Verify token in .env file
cat .env | grep DISCORD_BOT_TOKEN
```

**Database connection errors:**
```bash
# Check PostgreSQL logs
docker-compose logs postgres

# Verify database password
cat .env | grep POSTGRES_PASSWORD
```

**Permission errors:**
- Verify bot has required permissions in Discord server
- Check OAuth2 URL generator settings
- Ensure bot role is above users it needs to interact with

### Security Notes

- Keep your Discord bot token secure and never commit it to version control
- Use a strong database password
- Regularly update the bot and dependencies
- Monitor logs for unusual activity
- Consider using environment variable management tools for production

### System Requirements

**Minimum:**
- 1 CPU core
- 512MB RAM
- 5GB storage
- Docker support

**Recommended:**
- 2 CPU cores
- 1GB RAM
- 10GB storage
- SSD storage for database performance

### Default Categories

The bot comes with these pre-configured challenge categories:
- **Backend**: Server-side development, databases, APIs
- **Frontend**: User interface, web development, mobile apps
- **DevOps**: Infrastructure, deployment, monitoring
- **Learning**: Acquiring new skills, studying, research
- **Refactoring**: Code improvement, optimization, cleanup
- **Testing**: Writing tests, debugging, quality assurance

## Database Schema

### Core Tables
- **users**: ELO ratings, challenge statistics
- **categories**: Guild-specific challenge categories  
- **challenges**: Challenge details, status, proof
- **sprints**: Weekly competition cycles
- **approvals**: Peer review votes
- **elo_history**: Rating change history
- **guild_config**: Server-specific settings

## Development

### Local Development
```bash
# Install Python dependencies
pip install -r requirements.txt

# Run without Docker (requires PostgreSQL)
python bot.py

# Run with Docker
docker-compose up --build
```

### Adding Features
1. Update database schema in `init.sql`
2. Add command functions to `bot.py`
3. Test locally with `docker-compose up`
4. Deploy with your chosen method

## Contributing

1. Fork the repository
2. Create a feature branch
3. Test thoroughly
4. Submit a pull request

## License

MIT License - Feel free to fork and customize for your community!