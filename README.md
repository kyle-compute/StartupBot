# ELO Accountability Bot

Standard startup ecosystem is cringe and performative, this bot helps you engage in friendly competition with friends. 


## Core Concepts

### ELO Rating System

There's an ELO rating system

Essentially you use a command (In this case) `!challenge <category> <difficulty> <description>`
After you finish said challenge (With proof), your ELO increases and vice versa.

A leaderboard system is in place 

### Challenges
A challenge is a task defined by a user, assigned a category, and given a base difficulty rating. Other users can vote to adjust the difficulty before it becomes active. Once a challenge is completed, the user submits it for peer review.

### Sprints
Sprints are fixed-length seasons (e.g., weekly or bi-weekly) where users compete on a temporary leaderboard. This allows for regular resets, giving new users a chance to compete without having to overcome a large ELO gap. At the end of a sprint, winners are announced, and a new sprint begins.

## Command Reference

Commands are organized by function.

### General Commands

- `!help`: Displays a detailed list of all commands.
- `!guide`: Shows a simplified quick-start guide.

### Challenge Management

- `!challenge <category> <difficulty> <description>`: Issue a new challenge. The difficulty is an ELO value between 100 and 2000.
- `!challenges [status]`: List challenges. The status can be `active`, `pending_review`, `completed`, `failed`, or `rejected`.
- `!complete <id> <proof>`: Submit a completed challenge for peer review. The proof can be a link, text, or image URL.
- `!approve <id> [comment]`: Approve a completed challenge.
- `!reject <id> [reason]`: Reject a completed challenge.

### Statistics and Leaderboards

- `!leaderboard [period]`: View the leaderboard. The period can be `weekly` (for the current sprint) or `alltime`.
- `!profile [@user]`: View a user's statistics, including their ELO, challenge history, and completion rate.
- `!sprint status`: View the status of the current sprint, including the start date, end date, and time remaining.

### Categories

- `!categories`: List all available challenge categories.
- `!category add <name> [description]`: Create a new challenge category.
- `!category remove <name>`: Remove a category (Admin only).

### Administrative Commands

- `!sprint start|end`: Manually start or end a sprint cycle. (Admin only)
- `!config show`: Display the current server configuration for the bot. (Admin only)
- `!config set <key> <value>`: Set a configuration value. (Admin only)
- `!config channel review|voting #channel`: Set the channels for reviews and difficulty voting. (Admin only)

## Special Features

### Knowledge Management
The bot includes a prerequisite system to create links between messages, which is useful for tracking dependencies in technical discussions or project tasks.

- **Add Prerequisite**: Right-click on a Discord message and select `Apps > Add Prerequisite` to link it to another message.
- **View Prerequisites**: Right-click a message and select `Apps > View Prerequisites` to see its dependency chain.

### AI Conversation Summarization
You can instantly summarize a long conversation using Gemini.

- `!fromhere`: Reply to the message where you want the summary to begin. The bot will analyze the conversation from that point forward and provide a concise, bulleted summary of key topics, decisions, and action items.

## Setup and Installation

To run this bot, you will need Docker and Docker Compose.

1.  **Clone the Repository**
    ```sh
    git clone https://github.com/your-repo/discord-elo-bot.git
    cd discord-elo-bot
    ```

2.  **Configure Environment Variables**
    Copy the example environment file and fill in the required tokens and credentials.
    ```sh
    cp .env.example .env
    ```
    You will need to provide:
    - `DISCORD_BOT_TOKEN`: Your Discord bot's token.
    - `GEMINI_API_KEY`: Your Google AI Gemini API key for the summarization feature.
    - Database credentials (PostgreSQL).
    - Redis credentials.

3.  **Run the Bot**
    Use Docker Compose to build and run the bot and its database services in the background.
    ```sh
    docker-compose up --build -d
    ``` 
