# 🎮 Marble - Multi-Game Discord Bot

<!-- 🔧 CUSTOMIZATION: Add your personal badges here -->
<!-- Example: [![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/) -->
<!-- Example: [![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE) -->

A feature-rich Discord bot for gaming communities that integrates with **League of Legends** and **Valorant** APIs to provide match analysis, player statistics, trivia games, and voice activity tracking.

<!-- 🔧 CUSTOMIZATION: Add a GIF/screenshot of your bot in action here -->
<!-- ![Marble Bot Demo](path/to/demo.gif) -->

## 🌟 Overview

Marble is a production-ready Discord bot designed to enhance gaming community experiences through automated match analysis, interactive games, and engagement tracking. Built with Python and discord.py, it demonstrates proficiency in:

- **RESTful API Integration** (Riot Games API, Henrik Valorant API)
- **Asynchronous Programming** (asyncio, event-driven architecture)
- **Data Persistence** (JSON-based storage with concurrent access management)
- **Object-Oriented Design** (modular cog system, class hierarchies)
- **Statistical Analysis** (Z-score calculations, performance metrics)

<!-- 🔧 CUSTOMIZATION: Update the server count and stats if you have them -->
**Current Status:** Active in production | Serving 1+ Discord server <!-- Update with your actual stats -->

---

## ✨ Key Features

### 🎯 League of Legends Integration

#### **Blame Analysis System**
Analyzes match performance to identify underperforming players using a custom "INT Score" algorithm:
- Multi-factor performance scoring (KDA, vision, gold, damage, kill participation)
- Position-specific baselines and weighted metrics
- Solo queue vs. team queue analysis modes
- Automatically fetches recent match history via Riot API

```bash
# Example commands
!blame 5 flex          # Analyze last 5 flex queue losses
!register RiotName#TAG # Link Discord to Riot account
```

**Technical Highlights:**
- Implements inverse hyperbolic functions for performance normalization
- Handles API rate limiting and error recovery
- Supports dynamic player pool management

#### **Champion Trivia Game**
Interactive quiz game with 170+ League champions:
- Three difficulty modes (Ults Only, Abilities, Anything Goes)
- Real-time leaderboard tracking with persistent storage
- Fuzzy matching with champion alias system
- Timeout handling and graceful error management

### 🎯 Valorant Integration

#### **Match Report System**
Automated post-match analysis with custom title assignments:
- **Advanced Statistics Tracking:** 30+ performance metrics per player
- **Dynamic Title Assignment:** Z-score based algorithm assigns unique titles
  - Calculates statistical significance across 20+ categories
  - Weighted random selection for competitive titles
  - Fallback handling for edge cases
- **Rich Embeds:** Formatted match summaries with embedded map images
- **Team Performance Analysis:** Round-by-round breakdowns, clutch detection

**Algorithm Showcase:**
```python
# Z-score normalization with custom weighting
z_weighted = ((stat - mean) / std_dev) * weight
```

### 📊 Voice Activity Tracking
Monitors and analyzes Discord voice channel usage:
- Real-time presence tracking with state machine
- Daily/weekly activity summaries
- Concurrent data access with async locks
- Automatic cleanup of old records (configurable retention)
- Background tasks with graceful shutdown handling

---

## 🏗️ Architecture

### Project Structure
```
Marble/
├── bot.py                      # Main entry point, event loop
├── config.py                   # Centralized configuration
├── helpers.py                  # League of Legends API utilities
├── match_score_calculator.py   # INT score algorithm
├── refresh_lol_data.py         # Champion data updater
│
├── cogs/                       # Modular feature systems
│   ├── activity.py            # Voice tracking (500+ LOC)
│   ├── blamer.py              # LoL blame analysis
│   ├── games.py               # Trivia game system
│   └── titles.py              # Valorant match reports (700+ LOC)
│
├── data/                       # Runtime persistence
│   ├── voicePresences.json    # Voice activity history
│   ├── players.json           # User registrations
│   └── loltriviaLeaderboards.json
│
└── static/                     # Reference data
    ├── championFull.json      # Champion metadata (auto-updated)
    ├── championAliases.json   # Fuzzy matching data
    └── titles.json            # Valorant title definitions
```

### Design Patterns
- **Cog System:** Modular, hot-reloadable feature extensions
- **Async/Await:** Non-blocking I/O for API calls and file operations
- **Lock-Based Concurrency:** Race condition prevention in data persistence
- **Factory Pattern:** Dynamic object creation from API responses
- **Singleton Configuration:** Centralized settings management

---

## 🛠️ Technical Stack

**Core Technologies:**
- **Python 3.11+** - Modern async/await, type hints
- **discord.py 2.3+** - Discord API wrapper with slash commands support
- **Requests** - HTTP client for external APIs

**External APIs:**
- Riot Games API (League of Legends match data)
- Henrik Valorant API (Valorant match statistics)
- Data Dragon API (Champion metadata)

**Development Tools:**
- Git for version control
- Logging module for debugging and monitoring
- JSON for data serialization

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11 or higher
- Discord Bot Token ([Discord Developer Portal](https://discord.com/developers/applications))
- Riot Games API Key ([Riot Developer Portal](https://developer.riotgames.com/))
- Henrik API Key ([Henrik Dev API](https://docs.henrikdev.xyz/))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/Marble.git  # 🔧 Update with your repo URL
   cd Marble
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   
   Create a `.env` file in the root directory:
   ```env
   BOT_TOKEN=your_discord_bot_token_here
   RIOT_KEY=your_riot_api_key_here
   HD_KEY=your_henrik_api_key_here
   ```
   
   <!-- 🔧 CUSTOMIZATION: Update config.py with your server/channel IDs -->

4. **Update configuration** (Optional)
   
   Edit `config.py` to customize:
   - Discord server/channel IDs
   - Team member roster for Valorant features
   - Performance metric thresholds

5. **Run the bot**
   ```bash
   python bot.py
   ```

---

## 📖 Usage Examples

### League of Legends Commands
```bash
!blame [count] [queue]        # Analyze recent losses
!register RiotName#TAG        # Link Riot account
!loltrivia                    # Start trivia game
!loltlb [difficulty] [count]  # View leaderboards
```

### Valorant Commands (Owner Only)
```bash
!force_send_premier_results   # Generate match report
```

### Utility Commands
```bash
!hi                           # Test bot responsiveness
!changelog [filter]           # View update history
```

---

## 🎓 Learning Highlights

This project demonstrates practical experience with:

### **Software Engineering Principles**
- ✅ Modular, maintainable code structure
- ✅ Comprehensive error handling and logging
- ✅ API rate limiting and retry logic
- ✅ Asynchronous programming patterns
- ✅ Data validation and type safety

### **API Integration**
- ✅ RESTful API consumption (GET requests, pagination)
- ✅ Authentication and header management
- ✅ Response parsing and data transformation
- ✅ Error handling for network failures

### **Data Management**
- ✅ JSON serialization/deserialization
- ✅ File I/O with encoding handling
- ✅ Concurrent access management (locks)
- ✅ Data migration and versioning

### **Algorithms & Math**
- ✅ Statistical analysis (mean, standard deviation, z-scores)
- ✅ Weighted scoring systems
- ✅ Performance normalization
- ✅ Distance calculations (Euclidean)

---

## 📊 Code Statistics

<!-- 🔧 CUSTOMIZATION: Update these stats based on your actual codebase -->
- **Total Lines of Code:** ~3,500+
- **Number of Commands:** 15+
- **API Endpoints Used:** 10+
- **Data Classes Implemented:** 3 (VoiceActivity, VoicePresence, Player, Match)
- **Background Tasks:** 4 (auto-save, daily cleanup, weekly reports)

---

## 🔄 Recent Updates

See [CHANGELOG.md](CHANGELOG.md) for detailed version history.

**Latest:** v0.7.2 (December 2, 2025)
- Fixed kill participation formulas for supports/junglers
- Improved damage threshold calculations
- Enhanced activity summary timing

---

## 🤝 Contributing

<!-- 🔧 CUSTOMIZATION: Decide if you want contributions -->
This is a personal project primarily for portfolio purposes. However, feedback and suggestions are welcome!

If you'd like to contribute:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

<!-- 🔧 CUSTOMIZATION: Choose and add a license -->
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
<!-- Or use: This project is available for educational and portfolio purposes. -->

---

## 🙏 Acknowledgments

- **Riot Games** - For the League of Legends and Valorant APIs
- **Henrik Dev** - For the comprehensive Valorant API wrapper
- **discord.py** - For the excellent Discord library
- **Data Dragon** - For champion metadata and assets

---

## 📬 Contact

<!-- 🔧 CUSTOMIZATION: Add your contact information -->
**Developer:** Peafowll  
**GitHub:** [@Peafowll](https://github.com/Peafowll)  
<!-- Add more: **LinkedIn:** [Your Profile](linkedin.com/in/yourprofile) -->
<!-- Add more: **Email:** your.email@example.com -->
<!-- Add more: **Portfolio:** [yourportfolio.com](https://yourportfolio.com) -->

---

## 🎯 Future Enhancements

<!-- 🔧 CUSTOMIZATION: Add features you plan to implement -->
- [ ] Database migration (PostgreSQL/MongoDB)
- [ ] Slash command implementation
- [ ] Web dashboard for statistics
- [ ] Machine learning for match outcome prediction
- [ ] Expanded Valorant features (rank tracking, agent recommendations)
- [ ] Docker containerization
- [ ] Automated testing suite (pytest)
- [ ] CI/CD pipeline (GitHub Actions)

---

<div align="center">

**⭐ If this project helped you learn something new, consider giving it a star! ⭐**

Made with ❤️ and lots of ☕

</div>
