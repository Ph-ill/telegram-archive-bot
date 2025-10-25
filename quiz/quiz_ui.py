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
    
    def send_question(self, chat_id: int, question_data: Dict[str, Any], question_num: int, 
                     total_questions: int, previous_result: str = None) -> Optional[int]:
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
            
            # Format the question message with options and previous result
            message_text = self._format_question_message(question_text, question_num, total_questions, options, previous_result)
            
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
                message_id = response['message_id']
                logger.debug(f"Question {question_num} sent to chat {chat_id}, message_id: {message_id}")
                
                # Track message ID for later deletion
                try:
                    from .state_manager import QuizStateManager
                    import os
                    data_dir = '/app/data' if os.path.exists('/app/data') else '/app'
                    quiz_data_path = os.path.join(data_dir, 'quiz_data.json')
                    state_manager = QuizStateManager(quiz_data_path)
                    state_manager.add_message_id(chat_id, message_id)
                except Exception as e:
                    logger.warning(f"Failed to track message ID {message_id}: {e}")
                
                return message_id
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
                        quiz_info: Dict[str, Any] = None, is_final: bool = False, 
                        leaderboard_type: str = 'current_quiz') -> Optional[int]:
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
            is_persistent = (leaderboard_type == 'persistent')
            message_text = self._format_leaderboard_message(leaderboard_data, quiz_info, is_final, is_persistent)
            
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
                parse_mode='Markdown',
                disable_web_page_preview=True
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
                message_id = response['message_id']
                logger.debug(f"Quiz progress sent to chat {chat_id}, message_id: {message_id}")
                
                # Track message ID for later deletion
                try:
                    from .state_manager import QuizStateManager
                    import os
                    data_dir = '/app/data' if os.path.exists('/app/data') else '/app'
                    quiz_data_path = os.path.join(data_dir, 'quiz_data.json')
                    state_manager = QuizStateManager(quiz_data_path)
                    state_manager.add_message_id(chat_id, message_id)
                except Exception as e:
                    logger.warning(f"Failed to track message ID {message_id}: {e}")
                
                return message_id
            else:
                logger.warning(f"Failed to send quiz progress to chat {chat_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error sending quiz progress to chat {chat_id}: {e}")
            return None
    
    def _format_question_message(self, question_text: str, question_num: int, total_questions: int, 
                               options: List[str] = None, previous_result: str = None) -> str:
        """
        Format a question message with proper styling and answer options
        
        Args:
            question_text: The question text
            question_num: Current question number (1-based)
            total_questions: Total number of questions
            options: List of answer options to display
            previous_result: Result from previous question (if any)
            
        Returns:
            Formatted message text
        """
        message = ""
        
        # Add previous result if provided
        if previous_result:
            message += f"{previous_result}\n\n"
        
        message += f"❓ **Question {question_num}/{total_questions}**\n"
        message += f"{question_text}\n\n"
        
        if options:
            for i, option in enumerate(options):
                letter = chr(65 + i)  # A, B, C, D
                message += f"**{letter})** {option}\n"
        
        return message
    
    def _format_leaderboard_message(self, leaderboard_data: List[Dict[str, Any]], 
                                  quiz_info: Dict[str, Any], is_final: bool = False, is_persistent: bool = False) -> str:
        """
        Format leaderboard message with proper styling
        
        Args:
            leaderboard_data: List of user scores
            quiz_info: Quiz information
            is_final: Whether this is the final leaderboard
            is_persistent: Whether this is the persistent all-time leaderboard
            
        Returns:
            Formatted leaderboard message
        """
        if is_persistent:
            title = "🏆 **All-Time Quiz Champions**"
        elif is_final:
            title = "🏆 **Final Results**"
        else:
            title = "📊 **Current Leaderboard**"
        
        message = f"{title}\n\n"
        
        if is_persistent:
            message += "**Top quiz winners across all games**\n\n"
        else:
            # Add quiz info for current/final quiz
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
            if is_persistent:
                message += "No quiz winners yet! Be the first to win a quiz! 🏆"
            else:
                message += "No participants yet! 🤷‍♂️"
        else:
            # Medals for top 3
            medals = ["🥇", "🥈", "🥉"]
            
            for i, player in enumerate(leaderboard_data):
                rank = i + 1
                username = player.get('username', 'Unknown')
                
                if is_persistent:
                    # Show quiz wins and win rate for persistent leaderboard
                    quiz_wins = player.get('quiz_wins', 0)
                    win_rate = player.get('win_rate', 0)
                    total_points = player.get('total_points', 0)
                    
                    if rank <= 3 and len(leaderboard_data) > 1:
                        medal = medals[rank - 1]
                        message += f"{medal} **{rank}.** {username}\n"
                    else:
                        message += f"**{rank}.** {username}\n"
                    
                    message += f"    🏆 {quiz_wins} wins • 📊 {win_rate}% win rate • ⭐ {total_points} total points\n"
                else:
                    # Show current quiz points
                    points = player.get('points', 0)
                    
                    if rank <= 3 and len(leaderboard_data) > 1:
                        medal = medals[rank - 1]
                        message += f"{medal} **{rank}.** {username} - {points} points\n"
                    else:
                        message += f"**{rank}.** {username} - {points} points\n"
        
        if is_final:
            message += "\n🎉 Thanks for playing!"
        elif is_persistent:
            message += "\n💡 Win quizzes to climb the leaderboard!"
        
        return message
    
    def _create_question_keyboard(self, chat_id: int, question_idx: int, options: List[str]) -> Dict[str, Any]:
        """
        Create inline keyboard for question options with simple A, B, C, D buttons
        
        Args:
            chat_id: Telegram chat ID
            question_idx: Question index
            options: List of answer options
            
        Returns:
            Inline keyboard markup dictionary
        """
        keyboard = []
        
        # Create simple letter buttons (2 per row for better layout)
        for i in range(0, len(options), 2):
            row = []
            
            # First button in row
            letter = chr(65 + i)  # A, B, C, D
            callback_data = f"quiz_{chat_id}_{question_idx}_{i}"
            row.append({
                "text": letter,
                "callback_data": callback_data
            })
            
            # Second button in row (if exists)
            if i + 1 < len(options):
                letter = chr(65 + i + 1)  # B, C, D
                callback_data = f"quiz_{chat_id}_{question_idx}_{i + 1}"
                row.append({
                    "text": letter,
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
            'already_attempted': '🚫',
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
    
    def send_final_results(self, chat_id: int, leaderboard_data: List[Dict[str, Any]], 
                          quiz_info: Dict[str, Any], last_result: str = None) -> Optional[int]:
        """
        Send final quiz results with winner announcement
        
        Args:
            chat_id: Telegram chat ID
            leaderboard_data: Final leaderboard data
            quiz_info: Quiz information
            last_result: Result from the last question (optional)
            
        Returns:
            Message ID of sent message, or None if failed
        """
        try:
            message = ""
            
            # Add last result if provided
            if last_result:
                message += f"{last_result}\n\n"
            
            message += "🏁 **Quiz Complete!**\n\n"
            
            if leaderboard_data and len(leaderboard_data) > 0:
                winner = leaderboard_data[0]
                winner_points = winner.get('points', 0)
                
                # Show winner announcement if there's a clear winner with points
                if winner_points > 0:
                    if len(leaderboard_data) > 1:
                        # Multiple participants - show winner
                        message += f"🎉 **WINNER: {winner['username']}!** 🎉\n"
                        message += f"🏆 Final Score: {winner_points} points\n\n"
                        
                        # Check if there's a tie for first place
                        tied_winners = [p for p in leaderboard_data if p.get('points', 0) == winner_points]
                        if len(tied_winners) > 1:
                            tied_names = [p['username'] for p in tied_winners]
                            message = message.replace("WINNER:", "TIE FOR FIRST:")
                            message = message.replace(f"{winner['username']}!", f"{', '.join(tied_names)}!")
                    else:
                        # Solo player
                        message += f"🎯 **Solo Victory: {winner['username']}!**\n"
                        message += f"📊 Final Score: {winner_points} points\n\n"
                
                # Show final leaderboard (top 5)
                message += "📊 **Final Leaderboard:**\n"
                medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
                
                for i, player in enumerate(leaderboard_data[:5]):
                    rank = i + 1
                    username = player.get('username', 'Unknown')
                    points = player.get('points', 0)
                    
                    if rank <= len(medals):
                        medal = medals[rank - 1]
                        message += f"{medal} {username} - {points} points\n"
                    else:
                        message += f"{rank}. {username} - {points} points\n"
                
                if len(leaderboard_data) > 5:
                    message += f"... and {len(leaderboard_data) - 5} more players\n"
                    
            else:
                message += "🤷‍♂️ No participants scored points.\n"
            
            # Add quiz info
            subject = quiz_info.get('subject', 'Unknown')
            difficulty = quiz_info.get('difficulty', 'medium')
            total_questions = quiz_info.get('total_questions', 0)
            
            message += f"\n📚 **Quiz:** {subject} ({difficulty.title()})\n"
            message += f"❓ **Questions:** {total_questions}\n"
            message += f"👥 **Participants:** {len(leaderboard_data) if leaderboard_data else 0}\n"
            message += "\n🎉 Thanks for playing! Use /quiz_new to start another quiz!"
            
            response = self.bot_instance.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='Markdown'
            )
            
            if response and 'message_id' in response:
                logger.info(f"Final results with winner announcement sent to chat {chat_id}")
                return response['message_id']
            else:
                logger.warning(f"Failed to send final results to chat {chat_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error sending final results to chat {chat_id}: {e}")
            return None
    
    def delete_quiz_messages(self, chat_id: int, message_ids: List[int]) -> int:
        """
        Delete quiz-related messages (questions, progress, etc.)
        
        Args:
            chat_id: Telegram chat ID
            message_ids: List of message IDs to delete
            
        Returns:
            Number of messages successfully deleted
        """
        deleted_count = 0
        
        for message_id in message_ids:
            try:
                success = self.bot_instance.delete_message(chat_id, message_id)
                if success:
                    deleted_count += 1
                    logger.debug(f"Deleted message {message_id} from chat {chat_id}")
                else:
                    logger.warning(f"Failed to delete message {message_id} from chat {chat_id}")
            except Exception as e:
                logger.warning(f"Error deleting message {message_id} from chat {chat_id}: {e}")
                continue
        
        logger.info(f"Deleted {deleted_count}/{len(message_ids)} quiz messages from chat {chat_id}")
        return deleted_count