#!/usr/bin/env python3

import sys
import os

# Add current directory to Python path
sys.path.insert(0, '.')

print("Testing QuizStateManager import...")

try:
    from quiz.state_manager import QuizStateManager
    print("✓ QuizStateManager imported successfully")
    
    # Create a simple test
    import tempfile
    temp_dir = tempfile.mkdtemp()
    test_file = os.path.join(temp_dir, 'test.json')
    
    print(f"Creating QuizStateManager with file: {test_file}")
    manager = QuizStateManager(test_file)
    print("✓ QuizStateManager created successfully")
    
    # Test basic functionality
    chat_id = 12345
    quiz_data = {
        'active': True,
        'subject': 'Test Subject',
        'difficulty': 'medium',
        'questions': [
            {
                'question_text': 'What is 2+2?',
                'options': ['3', '4', '5', '6'],
                'correct_answer': '4',
                'answered': False,
                'answered_by': None
            }
        ],
        'current_question': 0,
        'scores': {},
        'created_at': '2024-01-01T00:00:00',
        'message_ids': []
    }
    
    print("Testing save_quiz_state...")
    manager.save_quiz_state(chat_id, quiz_data)
    print("✓ Quiz state saved")
    
    print("Testing load_quiz_state...")
    loaded_data = manager.load_quiz_state(chat_id)
    print(f"✓ Quiz state loaded: {loaded_data.get('subject', 'MISSING')}")
    
    print("Testing validate_quiz_state...")
    is_valid = manager.validate_quiz_state(quiz_data)
    print(f"✓ Quiz state validation: {is_valid}")
    
    # Cleanup
    os.remove(test_file)
    os.rmdir(temp_dir)
    
    print("✓ All basic tests passed!")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()