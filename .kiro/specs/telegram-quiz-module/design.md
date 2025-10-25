# Design Document

## Overview

The Telegram Quiz Module integrates seamlessly into the existing SeleniumArchiveBot, adding interactive quiz functionality powered by Google's Gemini API. The system manages concurrent quiz sessions across multiple chats, implements thread-safe state persistence, and provides real-time competitive gameplay with inline keyboard interactions.

## Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Telegram      │    │   Quiz Module    │    │   Gemini API    │
│   Webhook       │◄──►│   (New)          │◄──►│   Integration   │
│   (Existing)    │    │                  │    │   (New)         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       ▼                       │
         │              ┌──────────────────┐             │
         │              │   State Manager  │             │
         │              │   (Thread-Safe)  │             │
         │              └──────────────────┘             │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Message       │    │   JSON File      │    │   Error         │
│   Handler       │    │   Storage        │    │   Handler       │
│   (Enhanced)    │    │   (Persistent)   │    │   (New)         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Integration Points

The quiz module integrates with the existing bot through:
- **Command Processing**: Extends the existing `process_slash_command` method
- **Callback Handling**: Adds new callback query processing for inline keyboards
- **Message Sending**: Utilizes existing `send_message` method
- **Data Storage**: Uses the established `/app/data` directory pattern

## Components and Interfaces

### 1. QuizManager Class

**Purpose**: Central coordinator for all quiz operations

**Key Methods**:
```python
class QuizManager:
    def __init__(self, bot_instance, data_dir: str, gemini_api_key: str)
    def create_quiz(self, chat_id: int, subject: str, num_questions: int, difficulty: str) -> bool
    def process_answer(self, chat_id: int, user_id: int, username: str, question_idx: int, answer: str) -> dict
    def get_leaderboard(self, chat_id: int) -> dict
    def stop_quiz(self, chat_id: int) -> dict
    def is_quiz_active(self, chat_id: int) -> bool
```

**Responsibilities**:
- Quiz lifecycle management
- State validation and transitions
- Coordination between components

### 2. GeminiQuestionGenerator Class

**Purpose**: Handles all Gemini API interactions for question generation

**Key Methods**:
```python
class GeminiQuestionGenerator:
    def __init__(self, api_key: str)
    def generate_questions(self, subject: str, num_questions: int, difficulty: str) -> list
    def _build_prompt(self, subject: str, num_questions: int, difficulty: str) -> str
    def _parse_response(self, response: str) -> list
```

**API Integration**:
- Uses `google-generativeai` library
- Implements retry logic for API failures
- Validates JSON response structure
- Handles rate limiting and errors gracefully

### 3. QuizStateManager Class

**Purpose**: Thread-safe persistence and state management

**Key Methods**:
```python
class QuizStateManager:
    def __init__(self, data_file_path: str)
    def save_quiz_state(self, chat_id: int, quiz_data: dict) -> None
    def load_quiz_state(self, chat_id: int) -> dict
    def update_scores(self, chat_id: int, user_id: int, username: str, points: int) -> None
    def mark_question_answered(self, chat_id: int, question_idx: int, correct_answer: str) -> bool
    def clear_quiz_state(self, chat_id: int) -> None
```

**Thread Safety**:
- Uses `threading.Lock()` for file operations
- Implements atomic read-modify-write operations
- Prevents race conditions during concurrent access

### 4. QuizUI Class

**Purpose**: Handles all Telegram UI interactions

**Key Methods**:
```python
class QuizUI:
    def __init__(self, bot_instance)
    def send_question(self, chat_id: int, question_data: dict, question_num: int) -> int
    def update_question_result(self, chat_id: int, message_id: int, result: str) -> None
    def send_leaderboard(self, chat_id: int, scores: dict, is_final: bool) -> None
    def send_quiz_help(self, chat_id: int) -> None
```

**UI Components**:
- Inline keyboard generation for multiple choice
- Message formatting with block quotes
- Progress indicators and status messages
- Error message display

## Data Models

### Quiz State Structure

```json
{
  "chat_id_123": {
    "active": true,
    "subject": "World History",
    "difficulty": "medium",
    "questions": [
      {
        "question_text": "What year did World War II end?",
        "options": ["1944", "1945", "1946", "1947"],
        "correct_answer": "1945",
        "answered": false,
        "answered_by": null
      }
    ],
    "current_question": 0,
    "scores": {
      "user_456": {
        "username": "john_doe",
        "points": 2
      }
    },
    "created_at": "2024-01-15T10:30:00Z",
    "message_ids": [789, 790]
  }
}
```

### Callback Data Format

```
quiz_{chat_id}_{question_idx}_{option_idx}
```

Example: `quiz_123_0_1` (chat 123, question 0, option 1)

## Error Handling

### Error Categories and Responses

1. **API Errors**:
   - Gemini API timeout/failure
   - Invalid API key
   - Rate limiting
   - Response: Inform users, clean up partial state

2. **Validation Errors**:
   - Invalid command parameters
   - Malformed JSON responses
   - Response: Show help message with correct format

3. **State Errors**:
   - File corruption
   - Concurrent access conflicts
   - Response: Reset quiz state, log error

4. **User Errors**:
   - Quiz already active
   - No active quiz for leaderboard/stop
   - Response: Informative error messages

### Error Recovery Strategies

- **Graceful Degradation**: Continue with reduced functionality
- **State Cleanup**: Remove corrupted quiz states
- **User Notification**: Clear error messages with next steps
- **Logging**: Comprehensive error logging for debugging

## Testing Strategy

### Unit Tests

1. **QuizManager Tests**:
   - Quiz creation validation
   - State transitions
   - Score calculations

2. **GeminiQuestionGenerator Tests**:
   - Prompt generation
   - Response parsing
   - Error handling

3. **QuizStateManager Tests**:
   - Thread safety
   - File operations
   - Data integrity

### Integration Tests

1. **End-to-End Quiz Flow**:
   - Complete quiz lifecycle
   - Multiple user interactions
   - Concurrent access scenarios

2. **API Integration Tests**:
   - Gemini API responses
   - Error scenarios
   - Rate limiting

### Performance Tests

1. **Concurrent Users**:
   - Multiple simultaneous answers
   - State consistency
   - Response times

2. **Large Quizzes**:
   - Many questions
   - Many participants
   - Memory usage

## Security Considerations

### API Key Management
- Retrieve from environment variable only
- No logging of API keys
- Secure error messages (no key exposure)

### Input Validation
- Sanitize all user inputs
- Validate JSON structures
- Prevent injection attacks

### Rate Limiting
- Implement client-side rate limiting
- Handle API rate limits gracefully
- Prevent abuse of quiz creation

## Performance Considerations

### Optimization Strategies

1. **Caching**:
   - Cache quiz states in memory
   - Lazy loading of inactive quizzes
   - TTL for memory cleanup

2. **Batch Operations**:
   - Batch score updates
   - Minimize file I/O operations
   - Efficient JSON serialization

3. **Resource Management**:
   - Connection pooling for API calls
   - Memory cleanup for completed quizzes
   - Async operations where possible

### Scalability Limits

- **File-based storage**: Suitable for moderate usage
- **Memory usage**: Linear with active quizzes
- **API limits**: Respect Gemini API quotas

## Deployment Considerations

### Environment Variables
```bash
GEMINI_API_KEY=your_api_key_here
```

### File Permissions
- Ensure `/app/data` directory is writable
- Set appropriate file permissions for `quiz_data.json`

### Dependencies
```python
google-generativeai>=0.3.0
```

### Monitoring
- Log quiz creation/completion rates
- Monitor API usage and errors
- Track file system usage