"""
Quiz UI - Handles all Telegram UI interactions
"""

import logging

logger = logging.getLogger(__name__)


class QuizUI:
    """Handles all Telegram UI interactions"""
    
    def __init__(self, bot_instance):
        """Initialize with bot instance"""
        self.bot_instance = bot_instance
        logger.info("QuizUI initialized")
    
    def send_question(self, chat_id: int, question_data: dict, question_num: int) -> int:
        """Send question with inline keyboard to chat"""
        # Implementation will be added in later tasks
        return 0
    
    def update_question_result(self, chat_id: int, message_id: int, result: str) -> None:
        """Update question message with result"""
        # Implementation will be added in later tasks
        pass
    
    def send_leaderboard(self, chat_id: int, scores: dict, is_final: bool) -> None:
        """Send leaderboard message to chat"""
        # Implementation will be added in later tasks
        pass
    
    def send_quiz_help(self, chat_id: int) -> None:
        """Send quiz help message to chat"""
        # Implementation will be added in later tasks
        pass