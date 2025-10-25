"""
Quiz Manager - Central coordinator for all quiz operations
"""

import logging
import os
from typing import Dict, Any, Optional, List
from .state_manager import QuizStateManager
from .gemini_generator import GeminiQuestionGenerator

logger = logging.getLogger(__name__)


class QuizManager:
    """Central coordinator for all quiz operations"""
    
    def __init__(self, bot_instance, data_dir: str, gemini_api_key: str):
        """Initialize QuizManager with dependencies"""
        self.bot_instance = bot_instance
        self.data_dir = data_dir
        self.gemini_api_key = gemini_api_key
        
        # Initialize components
        quiz_data_path = os.path.join(data_dir, 'quiz_data.json')
        self.state_manager = QuizStateManager(quiz_data_path)
        self.question_generator = GeminiQuestionGenerator(gemini_api_key)
        
        # Validate API configuration
        api_status = self.question_generator.validate_api_configuration()
        if not api_status['valid']:
            logger.warning(f"Gemini API configuration issues: {api_status['errors']}")
        
        logger.info("QuizManager initialized successfully")
    
    def create_quiz(self, chat_id: int, subject: str, num_questions: int, difficulty: str) -> Dict[str, Any]:
        """
        Create a new quiz for the specified chat
        
        Args:
            chat_id: Telegram chat ID
            subject: Quiz subject/topic
            num_questions: Number of questions to generate
            difficulty: Difficulty level (easy, medium, hard, expert)
            
        Returns:
            Dictionary with success status and message/error details
        """
        try:
            # Check if quiz is already active
            if self.is_quiz_active(chat_id):
                return {
                    'success': False,
                    'error': 'A quiz is already active in this chat. Use /quiz_stop to end it first.',
                    'error_type': 'quiz_active'
                }
            
            # Validate parameters
            validation_result = self._validate_quiz_parameters(subject, num_questions, difficulty)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'error_type': 'validation'
                }
            
            # Use validated parameters
            subject = validation_result['subject']
            num_questions = validation_result['num_questions']
            difficulty = validation_result['difficulty']
            
            logger.info(f"Creating quiz for chat {chat_id}: {subject}, {num_questions} questions, {difficulty} difficulty")
            
            # Generate questions using Gemini API
            try:
                questions = self.question_generator.generate_questions(subject, num_questions, difficulty)
            except Exception as e:
                error_message = self.question_generator.handle_api_error(e, "Quiz creation")
                logger.error(f"Failed to generate questions for chat {chat_id}: {e}")
                return {
                    'success': False,
                    'error': error_message,
                    'error_type': 'api_error'
                }
            
            # Create quiz state
            quiz_state = self.state_manager.create_quiz_state_template(subject, difficulty, questions)
            
            # Validate quiz state
            if not self.state_manager.validate_quiz_state(quiz_state):
                logger.error(f"Generated quiz state is invalid for chat {chat_id}")
                return {
                    'success': False,
                    'error': 'Failed to create valid quiz state. Please try again.',
                    'error_type': 'state_error'
                }
            
            # Save quiz state
            self.state_manager.save_quiz_state(chat_id, quiz_state)
            
            logger.info(f"Quiz created successfully for chat {chat_id}")
            return {
                'success': True,
                'quiz_data': {
                    'subject': subject,
                    'num_questions': num_questions,
                    'difficulty': difficulty,
                    'first_question': questions[0] if questions else None
                }
            }
            
        except Exception as e:
            logger.error(f"Unexpected error creating quiz for chat {chat_id}: {e}")
            return {
                'success': False,
                'error': 'An unexpected error occurred while creating the quiz. Please try again.',
                'error_type': 'system_error'
            }
    
    def process_answer(self, chat_id: int, user_id: int, username: str, question_idx: int, answer: str) -> Dict[str, Any]:
        """
        Process a user's answer to a quiz question with "first wins" logic
        
        Args:
            chat_id: Telegram chat ID
            user_id: User ID who answered
            username: Username of the answerer
            question_idx: Index of the question being answered
            answer: The selected answer
            
        Returns:
            Dictionary with processing results and next actions
        """
        try:
            # Check if quiz is active
            if not self.is_quiz_active(chat_id):
                return {
                    'success': False,
                    'error': 'No active quiz in this chat.',
                    'error_type': 'no_quiz'
                }
            
            # Load quiz state
            quiz_state = self.state_manager.load_quiz_state(chat_id)
            if not quiz_state:
                return {
                    'success': False,
                    'error': 'Failed to load quiz state.',
                    'error_type': 'state_error'
                }
            
            # Validate question index
            questions = quiz_state.get('questions', [])
            if question_idx < 0 or question_idx >= len(questions):
                return {
                    'success': False,
                    'error': 'Invalid question index.',
                    'error_type': 'invalid_question'
                }
            
            question = questions[question_idx]
            
            # Check if question is already answered (atomic operation)
            if not self.state_manager.mark_question_answered(chat_id, question_idx, answer):
                return {
                    'success': False,
                    'error': 'Too late! Someone else already answered this question.',
                    'error_type': 'already_answered'
                }
            
            # Check if answer is correct
            correct_answer = question.get('correct_answer', '')
            is_correct = answer.strip() == correct_answer.strip()
            
            result = {
                'success': True,
                'is_correct': is_correct,
                'correct_answer': correct_answer,
                'user_id': user_id,
                'username': username,
                'question_idx': question_idx
            }
            
            # Award points if correct
            if is_correct:
                self.state_manager.update_scores(chat_id, user_id, username, 1)
                result['points_awarded'] = 1
                logger.info(f"User {username} ({user_id}) answered question {question_idx} correctly in chat {chat_id}")
            else:
                result['points_awarded'] = 0
                logger.info(f"User {username} ({user_id}) answered question {question_idx} incorrectly in chat {chat_id}")
            
            # Check if quiz is complete
            current_question = quiz_state.get('current_question', 0)
            if question_idx == current_question:
                # This was the current question, advance to next
                if self.state_manager.advance_to_next_question(chat_id):
                    # More questions available
                    next_question = self.get_current_question(chat_id)
                    result['next_question'] = next_question
                    result['quiz_complete'] = False
                else:
                    # Quiz is complete
                    result['quiz_complete'] = True
                    result['final_leaderboard'] = self.get_leaderboard(chat_id)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing answer for chat {chat_id}: {e}")
            return {
                'success': False,
                'error': 'An error occurred while processing your answer.',
                'error_type': 'system_error'
            }
    
    def get_leaderboard(self, chat_id: int) -> Dict[str, Any]:
        """
        Get current leaderboard for active quiz
        
        Args:
            chat_id: Telegram chat ID
            
        Returns:
            Dictionary with leaderboard data or error information
        """
        try:
            if not self.is_quiz_active(chat_id):
                return {
                    'success': False,
                    'error': 'No active quiz in this chat.',
                    'error_type': 'no_quiz'
                }
            
            # Get leaderboard data
            leaderboard_data = self.state_manager.get_leaderboard_data(chat_id)
            quiz_status = self.state_manager.get_quiz_status(chat_id)
            
            return {
                'success': True,
                'leaderboard': leaderboard_data,
                'quiz_info': {
                    'subject': quiz_status.get('subject', 'Unknown'),
                    'difficulty': quiz_status.get('difficulty', 'medium'),
                    'total_questions': quiz_status.get('total_questions', 0),
                    'answered_questions': quiz_status.get('answered_questions', 0),
                    'participants': quiz_status.get('participants', 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting leaderboard for chat {chat_id}: {e}")
            return {
                'success': False,
                'error': 'Failed to retrieve leaderboard.',
                'error_type': 'system_error'
            }
    
    def stop_quiz(self, chat_id: int) -> Dict[str, Any]:
        """
        Stop the active quiz in the specified chat
        
        Args:
            chat_id: Telegram chat ID
            
        Returns:
            Dictionary with final results or error information
        """
        try:
            if not self.is_quiz_active(chat_id):
                return {
                    'success': False,
                    'error': 'No active quiz in this chat.',
                    'error_type': 'no_quiz'
                }
            
            # Get final leaderboard before clearing
            final_leaderboard = self.get_leaderboard(chat_id)
            
            # Clear quiz state
            self.state_manager.clear_quiz_state(chat_id)
            
            logger.info(f"Quiz stopped for chat {chat_id}")
            
            return {
                'success': True,
                'final_leaderboard': final_leaderboard.get('leaderboard', []) if final_leaderboard['success'] else [],
                'quiz_info': final_leaderboard.get('quiz_info', {}) if final_leaderboard['success'] else {}
            }
            
        except Exception as e:
            logger.error(f"Error stopping quiz for chat {chat_id}: {e}")
            return {
                'success': False,
                'error': 'Failed to stop quiz.',
                'error_type': 'system_error'
            }
    
    def is_quiz_active(self, chat_id: int) -> bool:
        """
        Check if a quiz is currently active in the specified chat
        
        Args:
            chat_id: Telegram chat ID
            
        Returns:
            True if quiz is active, False otherwise
        """
        try:
            quiz_state = self.state_manager.load_quiz_state(chat_id)
            return quiz_state.get('active', False) if quiz_state else False
        except Exception as e:
            logger.error(f"Error checking quiz status for chat {chat_id}: {e}")
            return False
    
    def get_current_question(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """
        Get the current unanswered question for the active quiz
        
        Args:
            chat_id: Telegram chat ID
            
        Returns:
            Current question data or None if no active quiz/question
        """
        try:
            return self.state_manager.get_current_question(chat_id)
        except Exception as e:
            logger.error(f"Error getting current question for chat {chat_id}: {e}")
            return None
    
    def get_quiz_status(self, chat_id: int) -> Dict[str, Any]:
        """
        Get detailed status information about the current quiz
        
        Args:
            chat_id: Telegram chat ID
            
        Returns:
            Dictionary with quiz status information
        """
        try:
            return self.state_manager.get_quiz_status(chat_id)
        except Exception as e:
            logger.error(f"Error getting quiz status for chat {chat_id}: {e}")
            return {'active': False}
    
    def _validate_quiz_parameters(self, subject: str, num_questions: int, difficulty: str) -> Dict[str, Any]:
        """
        Validate and normalize quiz creation parameters
        
        Args:
            subject: Quiz subject/topic
            num_questions: Number of questions
            difficulty: Difficulty level
            
        Returns:
            Dictionary with validation results and normalized values
        """
        result = {'valid': True, 'error': None}
        
        # Validate subject
        if not subject or not subject.strip():
            result['valid'] = False
            result['error'] = 'Subject cannot be empty. Please provide a topic for the quiz.'
            return result
        
        subject = subject.strip()
        if len(subject) > 100:
            result['valid'] = False
            result['error'] = 'Subject is too long. Please keep it under 100 characters.'
            return result
        
        # Validate number of questions
        if not isinstance(num_questions, int):
            try:
                num_questions = int(num_questions)
            except (ValueError, TypeError):
                num_questions = 5  # Default
        
        if num_questions < 1:
            num_questions = 5
        elif num_questions > 20:
            num_questions = 20
        
        # Validate difficulty
        valid_difficulties = ['easy', 'medium', 'hard', 'expert']
        if not difficulty or difficulty.lower() not in valid_difficulties:
            difficulty = 'medium'  # Default
        else:
            difficulty = difficulty.lower()
        
        result.update({
            'subject': subject,
            'num_questions': num_questions,
            'difficulty': difficulty
        })
        
        return result
    
    def get_help_text(self) -> str:
        """
        Get comprehensive help text for quiz commands
        
        Returns:
            Formatted help text string
        """
        return """🎯 **Quiz Commands Help**

**Start a New Quiz:**
`/quiz_new [Subject] [Number] [Difficulty]`

• **Subject**: Topic for the quiz (required)
• **Number**: Number of questions (1-20, default: 5)
• **Difficulty**: easy, medium, hard, expert (default: medium)

**Examples:**
• `/quiz_new World History 10 hard`
• `/quiz_new Python Programming 5`
• `/quiz_new Science`

**Other Commands:**
• `/quiz_leaderboard` - Show current scores
• `/quiz_stop` - End the current quiz
• `/quiz_help` - Show this help message

**How to Play:**
1. Someone starts a quiz with `/quiz_new`
2. Questions appear with multiple choice buttons
3. Click your answer quickly - first correct answer wins!
4. Earn 1 point for each correct answer
5. View scores anytime with `/quiz_leaderboard`

**Rules:**
• Only one quiz per chat at a time
• First person to answer correctly gets the point
• Quiz ends when all questions are answered or someone uses `/quiz_stop`

Have fun! 🎉"""