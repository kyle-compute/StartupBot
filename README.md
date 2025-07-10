# MLH ELO Bot - Competitive Accountability

This Discord bot transforms team productivity and personal accountability into a competitive game using a peer-reviewed ELO rating system. Users issue challenges, the community votes on their difficulty, and members earn ELO by submitting proof of their completed work. It's designed for developers, founders, and students who want a fun, collaborative way to stay motivated and build in public.

![image](https://github.com/user-attachments/assets/81c8159c-735c-4861-829d-48d68407481f)

## Core Features

- **ELO-Based Task Rating**: Assign a difficulty (100-2000 ELO) to each challenge.
- **Community-Driven Difficulty Voting**: Peers can vote to adjust the ELO of a challenge before it starts.
- **Proof of Work & Peer Review**: Users submit proof of completion, and peers approve or reject it.
- **Weekly Sprints**: Compete on a weekly leaderboard for ELO gains.
- **AI-Powered Summaries**: Use the `!fromhere` command to get Gemini-powered summaries of your conversations.
- **Flexible & Configurable**: Admins can customize categories, ELO parameters, and dedicated channels.

---

## 🚀 Getting Started with Docker

The easiest way to get the bot running is with Docker Compose.

### 1. Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) installed.
- A Discord Bot Token. You can get one from the [Discord Developer Portal](https://discord.com/developers/applications).
- A Gemini API Key from [Google AI Studio](https://aistudio.google.com/app/apikey) for the `!fromhere` command.

### 2. Configuration

**Create an Environment File:**  
Create a file named `.env` in the root of the project directory. This file will store your secret keys.

```env
# .env

# Your Discord bot token from the developer portal
DISCORD_BOT_TOKEN=your_discord_bot_token_here

# Your Gemini API key for AI features
GEMINI_API_KEY=your_gemini_api_key_here

# Secure password for the PostgreSQL database user
POSTGRES_PASSWORD=a_very_strong_and_secret_password
```

### 3. Running the Bot

Once your `.env` file is configured, you can start the bot and the database with a single command:

```bash
docker-compose up --build -d
```

- `--build` rebuilds the image if there are any changes to the `Dockerfile`.
- `-d` runs the containers in detached mode (in the background).

To view the logs for the bot container:

```bash
docker-compose logs -f discord-bot
```

### 4. Stopping the Services

To stop the bot and database containers:

```bash
docker-compose down
```

---

## 🤖 Bot Commands

### Getting Started

-   `!guide` - Shows a comprehensive tutorial and command reference.
-   `!categories` - Lists all available challenge categories.

### Challenge Management

-   `!challenge <category> <difficulty> <description>` - Issues a new challenge (e.g., `!challenge Backend 1200 Build REST API`).
-   `!challenges [status]` - Lists challenges by status (active, pending\_review, completed, etc.).
-   `!complete <id> <proof>` - Submits a challenge for review with a link or description.
-   `!approve <id> [comment]` - Approves a peer's submission.
-   `!reject <id> [reason]` - Rejects a peer's submission.

### AI Features

-   `!fromhere` - (As a reply to a message) Generates an AI summary of the conversation from that point onward.

### Stats & Leaderboards

-   `!leaderboard` or `!lb` - Shows the weekly sprint leaderboard.
-   `!leaderboard alltime` - Shows the all-time ELO rankings.
-   `!profile [@user]` - Shows detailed stats for you or another user.
-   `!sprint status` - Displays the current sprint's status and time remaining.

### Admin Commands

-   `!category add <name> [desc]` - Creates a new challenge category.
-   `!category remove <name>` - Deletes a category.
-   `!sprint start|end` - Manually starts or ends a sprint cycle.
-   `!config show` - Displays all server configurations.
-   `!config set <key> <value>` - Sets a configuration value (e.g., `approvals_needed`).
-   `!config channel <review|voting> #channel` - Sets the dedicated channels for reviews and voting.

---

## 📂 Project Structure

This bot is organized into a modular structure using Discord.py Cogs for better readability and maintainability.

```
.
├── 📄 .env                  # Environment variables (you create this)
├── 📄 bot.py                 # Main bot entry point, loads cogs and handles events
├── 📄 docker-compose.yml      # Defines services, networks, and volumes for Docker
├── 📄 Dockerfile              # Instructions to build the bot's Docker image
├── 📄 init.sql                # Initial database schema
├── 📄 requirements.txt        # Python dependencies
├── 📁 cogs/                   # Houses all command modules (cogs)
│   ├── 📄 ai.py
│   ├── 📄 categories.py
│   └── ... (and so on)
└── 📁 utils/                  # Shared utilities
    ├── 📄 db.py               # Database manager
    ├── 📄 elo.py              # ELO calculation engine
    └── 📄 ui.py               # Discord UI elements (e.g., buttons, views)
```

## ELO System Explained

-   **Starting ELO**: All users begin at 1000.
-   **Risk vs. Reward**: Higher difficulty challenges offer greater ELO gains but also greater losses.
-   **K-Factor**: A dynamic value that determines the volatility of ELO changes. It's higher for new users to help them find their rank faster and lower for established users.
-   **Peer Review**: The community validates work, ensuring quality and preventing gaming the system.
-   **Difficulty Voting**: Before a challenge is finalized, the community can vote to adjust its difficulty rating, ensuring a fair assessment. 