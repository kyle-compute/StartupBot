# MLH ELO Bot - Competitive Accountability

A Discord bot that turns productivity into a competitive game with a peer-reviewed ELO rating system. Issue challenges, submit proof, and climb the leaderboard. Features AI-powered summaries and prerequisite tracking for technical discussions.

## 🚀 Getting Started

1.  **Configure**: Copy `.env.example` to `.env` and fill in your tokens:
    ```bash
    cp .env.example .env
    ```
2.  **Run**:
    ```bash
    docker-compose up --build -d
    ```

---

## 🤖 Bot Commands

For a quick introduction, use `!guide` in your server. For a full list, use `!help`.

### Core Commands
*   `!challenge <cat> <diff> <desc>`: Issue a challenge.
*   `!complete <id> <proof>`: Submit your work for review.
*   `!approve <id>` / `!reject <id>`: Review a submission.
*   `!leaderboard`: View the rankings.
*   `!profile`: See your stats.

### Knowledge Management
*   **Right-click on a message** to use the new context menu commands:
    *   `Add Prerequisite`: Link the message to another as a prerequisite.
    *   `View Prerequisites`: Display the chain of prerequisites for a message.

### AI Summaries
*   `!fromhere`: Reply to a message to get an AI-powered summary of the conversation from that point.

---

## 📂 Project Structure

The bot uses a modular cog structure for easy extension. See `bot.py` for the entry point and `cogs/` for command modules. The database schema is in `init.sql`. 