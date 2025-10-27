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
    
    def create_quiz(self, chat_id: int, subject: str, num_questions: int, difficulty: str, 
                   mode: str, creator_id: int, creator_name: str) -> Dict[str, Any]:
        """
        Create a new quiz for the specified chat
        
        Args:
            chat_id: Telegram chat ID
            subject: Quiz subject/topic
            num_questions: Number of questions to generate
            difficulty: Difficulty level (easy, medium, hard, expert)
            mode: Quiz mode ('solo' or 'multi')
            creator_id: User ID of quiz creator
            creator_name: Username of quiz creator
            
        Returns:
            Dictionary with success status and message/error details
        """
        try:
            # Check if quiz is already active and stop it automatically
            previous_quiz_stopped = False
            if self.is_quiz_active(chat_id):
                logger.info(f"Stopping previous quiz in chat {chat_id} to start new one")
                
                stop_result = self.stop_quiz(chat_id, record_win=False)  # Don't record win for interrupted quiz
                if stop_result['success']:
                    previous_quiz_stopped = True
                    logger.info(f"Successfully stopped previous quiz in chat {chat_id}")
                else:
                    logger.warning(f"Failed to stop previous quiz in chat {chat_id}: {stop_result.get('error', 'Unknown error')}")
                    # Continue anyway - try to start new quiz
            
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
            
            # Create quiz state with mode and creator info
            quiz_state = self.state_manager.create_quiz_state_template(subject, difficulty, questions, mode, creator_id, creator_name)
            
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
                'previous_quiz_stopped': previous_quiz_stopped,
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
            
            # Get quiz mode and creator info
            mode = quiz_state.get('mode', 'multi')
            creator_id = quiz_state.get('creator_id')
            
            # Check if user has already attempted this question (only in multi mode)
            if mode == 'multi':
                already_attempted = self.state_manager.check_user_attempted_question(chat_id, question_idx, user_id)
                logger.info(f"ATTEMPT CHECK: chat_id={chat_id}, user_id={user_id}, question_idx={question_idx}, mode={mode}, already_attempted={already_attempted}")
                if already_attempted:
                    logger.info(f"BLOCKING REPEAT ATTEMPT: User {user_id} already attempted question {question_idx}")
                    return {
                        'success': False,
                        'error': 'You have already attempted this question.',
                        'error_type': 'already_attempted'
                    }
            
            # Mark user as having attempted this question (only in multi mode)
            if mode == 'multi':
                logger.info(f"MARKING ATTEMPT: chat_id={chat_id}, user_id={user_id}, question_idx={question_idx}")
                self.state_manager.mark_user_attempted_question(chat_id, question_idx, user_id)
            
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
            
            # Always record the answer for scoring purposes
            if is_correct:
                self.state_manager.update_scores(chat_id, user_id, username, 1)
                result['points_awarded'] = 1
                logger.info(f"User {username} ({user_id}) answered question {question_idx} correctly in chat {chat_id}")
            else:
                result['points_awarded'] = 0
                logger.info(f"User {username} ({user_id}) answered question {question_idx} incorrectly in chat {chat_id}")
            
            # Determine if quiz should advance based on mode
            should_advance = False
            current_question = quiz_state.get('current_question', 0)
            
            if question_idx == current_question:
                if mode == 'solo':
                    # In solo mode, advance only if the creator answered (correct or incorrect)
                    should_advance = (user_id == creator_id)
                    logger.info(f"Solo mode: user_id={user_id}, creator_id={creator_id}, should_advance={should_advance}")
                elif mode == 'multi':
                    # In multi mode, advance only if someone answered correctly
                    should_advance = is_correct
                    logger.info(f"Multi mode: is_correct={is_correct}, should_advance={should_advance}")
                
                if should_advance:
                    # Mark question as answered and advance
                    self.state_manager.mark_question_answered(chat_id, question_idx, answer)
                    
                    logger.info(f"Attempting to advance to next question for chat {chat_id}")
                    if self.state_manager.advance_to_next_question(chat_id):
                        # More questions available
                        logger.info(f"Advanced to next question for chat {chat_id}")
                        next_question = self.get_current_question(chat_id)
                        result['next_question'] = next_question
                        result['quiz_complete'] = False
                    else:
                        # Quiz is complete - record win and get final results
                        logger.info(f"Quiz completed for chat {chat_id}, stopping quiz")
                        try:
                            final_results = self.stop_quiz(chat_id, record_win=True)
                            logger.info(f"stop_quiz returned: {final_results}")
                        except Exception as e:
                            logger.error(f"Error in stop_quiz for chat {chat_id}: {e}")
                            import traceback
                            logger.error(f"Traceback: {traceback.format_exc()}")
                            final_results = {'success': False, 'final_leaderboard': [], 'quiz_info': {}}
                        
                        result['quiz_complete'] = True
                        result['final_leaderboard'] = {
                            'success': final_results['success'],
                            'leaderboard': final_results.get('final_leaderboard', []),
                            'quiz_info': final_results.get('quiz_info', {})
                        }
                        logger.info(f"Quiz completion result for chat {chat_id}: {result['quiz_complete']}")
                else:
                    # Don't advance - stay on current question
                    result['quiz_complete'] = False
                    logger.info(f"Not advancing question for chat {chat_id} (mode={mode}, should_advance={should_advance})")
            else:
                logger.warning(f"Question {question_idx} answered but current_question is {current_question}")
                result['quiz_complete'] = False
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing answer for chat {chat_id}: {e}")
            return {
                'success': False,
                'error': 'An error occurred while processing your answer.',
                'error_type': 'system_error'
            }
    
    def skip_question(self, chat_id: int, user_id: int) -> Dict[str, Any]:
        """
        Skip the current question (only allowed if everyone got it wrong in multi mode, or anytime in solo mode)
        
        Args:
            chat_id: Telegram chat ID
            user_id: User ID requesting the skip
            
        Returns:
            Dictionary with skip results and next actions
        """
        try:
            logger.info(f"SKIP_DEBUG: skip_question called for chat_id={chat_id}, user_id={user_id}")
            
            # Check if quiz is active
            if not self.is_quiz_active(chat_id):
                logger.info(f"SKIP_DEBUG: No active quiz in chat {chat_id}")
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
            
            mode = quiz_state.get('mode', 'multi')
            creator_id = quiz_state.get('creator_id')
            current_question_idx = quiz_state.get('current_question', 0)
            questions = quiz_state.get('questions', [])
            
            # Validate current question
            if current_question_idx >= len(questions):
                return {
                    'success': False,
                    'error': 'No current question to skip.',
                    'error_type': 'invalid_question'
                }
            
            # Check permissions based on mode
            logger.info(f"SKIP_DEBUG: mode={mode}, user_id={user_id}, creator_id={creator_id}")
            if mode == 'solo' and user_id != creator_id:
                logger.info(f"SKIP_DEBUG: Permission denied - only creator can skip in solo mode")
                return {
                    'success': False,
                    'error': 'Only the quiz creator can skip questions in solo mode.',
                    'error_type': 'permission_denied'
                }
            
            # Get username for the skip message
            username = 'Unknown'
            scores = quiz_state.get('scores', {})
            for uid, user_data in scores.items():
                if int(uid) == user_id:
                    username = user_data.get('username', 'Unknown')
                    break
            
            # Mark current question as answered (skipped)
            self.state_manager.mark_question_answered(chat_id, current_question_idx, "SKIPPED")
            
            # Advance to next question
            if self.state_manager.advance_to_next_question(chat_id):
                # More questions available
                next_question = self.get_current_question(chat_id)
                return {
                    'success': True,
                    'next_question': next_question,
                    'quiz_complete': False,
                    'username': username,
                    'message': f'Question skipped by {username}.'
                }
            else:
                # Quiz is complete
                final_results = self.stop_quiz(chat_id, record_win=True)
                return {
                    'success': True,
                    'quiz_complete': True,
                    'final_leaderboard': {
                        'success': final_results['success'],
                        'leaderboard': final_results.get('final_leaderboard', []),
                        'quiz_info': final_results.get('quiz_info', {})
                    },
                    'username': username,
                    'message': f'Quiz completed after skip by {username}.'
                }
                
        except Exception as e:
            logger.error(f"Error skipping question for chat {chat_id}: {e}")
            return {
                'success': False,
                'error': 'An error occurred while skipping the question.',
                'error_type': 'system_error'
            }

    def get_leaderboard(self, chat_id: int) -> Dict[str, Any]:
        """
        Get leaderboard - current quiz if active, otherwise persistent leaderboard
        
        Args:
            chat_id: Telegram chat ID
            
        Returns:
            Dictionary with leaderboard data or error information
        """
        try:
            if self.is_quiz_active(chat_id):
                # Get current quiz leaderboard
                leaderboard_data = self.state_manager.get_leaderboard_data(chat_id)
                quiz_status = self.state_manager.get_quiz_status(chat_id)
                
                return {
                    'success': True,
                    'type': 'current_quiz',
                    'leaderboard': leaderboard_data,
                    'quiz_info': {
                        'subject': quiz_status.get('subject', 'Unknown'),
                        'difficulty': quiz_status.get('difficulty', 'medium'),
                        'total_questions': quiz_status.get('total_questions', 0),
                        'answered_questions': quiz_status.get('answered_questions', 0),
                        'participants': quiz_status.get('participants', 0)
                    }
                }
            else:
                # Get persistent leaderboard
                persistent_leaderboard = self.state_manager.get_persistent_leaderboard()
                
                return {
                    'success': True,
                    'type': 'persistent',
                    'leaderboard': persistent_leaderboard
                }
            
        except Exception as e:
            logger.error(f"Error getting leaderboard for chat {chat_id}: {e}")
            return {
                'success': False,
                'error': 'Failed to retrieve leaderboard.',
                'error_type': 'system_error'
            }
    
    def stop_quiz(self, chat_id: int, record_win: bool = True) -> Dict[str, Any]:
        """
        Stop the active quiz in the specified chat
        
        Args:
            chat_id: Telegram chat ID
            record_win: Whether to record the win in persistent leaderboard
            
        Returns:
            Dictionary with final results or error information
        """
        try:
            # Note: We don't check is_quiz_active here because this method is called
            # immediately after the quiz becomes inactive (when the last question is answered)
            quiz_state = self.state_manager.load_quiz_state(chat_id)
            if not quiz_state:
                return {
                    'success': False,
                    'error': 'No quiz state found for this chat.',
                    'error_type': 'no_quiz'
                }
            
            # Get final leaderboard and quiz info before clearing
            # Note: We need to get this directly since the quiz might already be marked inactive
            logger.info(f"Getting final leaderboard data for chat {chat_id}")
            leaderboard_data = self.state_manager.get_leaderboard_data(chat_id)
            quiz_status = self.state_manager.get_quiz_status(chat_id)
            quiz_state = self.state_manager.load_quiz_state(chat_id)
            
            logger.info(f"Retrieved data - leaderboard: {len(leaderboard_data) if leaderboard_data else 0} participants")
            logger.info(f"Quiz status: {quiz_status}")
            logger.info(f"Quiz state active: {quiz_state.get('active') if quiz_state else 'No state'}")
            
            final_leaderboard = {
                'success': True,
                'type': 'current_quiz',
                'leaderboard': leaderboard_data,
                'quiz_info': {
                    'subject': quiz_status.get('subject', 'Unknown'),
                    'difficulty': quiz_status.get('difficulty', 'medium'),
                    'total_questions': quiz_status.get('total_questions', 0),
                    'answered_questions': quiz_status.get('answered_questions', 0),
                    'participants': quiz_status.get('participants', 0)
                }
            }
            
            logger.info(f"Final leaderboard for chat {chat_id}: {len(leaderboard_data)} participants, quiz_info: {final_leaderboard['quiz_info']}")
            
            # Record win if appropriate
            if (record_win and final_leaderboard['success'] and 
                final_leaderboard.get('leaderboard') and
                self.state_manager.check_quiz_has_multiple_participants(chat_id)):
                
                # Get the winner (highest score)
                winner = final_leaderboard['leaderboard'][0]
                quiz_info = final_leaderboard.get('quiz_info', {})
                
                if winner['points'] > 0:  # Only record if winner actually scored
                    self.state_manager.record_quiz_win(
                        winner_user_id=winner['user_id'],
                        winner_username=winner['username'],
                        quiz_subject=quiz_info.get('subject', 'Unknown'),
                        total_participants=len(final_leaderboard['leaderboard']),
                        winner_score=winner['points'],
                        total_questions=quiz_info.get('total_questions', 0)
                    )
                    logger.info(f"Recorded quiz win for {winner['username']} in chat {chat_id}")
            
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
        return """🎯 <b>Quiz Commands Help</b>

<blockquote expandable><b>Start a New Quiz:</b>
<code>/quiz_new [mode] [topic] [questions] [difficulty]</code>

• <b>Mode</b>: solo or multi (required)
• <b>Topic</b>: Subject for the quiz (required)
• <b>Questions</b>: Number of questions (1-20, default: 5)
• <b>Difficulty</b>: easy, medium, hard, expert (default: medium)

<b>Examples:</b>
• <code>/quiz_new multi World History 10 hard</code>
• <code>/quiz_new solo Python Programming 5 medium</code>
• <code>/quiz_new multi Science</code>

<b>Other Commands:</b>
• <code>/quiz_leaderboard</code> - Show current scores
• <code>/quiz_stop</code> - End the current quiz
• <code>/quiz_skip</code> - Skip current question (conditions apply)
• <code>/quiz_help</code> - Show this help message

<b>Quiz Modes:</b>

<b>🎯 Solo Mode:</b>
• Quiz creator controls progression
• Anyone can answer and earn points
• Quiz advances only when creator answers (right or wrong)
• Creator can skip questions anytime with <code>/quiz_skip</code>
• Final results show everyone's scores

<b>👥 Multi Mode:</b>
• Traditional competitive mode
• Each player gets one attempt per question
• Quiz advances only when someone answers correctly
• If everyone gets it wrong, anyone can use <code>/quiz_skip</code>
• First correct answer wins the point

<b>How to Play:</b>
1. Someone starts a quiz with <code>/quiz_new [mode] [topic]</code>
2. Questions appear with answer options (A, B, C, D) and buttons
3. Click your chosen answer button
4. Quiz progression depends on the mode selected
5. View scores anytime with <code>/quiz_leaderboard</code>

<b>Rules:</b>
• Only one quiz per chat at a time
• In multi mode: one attempt per player per question
• In solo mode: unlimited attempts, but only creator advances quiz
• Quiz ends when all questions are answered or someone uses <code>/quiz_stop</code>

<b>Strategy Tips:</b>
• Choose your mode based on group preference
• Solo mode is great for learning/practice
• Multi mode is perfect for competition
• Read questions carefully - you might only get one shot!

Have fun! 🎉</blockquote>"""