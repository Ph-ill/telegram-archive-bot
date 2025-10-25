# Telegram Quiz Module

This module adds interactive quiz functionality to the Telegram bot using Google's Gemini API for question generation.

## Features

- **AI-Generated Questions**: Uses Google Gemini API to generate contextual quiz questions
- **Multiple Difficulty Levels**: Easy, Medium, Hard, and Expert difficulty settings
- **Real-time Competition**: "First answer wins" gameplay with immediate feedback
- **Persistent State**: Thread-safe quiz state management with JSON storage
- **Interactive UI**: Inline keyboard buttons for multiple choice answers
- **Leaderboards**: Real-time and final score tracking

## Environment Variables

### Required

- `GEMINI_API_KEY`: Your Google Gemini API key for question generation
  - Get your API key from: https://makersuite.google.com/app/apikey
  - Example: `GEMINI_API_KEY=AIzaSyC...`

### Optional

- `BOT_TOKEN`: Telegram bot token (already required by main bot)
- `WEBHOOK_URL`: Webhook URL (already required by main bot)

## Docker Configuration

Add the Gemini API key to your Docker environment:

```dockerfile
ENV GEMINI_API_KEY=your_api_key_here
```

Or in docker-compose.yml:

```yaml
environment:
  - GEMINI_API_KEY=your_api_key_here
```

## Commands

### Basic Commands

- `/quiz_new [Subject] [Number] [Difficulty]` - Start a new quiz
  - **Subject**: Topic for questions (required)
  - **Number**: Number of questions (1-20, default: 5)
  - **Difficulty**: easy, medium, hard, expert (default: medium)

- `/quiz_leaderboard` - Show current quiz scores
- `/quiz_stop` - Stop the current quiz and show final results
- `/quiz_help` - Show detailed help and rules

### Examples

```
/quiz_new Python Programming 10 hard
/quiz_new World History 5
/quiz_new Science
```

## How to Play

1. Someone starts a quiz with `/quiz_new`
2. Questions appear with multiple choice buttons (A, B, C, D)
3. Click your answer quickly - first correct answer wins!
4. Earn 1 point for each correct answer
5. View scores anytime with `/quiz_leaderboard`
6. Quiz ends when all questions are answered or someone uses `/quiz_stop`

## Rules

- Only one quiz per chat at a time
- First person to answer correctly gets the point
- Questions are generated based on the specified subject and difficulty
- Quiz state persists across bot restarts

## Technical Details

### Architecture

- **QuizManager**: Central coordinator for quiz operations
- **GeminiQuestionGenerator**: Handles AI question generation
- **QuizStateManager**: Thread-safe persistent state management
- **QuizUI**: Telegram interface and message formatting

### Data Storage

Quiz data is stored in `/app/data/quiz_data.json` with the following structure:

```json
{
  "chat_id": {
    "active": true,
    "subject": "Python Programming",
    "difficulty": "medium",
    "questions": [...],
    "current_question": 0,
    "scores": {...},
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### Error Handling

The module includes comprehensive error handling for:

- API failures and timeouts
- Invalid user input
- Concurrent access conflicts
- JSON parsing errors
- Network connectivity issues

### Thread Safety

All quiz operations are thread-safe using:

- `threading.Lock()` for file operations
- Atomic read-modify-write operations
- Race condition prevention for answer processing

## Troubleshooting

### Common Issues

1. **"Quiz functionality is not available"**
   - Check that `GEMINI_API_KEY` environment variable is set
   - Verify the API key is valid and has proper permissions

2. **"Failed to generate questions"**
   - Check internet connectivity
   - Verify Gemini API quota and billing
   - Try a simpler subject or fewer questions

3. **"Too late! Someone else answered first"**
   - This is normal behavior - only the first correct answer wins
   - Try to answer more quickly next time

4. **Quiz state corruption**
   - The system automatically recovers from most state issues
   - In extreme cases, delete `/app/data/quiz_data.json` to reset all quizzes

### API Limits

- Gemini API has rate limits and quotas
- The module implements exponential backoff for retries
- Consider upgrading your API plan for heavy usage

### Performance

- File-based storage is suitable for moderate usage
- Memory usage scales linearly with active quizzes
- Each quiz typically uses <1KB of storage

## Development

### Adding New Features

1. Extend `QuizManager` for new quiz logic
2. Update `QuizUI` for new message formats
3. Modify `QuizStateManager` for new data fields
4. Add new commands to the main bot's command processor

### Testing

Run the integration tests:

```bash
python test_quiz_integration.py
```

### Dependencies

- `google-generativeai>=0.3.0` - AI question generation
- `threading` - Thread-safe operations
- `json` - Data serialization
- `logging` - Error tracking and debugging

## License

This module is part of the Telegram Archive Bot project.