"""
Quiz UI - Handles all Telegram UI interactions for the quiz module
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class QuizUI:
    """Handles all Telegram UI interactions for quiz display and formatting"""
    
    def __init__(self, bot_instance):
        """Initialize QuizUI with bot instance"""
        self.bot_instance = bot_instance
        logger.info("QuizUI initialized")
    
    def send_question(self, chat_id: int, question_data: Dict[str, Any], question_num: int, total_questions: int) -> Optional[int]:
        """
        Send a quiz question with inline keyboard buttons
        
        Args:
            chat_id: Telegram chat ID
            question_data: Question data with text, options, etc.
            question_num: Current question number (1-based)
            total_questions: Total number of questions in quiz
            
        Returns:
            Message ID of sent message, or None if failed
        """
        try:
            question_text = question_data.get('question_text', '')
            options = question_data.get('options', [])
            question_idx = question_data.get('question_index', question_num - 1)
            
            if not question_text or not options:
                logger.error(f"Invalid question data for chat {chat_id}")
                return None
            
            # Format the question message
            message_text = self._format_question_message(question_text, question_num, total_questions)
            
            # Create inline keyboard
            keyboard = self._create_question_keyboard(chat_id, question_idx, options)
            
            # Send message with keyboard
            response = self.bot_instance.send_message(
                chat_id=chat_id,
                text=message_text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
            if response and 'message_id' in response:
                logger.debug(f"Question {question_num} sent to chat {chat_id}, message_id: {response['message_id']}")
                return response['message_id']
            else:
                logger.warning(f"Failed to send question {question_num} to chat {chat_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error sending question to chat {chat_id}: {e}")
            return None
    
    def update_question_result(self, chat_id: int, message_id: int, result_data: Dict[str, Any]) -> bool:
        """
        Update a question message with the result after someone answers
        
        Args:
            chat_id: Telegram chat ID
            message_id: Message ID of the question to update
            result_data: Result information including correct answer, winner, etc.
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            is_correct = result_data.get('is_correct', False)
            correct_answer = result_data.get('correct_answer', '')
            username = result_data.get('username', 'Unknown')
            points_awarded = result_data.get('points_awarded', 0)
            
            # Format result message
            if is_correct:
                result_text = f"✅ **Correct!** {username} got it right!\n"
                result_text += f"**Answer:** {correct_answer}\n"
                result_text += f"**Points awarded:** {points_awarded}"
            else:
                result_text = f"❌ **Incorrect!** {username} answered wrong.\n"
                result_text += f"**Correct answer:** {correct_answer}"
            
            # Update message (remove keyboard)
            response = self.bot_instance.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=result_text,
                parse_mode='Markdown'
            )
            
            if response:
                logger.debug(f"Question result updated for message {message_id} in chat {chat_id}")
                return True
            else:
                logger.warning(f"Failed to update question result for message {message_id} in chat {chat_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating question result for chat {chat_id}, message {message_id}: {e}")
            return False
    
    def send_leaderboard(self, chat_id: int, leaderboard_data: List[Dict[str, Any]], 
                        quiz_info: Dict[str, Any], is_final: bool = False) -> Optional[int]:
        """
        Send formatted leaderboard message
        
        Args:
            chat_id: Telegram chat ID
            leaderboard_data: List of user scores sorted by points
            quiz_info: Quiz information (subject, difficulty, etc.)
            is_final: Whether this is the final leaderboard
            
        Returns:
            Message ID of sent message, or None if failed
        """
        try:
            message_text = self._format_leaderboard_message(leaderboard_data, quiz_info, is_final)
            
            response = self.bot_instance.send_message(
                chat_id=chat_id,
                text=message_text,
                parse_mode='Markdown'
            )
            
            if response and 'message_id' in response:
                logger.debug(f"Leaderboard sent to chat {chat_id}, message_id: {response['message_id']}")
                return response['message_id']
            else:
                logger.warning(f"Failed to send leaderboard to chat {chat_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error sending leaderboard to chat {chat_id}: {e}")
            return None
    
    def send_quiz_help(self, chat_id: int, help_text: str) -> Optional[int]:
        """
        Send quiz help message
        
        Args:
            chat_id: Telegram chat ID
            help_text: Formatted help text
            
        Returns:
            Message ID of sent message, or None if failed
        """
        try:
            response = self.bot_instance.send_message(
                chat_id=chat_id,
                text=help_text,
                parse_mode='Markdown'
            )
            
            if response and 'message_id' in response:
                logger.debug(f"Quiz help sent to chat {chat_id}, message_id: {response['message_id']}")
                return response['message_id']
            else:
                logger.warning(f"Failed to send quiz help to chat {chat_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error sending quiz help to chat {chat_id}: {e}")
            return None
    
    def send_quiz_status(self, chat_id: int, status_message: str) -> Optional[int]:
        """
        Send quiz status or error message
        
        Args:
            chat_id: Telegram chat ID
            status_message: Status or error message to send
            
        Returns:
            Message ID of sent message, or None if failed
        """
        try:
            response = self.bot_instance.send_message(
                chat_id=chat_id,
                text=status_message,
                parse_mode='Markdown'
            )
            
            if response and 'message_id' in response:
                logger.debug(f"Quiz status sent to chat {chat_id}, message_id: {response['message_id']}")
                return response['message_id']
            else:
                logger.warning(f"Failed to send quiz status to chat {chat_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error sending quiz status to chat {chat_id}: {e}")
            return None
    
    def send_quiz_progress(self, chat_id: int, subject: str, num_questions: int, difficulty: str) -> Optional[int]:
        """
        Send quiz creation progress message
        
        Args:
            chat_id: Telegram chat ID
            subject: Quiz subject
            num_questions: Number of questions
            difficulty: Difficulty level
            
        Returns:
            Message ID of sent message, or None if failed
        """
        try:
            message_text = f"🎯 **Creating Quiz**\n\n"
            message_text += f"**Subject:** {subject}\n"
            message_text += f"**Questions:** {num_questions}\n"
            message_text += f"**Difficulty:** {difficulty.title()}\n\n"
            message_text += "⏳ Generating questions with AI... Please wait!"
            
            response = self.bot_instance.send_message(
                chat_id=chat_id,
                text=message_text,
                parse_mode='Markdown'
            )
            
            if response and 'message_id' in response:
                logger.debug(f"Quiz progress sent to chat {chat_id}, message_id: {response['message_id']}")
                return response['message_id']
            else:
                logger.warning(f"Failed to send quiz progress to chat {chat_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error sending quiz progress to chat {chat_id}: {e}")
            return None
    
    def _format_question_message(self, question_text: str, question_num: int, total_questions: int) -> str:
        """
        Format a question message with proper styling
        
        Args:
            question_text: The question text
            question_num: Current question number (1-based)
            total_questions: Total number of questions
            
        Returns:
            Formatted message text
        """
        message = f"❓ **Question {question_num}/{total_questions}**\n\n"
        message += f"> {question_text}\n\n"
        message += "👆 Choose your answer above!"
        return message
    
    def _format_leaderboard_message(self, leaderboard_data: List[Dict[str, Any]], 
                                  quiz_info: Dict[str, Any], is_final: bool = False) -> str:
        """
        Format leaderboard message with proper styling
        
        Args:
            leaderboard_data: List of user scores
            quiz_info: Quiz information
            is_final: Whether this is the final leaderboard
            
        Returns:
            Formatted leaderboard message
        """
        title = "🏆 **Final Results**" if is_final else "📊 **Current Leaderboard**"
        
        message = f"{title}\n\n"
        
        # Add quiz info
        subject = quiz_info.get('subject', 'Unknown')
        difficulty = quiz_info.get('difficulty', 'medium')
        total_questions = quiz_info.get('total_questions', 0)
        answered_questions = quiz_info.get('answered_questions', 0)
        
        message += f"**Quiz:** {subject} ({difficulty.title()})\n"
        if not is_final:
            message += f"**Progress:** {answered_questions}/{total_questions} questions\n"
        message += "\n"
        
        # Add leaderboard
        if not leaderboard_data:
            message += "No participants yet! 🤷‍♂️"
        else:
            # Medals for top 3
            medals = ["🥇", "🥈", "🥉"]
            
            for i, player in enumerate(leaderboard_data):
                rank = i + 1
                username = player.get('username', 'Unknown')
                points = player.get('points', 0)
                
                if rank <= 3 and len(leaderboard_data) > 1:
                    medal = medals[rank - 1]
                    message += f"{medal} **{rank}.** {username} - {points} points\n"
                else:
                    message += f"**{rank}.** {username} - {points} points\n"
        
        if is_final:
            message += "\n🎉 Thanks for playing!"
        
        return message
    
    def _create_question_keyboard(self, chat_id: int, question_idx: int, options: List[str]) -> Dict[str, Any]:
        """
        Create inline keyboard for question options
        
        Args:
            chat_id: Telegram chat ID
            question_idx: Question index
            options: List of answer options
            
        Returns:
            Inline keyboard markup dictionary
        """
        keyboard = []
        
        # Create buttons for each option (2 per row for better layout)
        for i in range(0, len(options), 2):
            row = []
            
            # First button in row
            option_text = options[i]
            callback_data = f"quiz_{chat_id}_{question_idx}_{i}"
            row.append({
                "text": f"A) {option_text}" if i == 0 else f"{'ABCD'[i]}) {option_text}",
                "callback_data": callback_data
            })
            
            # Second button in row (if exists)
            if i + 1 < len(options):
                option_text = options[i + 1]
                callback_data = f"quiz_{chat_id}_{question_idx}_{i + 1}"
                row.append({
                    "text": f"{'ABCD'[i + 1]}) {option_text}",
                    "callback_data": callback_data
                })
            
            keyboard.append(row)
        
        return {"inline_keyboard": keyboard}
    
    def parse_callback_data(self, callback_data: str) -> Optional[Dict[str, Any]]:
        """
        Parse quiz callback data from inline keyboard buttons
        
        Args:
            callback_data: Callback data string from button press
            
        Returns:
            Parsed data dictionary or None if invalid
        """
        try:
            if not callback_data.startswith('quiz_'):
                return None
            
            parts = callback_data.split('_')
            if len(parts) != 4:
                return None
            
            _, chat_id_str, question_idx_str, option_idx_str = parts
            
            return {
                'chat_id': int(chat_id_str),
                'question_idx': int(question_idx_str),
                'option_idx': int(option_idx_str)
            }
            
        except (ValueError, IndexError) as e:
            logger.warning(f"Invalid callback data format: {callback_data}, error: {e}")
            return None
    
    def format_error_message(self, error_type: str, error_message: str) -> str:
        """
        Format error messages with appropriate styling
        
        Args:
            error_type: Type of error
            error_message: Error message text
            
        Returns:
            Formatted error message
        """
        error_icons = {
            'quiz_active': '⚠️',
            'no_quiz': '❌',
            'validation': '⚠️',
            'api_error': '🔧',
            'system_error': '💥',
            'already_answered': '⏰',
            'invalid_question': '❓'
        }
        
        icon = error_icons.get(error_type, '❌')
        return f"{icon} **Error:** {error_message}"
    
    def format_success_message(self, message: str) -> str:
        """
        Format success messages with appropriate styling
        
        Args:
            message: Success message text
            
        Returns:
            Formatted success message
        """
        return f"✅ {message}"