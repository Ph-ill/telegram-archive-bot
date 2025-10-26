"""
Quiz State Manager - Thread-safe persistence and state management
"""

import json
import logging
import os
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class QuizStateManager:
    """Thread-safe persistence and state management"""
    
    def __init__(self, data_file_path: str):
        """Initialize with data file path"""
        self.data_file_path = data_file_path
        self.lock = threading.Lock()
        
        # Set up persistent leaderboard file
        data_dir = os.path.dirname(data_file_path)
        self.leaderboard_file_path = os.path.join(data_dir, 'quiz_leaderboard.json')
        
        # Ensure directory exists
        os.makedirs(data_dir, exist_ok=True)
        
        # Initialize files if they don't exist
        if not os.path.exists(data_file_path):
            self._write_data({})
        
        if not os.path.exists(self.leaderboard_file_path):
            self._write_leaderboard_data({})
        
        logger.info(f"QuizStateManager initialized with data file: {data_file_path}")
        logger.info(f"Persistent leaderboard file: {self.leaderboard_file_path}")
    
    def _read_data(self) -> Dict[str, Any]:
        """Read all data from JSON file with error handling"""
        try:
            with open(self.data_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except (FileNotFoundError, json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error reading quiz data file: {e}. Returning empty data.")
            return {}
    
    def _write_data(self, data: Dict[str, Any]) -> None:
        """Write all data to JSON file atomically"""
        try:
            # Write to temporary file first for atomic operation
            temp_file = f"{self.data_file_path}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            os.rename(temp_file, self.data_file_path)
        except (IOError, OSError) as e:
            logger.error(f"Error writing quiz data file: {e}")
            # Clean up temp file if it exists
            if os.path.exists(f"{self.data_file_path}.tmp"):
                try:
                    os.remove(f"{self.data_file_path}.tmp")
                except OSError:
                    pass
            raise
    
    def _read_leaderboard_data(self) -> Dict[str, Any]:
        """Read persistent leaderboard data from JSON file"""
        try:
            with open(self.leaderboard_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except (FileNotFoundError, json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error reading leaderboard file: {e}. Returning empty data.")
            return {}
    
    def _write_leaderboard_data(self, data: Dict[str, Any]) -> None:
        """Write persistent leaderboard data to JSON file atomically"""
        try:
            # Write to temporary file first for atomic operation
            temp_file = f"{self.leaderboard_file_path}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            os.rename(temp_file, self.leaderboard_file_path)
        except (IOError, OSError) as e:
            logger.error(f"Error writing leaderboard file: {e}")
            # Clean up temp file if it exists
            if os.path.exists(f"{self.leaderboard_file_path}.tmp"):
                try:
                    os.remove(f"{self.leaderboard_file_path}.tmp")
                except OSError:
                    pass
            raise
    
    def save_quiz_state(self, chat_id: int, quiz_data: dict) -> None:
        """Save quiz state to persistent storage"""
        with self.lock:
            try:
                data = self._read_data()
                data[str(chat_id)] = quiz_data
                self._write_data(data)
                logger.debug(f"Quiz state saved for chat {chat_id}")
            except Exception as e:
                logger.error(f"Failed to save quiz state for chat {chat_id}: {e}")
                raise
    
    def load_quiz_state(self, chat_id: int) -> dict:
        """Load quiz state from persistent storage"""
        with self.lock:
            try:
                data = self._read_data()
                quiz_state = data.get(str(chat_id), {})
                logger.debug(f"Quiz state loaded for chat {chat_id}")
                return quiz_state
            except Exception as e:
                logger.error(f"Failed to load quiz state for chat {chat_id}: {e}")
                return {}
    
    def update_scores(self, chat_id: int, user_id: int, username: str, points: int) -> None:
        """Update user scores atomically"""
        with self.lock:
            try:
                data = self._read_data()
                chat_key = str(chat_id)
                
                if chat_key not in data:
                    logger.warning(f"No quiz state found for chat {chat_id} when updating scores")
                    return
                
                quiz_state = data[chat_key]
                if 'scores' not in quiz_state:
                    quiz_state['scores'] = {}
                
                user_key = str(user_id)
                if user_key not in quiz_state['scores']:
                    quiz_state['scores'][user_key] = {
                        'username': username,
                        'points': 0
                    }
                
                # Update points and username (in case username changed)
                quiz_state['scores'][user_key]['points'] += points
                quiz_state['scores'][user_key]['username'] = username
                
                logger.info(f"Updated scores for user {username} ({user_id}) in chat {chat_id}: +{points} points, total: {quiz_state['scores'][user_key]['points']}")
                
                self._write_data(data)
                logger.debug(f"Scores updated for user {user_id} in chat {chat_id}: +{points} points")
            except Exception as e:
                logger.error(f"Failed to update scores for user {user_id} in chat {chat_id}: {e}")
                raise
    
    def mark_question_answered(self, chat_id: int, question_idx: int, correct_answer: str) -> bool:
        """Mark question as answered atomically. Returns True if successfully marked, False if already answered"""
        with self.lock:
            try:
                data = self._read_data()
                chat_key = str(chat_id)
                
                if chat_key not in data:
                    logger.warning(f"No quiz state found for chat {chat_id} when marking question answered")
                    return False
                
                quiz_state = data[chat_key]
                if 'questions' not in quiz_state or question_idx >= len(quiz_state['questions']):
                    logger.warning(f"Invalid question index {question_idx} for chat {chat_id}")
                    return False
                
                question = quiz_state['questions'][question_idx]
                
                # Check if already answered
                if question.get('answered', False):
                    logger.debug(f"Question {question_idx} in chat {chat_id} already answered")
                    return False
                
                # Mark as answered
                question['answered'] = True
                question['answered_by'] = correct_answer
                
                self._write_data(data)
                logger.debug(f"Question {question_idx} marked as answered in chat {chat_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to mark question {question_idx} as answered in chat {chat_id}: {e}")
                return False
    
    def check_user_attempted_question(self, chat_id: int, question_idx: int, user_id: int) -> bool:
        """Check if user has already attempted this question"""
        with self.lock:
            try:
                data = self._read_data()
                chat_key = str(chat_id)
                
                if chat_key not in data:
                    return False
                
                quiz_state = data[chat_key]
                if 'questions' not in quiz_state or question_idx >= len(quiz_state['questions']):
                    return False
                
                question = quiz_state['questions'][question_idx]
                attempted_by = question.get('attempted_by', [])
                
                return user_id in attempted_by
            except Exception as e:
                logger.error(f"Failed to check user attempt for question {question_idx} in chat {chat_id}: {e}")
                return False
    
    def mark_user_attempted_question(self, chat_id: int, question_idx: int, user_id: int) -> bool:
        """Mark that a user has attempted this question"""
        with self.lock:
            try:
                data = self._read_data()
                chat_key = str(chat_id)
                
                if chat_key not in data:
                    return False
                
                quiz_state = data[chat_key]
                if 'questions' not in quiz_state or question_idx >= len(quiz_state['questions']):
                    return False
                
                question = quiz_state['questions'][question_idx]
                if 'attempted_by' not in question:
                    question['attempted_by'] = []
                
                if user_id not in question['attempted_by']:
                    question['attempted_by'].append(user_id)
                    self._write_data(data)
                    logger.debug(f"User {user_id} marked as attempted question {question_idx} in chat {chat_id}")
                
                return True
            except Exception as e:
                logger.error(f"Failed to mark user attempt for question {question_idx} in chat {chat_id}: {e}")
                return False
    
    def clear_quiz_state(self, chat_id: int) -> None:
        """Clear quiz state for specified chat"""
        with self.lock:
            try:
                data = self._read_data()
                chat_key = str(chat_id)
                
                if chat_key in data:
                    del data[chat_key]
                    self._write_data(data)
                    logger.debug(f"Quiz state cleared for chat {chat_id}")
                else:
                    logger.debug(f"No quiz state found for chat {chat_id}")
            except Exception as e:
                logger.error(f"Error clearing quiz state for chat {chat_id}: {e}")
    
    def _write_leaderboard_data(self, data: Dict[str, Any]) -> None:
        """Write persistent leaderboard data to JSON file atomically"""
        try:
            # Write to temporary file first for atomic operation
            temp_file = f"{self.leaderboard_file_path}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            os.rename(temp_file, self.leaderboard_file_path)
        except (IOError, OSError) as e:
            logger.error(f"Error writing leaderboard file: {e}")
            # Clean up temp file if it exists
            if os.path.exists(f"{self.leaderboard_file_path}.tmp"):
                try:
                    os.remove(f"{self.leaderboard_file_path}.tmp")
                except OSError:
                    pass
            raise
    
    def get_persistent_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the persistent leaderboard sorted by total wins"""
        try:
            data = self._read_leaderboard_data()
            
            # Convert to list and sort by total wins
            leaderboard = []
            for user_id, user_data in data.items():
                leaderboard.append({
                    'user_id': int(user_id),
                    'username': user_data['username'],
                    'total_wins': user_data['total_wins'],
                    'subjects_won': user_data['subjects_won'],
                    'difficulty_wins': user_data['difficulty_wins'],
                    'last_win_date': user_data['last_win_date']
                })
            
            # Sort by total wins (descending)
            leaderboard.sort(key=lambda x: x['total_wins'], reverse=True)
            
            return leaderboard[:limit]
            
        except Exception as e:
            logger.error(f"Error getting persistent leaderboard: {e}")
            return []
    
    def check_quiz_has_multiple_participants(self, chat_id: int) -> bool:
        """Check if the current quiz has multiple participants who attempted questions"""
        try:
            quiz_state = self.load_quiz_state(chat_id)
            if not quiz_state or 'questions' not in quiz_state:
                return False
            
            # Collect all unique users who attempted any question
            all_attempted_users = set()
            for question in quiz_state['questions']:
                attempted_by = question.get('attempted_by', [])
                all_attempted_users.update(attempted_by)
            
            return len(all_attempted_users) > 1
            
        except Exception as e:
            logger.error(f"Error checking quiz participants for chat {chat_id}: {e}")
            return False
    
    def add_message_id(self, chat_id: int, message_id: int) -> None:
        """Add a message ID to track for later deletion"""
        with self.lock:
            try:
                data = self._read_data()
                chat_key = str(chat_id)
                
                if chat_key in data and 'message_ids' in data[chat_key]:
                    if message_id not in data[chat_key]['message_ids']:
                        data[chat_key]['message_ids'].append(message_id)
                        self._write_data(data)
                        logger.debug(f"Added message ID {message_id} to track for chat {chat_id}")
            except Exception as e:
                logger.error(f"Error adding message ID {message_id} for chat {chat_id}: {e}")
    
    def get_tracked_message_ids(self, chat_id: int) -> List[int]:
        """Get all tracked message IDs for a chat"""
        try:
            quiz_state = self.load_quiz_state(chat_id)
            if quiz_state and 'message_ids' in quiz_state:
                return quiz_state['message_ids']
            return []
        except Exception as e:
            logger.error(f"Error getting tracked message IDs for chat {chat_id}: {e}")
            return []
    
    def clear_tracked_message_ids(self, chat_id: int) -> None:
        """Clear tracked message IDs for a chat"""
        with self.lock:
            try:
                data = self._read_data()
                chat_key = str(chat_id)
                
                if chat_key in data and 'message_ids' in data[chat_key]:
                    data[chat_key]['message_ids'] = []
                    self._write_data(data)
                    logger.debug(f"Cleared tracked message IDs for chat {chat_id}")
            except Exception as e:
                logger.error(f"Error clearing tracked message IDs for chat {chat_id}: {e}")
    
    def set_main_message_id(self, chat_id: int, message_id: int) -> None:
        """Set the main quiz message ID that will be edited throughout the quiz"""
        with self.lock:
            try:
                data = self._read_data()
                chat_key = str(chat_id)
                
                if chat_key in data:
                    data[chat_key]['main_message_id'] = message_id
                    self._write_data(data)
                    logger.info(f"Set main message ID {message_id} for chat {chat_id}")
                else:
                    logger.warning(f"No quiz state found for chat {chat_id} when setting main message ID {message_id}")
            except Exception as e:
                logger.error(f"Error setting main message ID for chat {chat_id}: {e}")
    
    def get_main_message_id(self, chat_id: int) -> Optional[int]:
        """Get the main quiz message ID for a chat"""
        try:
            quiz_state = self.load_quiz_state(chat_id)
            if quiz_state and 'main_message_id' in quiz_state:
                message_id = quiz_state['main_message_id']
                logger.debug(f"Found main message ID {message_id} for chat {chat_id}")
                return message_id
            else:
                logger.warning(f"No main message ID found in quiz state for chat {chat_id}")
                return None
        except Exception as e:
            logger.error(f"Error getting main message ID for chat {chat_id}: {e}")
            return None
    
    def validate_quiz_state(self, quiz_state: dict) -> bool:
        """Validate quiz state structure and data integrity"""
        try:
            # Check required fields
            required_fields = ['active', 'subject', 'difficulty', 'questions', 'current_question', 'scores', 'created_at']
            for field in required_fields:
                if field not in quiz_state:
                    logger.warning(f"Missing required field: {field}")
                    return False
            
            # Validate field types and values
            if not isinstance(quiz_state['active'], bool):
                logger.warning("Field 'active' must be boolean")
                return False
            
            if not isinstance(quiz_state['subject'], str) or not quiz_state['subject'].strip():
                logger.warning("Field 'subject' must be non-empty string")
                return False
            
            if quiz_state['difficulty'] not in ['easy', 'medium', 'hard', 'expert']:
                logger.warning(f"Invalid difficulty: {quiz_state['difficulty']}")
                return False
            
            if not isinstance(quiz_state['questions'], list) or len(quiz_state['questions']) == 0:
                logger.warning("Field 'questions' must be non-empty list")
                return False
            
            if not isinstance(quiz_state['current_question'], int) or quiz_state['current_question'] < 0:
                logger.warning("Field 'current_question' must be non-negative integer")
                return False
            
            if not isinstance(quiz_state['scores'], dict):
                logger.warning("Field 'scores' must be dictionary")
                return False
            
            # Validate questions structure
            for i, question in enumerate(quiz_state['questions']):
                if not self._validate_question_structure(question, i):
                    return False
            
            # Validate scores structure
            for user_id, score_data in quiz_state['scores'].items():
                if not self._validate_score_structure(score_data, user_id):
                    return False
            
            return True
        except Exception as e:
            logger.error(f"Error validating quiz state: {e}")
            return False
    
    def _validate_question_structure(self, question: dict, index: int) -> bool:
        """Validate individual question structure"""
        required_fields = ['question_text', 'options', 'correct_answer']
        for field in required_fields:
            if field not in question:
                logger.warning(f"Question {index} missing required field: {field}")
                return False
        
        if not isinstance(question['question_text'], str) or not question['question_text'].strip():
            logger.warning(f"Question {index} has invalid question_text")
            return False
        
        if not isinstance(question['options'], list) or len(question['options']) < 2:
            logger.warning(f"Question {index} must have at least 2 options")
            return False
        
        if question['correct_answer'] not in question['options']:
            logger.warning(f"Question {index} correct_answer not in options")
            return False
        
        # Optional fields validation
        if 'answered' in question and not isinstance(question['answered'], bool):
            logger.warning(f"Question {index} 'answered' field must be boolean")
            return False
        
        return True
    
    def _validate_score_structure(self, score_data: dict, user_id: str) -> bool:
        """Validate individual score structure"""
        required_fields = ['username', 'points']
        for field in required_fields:
            if field not in score_data:
                logger.warning(f"Score for user {user_id} missing required field: {field}")
                return False
        
        if not isinstance(score_data['username'], str) or not score_data['username'].strip():
            logger.warning(f"Score for user {user_id} has invalid username")
            return False
        
        if not isinstance(score_data['points'], int) or score_data['points'] < 0:
            logger.warning(f"Score for user {user_id} has invalid points")
            return False
        
        return True
    
    def create_quiz_state_template(self, subject: str, difficulty: str, questions: List[dict]) -> dict:
        """Create a new quiz state template with proper structure"""
        return {
            'active': True,
            'subject': subject,
            'difficulty': difficulty,
            'questions': [self._format_question(q) for q in questions],
            'current_question': 0,
            'scores': {},
            'created_at': datetime.now().isoformat(),
            'message_ids': [],
            'main_message_id': None  # The main quiz message that gets edited
        }
    
    def _format_question(self, question_data: dict) -> dict:
        """Format question data to ensure proper structure"""
        return {
            'question_text': question_data.get('question_text', ''),
            'options': question_data.get('options', []),
            'correct_answer': question_data.get('correct_answer', ''),
            'answered': False,
            'answered_by': None,
            'attempted_by': []  # Track users who have attempted this question
        }
    
    def get_quiz_status(self, chat_id: int) -> dict:
        """Get current quiz status and statistics"""
        quiz_state = self.load_quiz_state(chat_id)
        if not quiz_state:
            return {'active': False}
        
        total_questions = len(quiz_state.get('questions', []))
        answered_questions = sum(1 for q in quiz_state.get('questions', []) if q.get('answered', False))
        
        return {
            'active': quiz_state.get('active', False),
            'subject': quiz_state.get('subject', ''),
            'difficulty': quiz_state.get('difficulty', ''),
            'total_questions': total_questions,
            'answered_questions': answered_questions,
            'current_question': quiz_state.get('current_question', 0),
            'participants': len(quiz_state.get('scores', {})),
            'created_at': quiz_state.get('created_at', '')
        }
    
    def get_leaderboard_data(self, chat_id: int) -> List[dict]:
        """Get sorted leaderboard data"""
        quiz_state = self.load_quiz_state(chat_id)
        if not quiz_state:
            logger.warning(f"No quiz state found for chat {chat_id} when getting leaderboard")
            return []
        
        if 'scores' not in quiz_state:
            logger.warning(f"No scores found in quiz state for chat {chat_id}")
            return []
        
        scores = quiz_state['scores']
        logger.info(f"Getting leaderboard for chat {chat_id}: {len(scores)} participants with scores: {scores}")
        
        # Convert scores to list and sort by points (descending)
        leaderboard = []
        for user_id, score_data in scores.items():
            leaderboard.append({
                'user_id': int(user_id),
                'username': score_data['username'],
                'points': score_data['points']
            })
        
        sorted_leaderboard = sorted(leaderboard, key=lambda x: x['points'], reverse=True)
        logger.info(f"Sorted leaderboard for chat {chat_id}: {sorted_leaderboard}")
        return sorted_leaderboard
    
    def get_current_question(self, chat_id: int) -> Optional[dict]:
        """Get the current unanswered question"""
        quiz_state = self.load_quiz_state(chat_id)
        if not quiz_state or not quiz_state.get('active', False):
            return None
        
        questions = quiz_state.get('questions', [])
        current_idx = quiz_state.get('current_question', 0)
        
        if current_idx >= len(questions):
            return None
        
        question = questions[current_idx].copy()
        question['question_index'] = current_idx
        return question
    
    def advance_to_next_question(self, chat_id: int) -> bool:
        """Advance to the next question. Returns True if advanced, False if quiz is complete"""
        with self.lock:
            try:
                data = self._read_data()
                chat_key = str(chat_id)
                
                if chat_key not in data:
                    return False
                
                quiz_state = data[chat_key]
                questions = quiz_state.get('questions', [])
                current_idx = quiz_state.get('current_question', 0)
                
                # Check if there are more questions
                logger.info(f"Advance check: current_idx={current_idx}, total_questions={len(questions)}")
                
                if current_idx + 1 >= len(questions):
                    # Quiz is complete
                    logger.info(f"Quiz complete for chat {chat_id}: no more questions")
                    quiz_state['active'] = False
                    self._write_data(data)
                    return False
                
                # Advance to next question
                new_idx = current_idx + 1
                quiz_state['current_question'] = new_idx
                self._write_data(data)
                logger.info(f"Advanced to question {new_idx} for chat {chat_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to advance to next question in chat {chat_id}: {e}")
                return False
    
    def migrate_quiz_state(self, quiz_state: dict) -> dict:
        """Migrate quiz state to current schema version"""
        # Add any missing fields with default values
        migrated_state = quiz_state.copy()
        
        # Ensure all required fields exist
        defaults = {
            'active': True,
            'subject': 'Unknown',
            'difficulty': 'medium',
            'questions': [],
            'current_question': 0,
            'scores': {},
            'created_at': datetime.now().isoformat(),
            'message_ids': []
        }
        
        for key, default_value in defaults.items():
            if key not in migrated_state:
                migrated_state[key] = default_value
        
        # Ensure questions have proper structure
        for question in migrated_state.get('questions', []):
            if 'answered' not in question:
                question['answered'] = False
            if 'answered_by' not in question:
                question['answered_by'] = None
        
        return migrated_state
    
    def record_quiz_win(self, winner_user_id: int, winner_username: str, quiz_subject: str, 
                       total_participants: int, winner_score: int, total_questions: int) -> None:
        """Record a quiz win in the persistent leaderboard"""
        with self.lock:
            try:
                data = self._read_leaderboard_data()
                user_key = str(winner_user_id)
                
                if user_key not in data:
                    data[user_key] = {
                        'username': winner_username,
                        'quiz_wins': 0,
                        'total_points': 0,
                        'quizzes_participated': 0,
                        'last_win_date': None
                    }
                
                # Update stats
                data[user_key]['username'] = winner_username  # Update in case username changed
                data[user_key]['quiz_wins'] += 1
                data[user_key]['total_points'] += winner_score
                data[user_key]['quizzes_participated'] += 1
                data[user_key]['last_win_date'] = datetime.now().isoformat()
                
                self._write_leaderboard_data(data)
                logger.info(f"Recorded quiz win for {winner_username} ({winner_user_id}): {winner_score}/{total_questions} points")
                
            except Exception as e:
                logger.error(f"Failed to record quiz win: {e}")
                raise
    
    def record_quiz_participation(self, user_id: int, username: str) -> None:
        """Record quiz participation (for users who didn't win but participated)"""
        with self.lock:
            try:
                data = self._read_leaderboard_data()
                user_key = str(user_id)
                
                if user_key not in data:
                    data[user_key] = {
                        'username': username,
                        'quiz_wins': 0,
                        'total_points': 0,
                        'quizzes_participated': 0,
                        'last_win_date': None
                    }
                
                # Update participation count and username
                data[user_key]['username'] = username
                data[user_key]['quizzes_participated'] += 1
                
                self._write_leaderboard_data(data)
                
            except Exception as e:
                logger.error(f"Failed to record quiz participation for {username}: {e}")
    
    def get_persistent_leaderboard(self) -> List[Dict[str, Any]]:
        """Get the persistent leaderboard sorted by quiz wins"""
        try:
            data = self._read_leaderboard_data()
            
            leaderboard = []
            for user_id, stats in data.items():
                if stats['quiz_wins'] > 0:  # Only show users who have won at least one quiz
                    leaderboard.append({
                        'user_id': int(user_id),
                        'username': stats['username'],
                        'quiz_wins': stats['quiz_wins'],
                        'total_points': stats['total_points'],
                        'quizzes_participated': stats['quizzes_participated'],
                        'win_rate': round((stats['quiz_wins'] / stats['quizzes_participated']) * 100, 1) if stats['quizzes_participated'] > 0 else 0,
                        'last_win_date': stats.get('last_win_date')
                    })
            
            # Sort by quiz wins (descending), then by win rate (descending)
            return sorted(leaderboard, key=lambda x: (x['quiz_wins'], x['win_rate']), reverse=True)
            
        except Exception as e:
            logger.error(f"Error getting persistent leaderboard: {e}")
            return []
    
    def _read_leaderboard_data(self) -> Dict[str, Any]:
        """Read persistent leaderboard data from JSON file"""
        try:
            with open(self.leaderboard_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except (FileNotFoundError, json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error reading leaderboard file: {e}. Returning empty data.")
            return {}
    
    def _write_leaderboard_data(self, data: Dict[str, Any]) -> None:
        """Write persistent leaderboard data to JSON file atomically"""
        try:
            # Write to temporary file first for atomic operation
            temp_file = f"{self.leaderboard_file_path}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            os.rename(temp_file, self.leaderboard_file_path)
        except (IOError, OSError) as e:
            logger.error(f"Error writing leaderboard file: {e}")
            # Clean up temp file if it exists
            if os.path.exists(f"{self.leaderboard_file_path}.tmp"):
                try:
                    os.remove(f"{self.leaderboard_file_path}.tmp")
                except OSError:
                    pass
            raise
    
    def update_participation_stats(self, participants: Dict[str, Dict[str, Any]]) -> None:
        """Update participation statistics for all quiz participants"""
        if len(participants) < 2:
            return  # Don't update stats for single-player quizzes
        
        with self.lock:
            try:
                data = self._read_leaderboard_data()
                
                for user_id_str, participant_data in participants.items():
                    user_key = str(user_id_str)
                    username = participant_data.get('username', f'user_{user_id_str}')
                    
                    if user_key not in data:
                        data[user_key] = {
                            'username': username,
                            'wins': 0,
                            'total_points': 0,
                            'quizzes_participated': 0,
                            'last_win_date': None
                        }
                    
                    # Update participation count and username
                    data[user_key]['quizzes_participated'] += 1
                    data[user_key]['username'] = username
                
                self._write_leaderboard_data(data)
                logger.debug(f"Updated participation stats for {len(participants)} users")
            except Exception as e:
                logger.error(f"Failed to update participation stats: {e}")
    
    def get_persistent_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get persistent leaderboard data sorted by wins"""
        try:
            data = self._read_leaderboard_data()
            
            # Convert to list and sort by wins (descending), then by total_points
            leaderboard = []
            for user_id, stats in data.items():
                if stats.get('wins', 0) > 0:  # Only include users with at least one win
                    leaderboard.append({
                        'user_id': int(user_id),
                        'username': stats['username'],
                        'wins': stats['wins'],
                        'total_points': stats.get('total_points', 0),
                        'quizzes_participated': stats.get('quizzes_participated', 0),
                        'last_win_date': stats.get('last_win_date'),
                        'win_rate': round((stats['wins'] / max(stats.get('quizzes_participated', 1), 1)) * 100, 1)
                    })
            
            # Sort by wins (descending), then by total_points (descending)
            leaderboard.sort(key=lambda x: (x['wins'], x['total_points']), reverse=True)
            
            return leaderboard[:limit]
        except Exception as e:
            logger.error(f"Error getting persistent leaderboard: {e}")
            return []
    
    def check_quiz_has_multiple_participants(self, chat_id: int) -> bool:
        """Check if quiz has multiple participants (to prevent solo play wins)"""
        try:
            quiz_state = self.load_quiz_state(chat_id)
            if not quiz_state:
                return False
            
            # Count unique users who attempted at least one question
            unique_participants = set()
            for question in quiz_state.get('questions', []):
                attempted_by = question.get('attempted_by', [])
                unique_participants.update(attempted_by)
            
            return len(unique_participants) > 1
            
        except Exception as e:
            logger.error(f"Error checking quiz participants for chat {chat_id}: {e}")
            return False