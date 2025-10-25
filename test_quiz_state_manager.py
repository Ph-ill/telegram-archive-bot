"""
Unit tests for QuizStateManager - Thread-safe persistence and state management
Tests focus on:
1. Thread safety with concurrent access (Requirement 7.1, 7.2)
2. File corruption recovery (Requirement 7.1, 7.2) 
3. State validation and cleanup (Requirement 7.1, 7.2)
"""

import json
import os
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime
from unittest.mock import patch

# Add current directory to Python path for imports
sys.path.insert(0, '.')

from quiz.state_manager import QuizStateManager


class TestQuizStateManager(unittest.TestCase):
    """Test cases for QuizStateManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary file for testing
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, 'test_quiz_data.json')
        self.manager = QuizStateManager(self.test_file)
        
        # Sample quiz data for testing
        self.sample_quiz_data = {
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
            'created_at': datetime.now().isoformat(),
            'message_ids': []
        }
    
    def tearDown(self):
        """Clean up test fixtures"""
        # Remove test files
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        if os.path.exists(f"{self.test_file}.tmp"):
            os.remove(f"{self.test_file}.tmp")
        os.rmdir(self.temp_dir)
    
    def test_thread_safety_concurrent_save_load(self):
        """Test thread safety with concurrent save and load operations"""
        chat_id = 12345
        num_threads = 10
        operations_per_thread = 5
        results = []
        errors = []
        
        def worker_save_load(thread_id):
            """Worker function for concurrent save/load operations"""
            try:
                for i in range(operations_per_thread):
                    # Save quiz data
                    quiz_data = self.sample_quiz_data.copy()
                    quiz_data['subject'] = f'Thread {thread_id} Operation {i}'
                    self.manager.save_quiz_state(chat_id, quiz_data)
                    
                    # Load quiz data
                    loaded_data = self.manager.load_quiz_state(chat_id)
                    results.append((thread_id, i, loaded_data.get('subject', 'MISSING')))
                    
                    # Small delay to increase chance of race conditions
                    time.sleep(0.001)
            except Exception as e:
                errors.append(f"Thread {thread_id}: {str(e)}")
        
        # Start multiple threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=worker_save_load, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        self.assertEqual(len(errors), 0, f"Errors occurred during concurrent operations: {errors}")
        
        # Verify we got results from all threads
        self.assertEqual(len(results), num_threads * operations_per_thread)
        
        # Verify final state is consistent
        final_state = self.manager.load_quiz_state(chat_id)
        self.assertIsInstance(final_state, dict)
        self.assertIn('subject', final_state)
    
    def test_thread_safety_concurrent_score_updates(self):
        """Test thread safety with concurrent score updates"""
        chat_id = 12345
        num_threads = 5
        updates_per_thread = 10
        
        # Initialize quiz state
        self.manager.save_quiz_state(chat_id, self.sample_quiz_data)
        
        def worker_update_scores(thread_id):
            """Worker function for concurrent score updates"""
            for i in range(updates_per_thread):
                user_id = thread_id * 1000 + i  # Unique user IDs
                username = f"user_{thread_id}_{i}"
                self.manager.update_scores(chat_id, user_id, username, 1)
        
        # Start multiple threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=worker_update_scores, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify final scores
        final_state = self.manager.load_quiz_state(chat_id)
        scores = final_state.get('scores', {})
        
        # Should have exactly num_threads * updates_per_thread users
        self.assertEqual(len(scores), num_threads * updates_per_thread)
        
        # Each user should have exactly 1 point
        for user_data in scores.values():
            self.assertEqual(user_data['points'], 1)
    
    def test_thread_safety_concurrent_question_marking(self):
        """Test thread safety with concurrent question marking"""
        chat_id = 12345
        num_threads = 10
        
        # Initialize quiz state with multiple questions
        quiz_data = self.sample_quiz_data.copy()
        quiz_data['questions'] = [
            {
                'question_text': f'Question {i}?',
                'options': ['A', 'B', 'C', 'D'],
                'correct_answer': 'A',
                'answered': False,
                'answered_by': None
            }
            for i in range(5)
        ]
        self.manager.save_quiz_state(chat_id, quiz_data)
        
        results = []
        
        def worker_mark_question(thread_id):
            """Worker function for concurrent question marking"""
            # All threads try to mark the same question (index 0)
            result = self.manager.mark_question_answered(chat_id, 0, f"Thread {thread_id}")
            results.append((thread_id, result))
        
        # Start multiple threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=worker_mark_question, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify only one thread succeeded
        successful_marks = [r for r in results if r[1] is True]
        failed_marks = [r for r in results if r[1] is False]
        
        self.assertEqual(len(successful_marks), 1, "Only one thread should successfully mark the question")
        self.assertEqual(len(failed_marks), num_threads - 1, "All other threads should fail")
        
        # Verify question is marked as answered
        final_state = self.manager.load_quiz_state(chat_id)
        question = final_state['questions'][0]
        self.assertTrue(question['answered'])
        self.assertIsNotNone(question['answered_by'])
    
    def test_file_corruption_recovery_invalid_json(self):
        """Test recovery from invalid JSON file corruption"""
        chat_id = 12345
        
        # Write invalid JSON to file
        with open(self.test_file, 'w') as f:
            f.write('{"invalid": json content}')
        
        # Manager should handle corrupted file gracefully
        corrupted_manager = QuizStateManager(self.test_file)
        
        # Should return empty dict for corrupted data
        result = corrupted_manager.load_quiz_state(chat_id)
        self.assertEqual(result, {})
        
        # Should be able to save new data after corruption
        corrupted_manager.save_quiz_state(chat_id, self.sample_quiz_data)
        
        # Should be able to load the newly saved data
        loaded_data = corrupted_manager.load_quiz_state(chat_id)
        self.assertEqual(loaded_data['subject'], 'Test Subject')
    
    def test_file_corruption_recovery_empty_file(self):
        """Test recovery from empty file"""
        chat_id = 12345
        
        # Create empty file
        with open(self.test_file, 'w') as f:
            f.write('')
        
        # Manager should handle empty file gracefully
        empty_manager = QuizStateManager(self.test_file)
        
        # Should return empty dict for empty file
        result = empty_manager.load_quiz_state(chat_id)
        self.assertEqual(result, {})
        
        # Should be able to save new data
        empty_manager.save_quiz_state(chat_id, self.sample_quiz_data)
        loaded_data = empty_manager.load_quiz_state(chat_id)
        self.assertEqual(loaded_data['subject'], 'Test Subject')
    
    def test_file_corruption_recovery_non_dict_json(self):
        """Test recovery from JSON that's not a dictionary"""
        chat_id = 12345
        
        # Write valid JSON but not a dictionary
        with open(self.test_file, 'w') as f:
            json.dump(["not", "a", "dictionary"], f)
        
        # Manager should handle non-dict JSON gracefully
        non_dict_manager = QuizStateManager(self.test_file)
        
        # Should return empty dict for non-dict JSON
        result = non_dict_manager.load_quiz_state(chat_id)
        self.assertEqual(result, {})
        
        # Should be able to save new data
        non_dict_manager.save_quiz_state(chat_id, self.sample_quiz_data)
        loaded_data = non_dict_manager.load_quiz_state(chat_id)
        self.assertEqual(loaded_data['subject'], 'Test Subject')
    
    def test_atomic_write_operation(self):
        """Test that write operations are atomic"""
        chat_id = 12345
        
        # Mock os.rename to fail and verify temp file cleanup
        with patch('os.rename', side_effect=OSError("Simulated rename failure")):
            with self.assertRaises(OSError):
                self.manager.save_quiz_state(chat_id, self.sample_quiz_data)
            
            # Verify temp file doesn't exist after failure
            temp_file = f"{self.test_file}.tmp"
            self.assertFalse(os.path.exists(temp_file))
    
    def test_state_validation_valid_state(self):
        """Test validation of valid quiz state"""
        valid_state = self.sample_quiz_data.copy()
        result = self.manager.validate_quiz_state(valid_state)
        self.assertTrue(result)
    
    def test_state_validation_missing_required_fields(self):
        """Test validation fails for missing required fields"""
        invalid_states = [
            # Missing 'active'
            {k: v for k, v in self.sample_quiz_data.items() if k != 'active'},
            # Missing 'subject'
            {k: v for k, v in self.sample_quiz_data.items() if k != 'subject'},
            # Missing 'questions'
            {k: v for k, v in self.sample_quiz_data.items() if k != 'questions'},
        ]
        
        for invalid_state in invalid_states:
            result = self.manager.validate_quiz_state(invalid_state)
            self.assertFalse(result)
    
    def test_state_validation_invalid_field_types(self):
        """Test validation fails for invalid field types"""
        # Invalid active field (not boolean)
        invalid_state = self.sample_quiz_data.copy()
        invalid_state['active'] = "true"
        self.assertFalse(self.manager.validate_quiz_state(invalid_state))
        
        # Invalid subject field (empty string)
        invalid_state = self.sample_quiz_data.copy()
        invalid_state['subject'] = ""
        self.assertFalse(self.manager.validate_quiz_state(invalid_state))
        
        # Invalid difficulty
        invalid_state = self.sample_quiz_data.copy()
        invalid_state['difficulty'] = "invalid_difficulty"
        self.assertFalse(self.manager.validate_quiz_state(invalid_state))
        
        # Invalid questions (empty list)
        invalid_state = self.sample_quiz_data.copy()
        invalid_state['questions'] = []
        self.assertFalse(self.manager.validate_quiz_state(invalid_state))
        
        # Invalid current_question (negative)
        invalid_state = self.sample_quiz_data.copy()
        invalid_state['current_question'] = -1
        self.assertFalse(self.manager.validate_quiz_state(invalid_state))
    
    def test_state_validation_invalid_question_structure(self):
        """Test validation fails for invalid question structure"""
        # Missing question_text
        invalid_state = self.sample_quiz_data.copy()
        invalid_state['questions'][0] = {
            'options': ['A', 'B', 'C', 'D'],
            'correct_answer': 'A',
            'answered': False,
            'answered_by': None
        }
        self.assertFalse(self.manager.validate_quiz_state(invalid_state))
        
        # Correct answer not in options
        invalid_state = self.sample_quiz_data.copy()
        invalid_state['questions'][0]['correct_answer'] = 'Z'
        self.assertFalse(self.manager.validate_quiz_state(invalid_state))
        
        # Too few options
        invalid_state = self.sample_quiz_data.copy()
        invalid_state['questions'][0]['options'] = ['A']
        self.assertFalse(self.manager.validate_quiz_state(invalid_state))
    
    def test_state_cleanup_clear_quiz_state(self):
        """Test cleanup of quiz state"""
        chat_id = 12345
        
        # Save quiz state
        self.manager.save_quiz_state(chat_id, self.sample_quiz_data)
        
        # Verify it exists
        loaded_data = self.manager.load_quiz_state(chat_id)
        self.assertEqual(loaded_data['subject'], 'Test Subject')
        
        # Clear the state
        self.manager.clear_quiz_state(chat_id)
        
        # Verify it's gone
        cleared_data = self.manager.load_quiz_state(chat_id)
        self.assertEqual(cleared_data, {})
    
    def test_state_cleanup_nonexistent_chat(self):
        """Test cleanup of nonexistent chat state doesn't cause errors"""
        nonexistent_chat_id = 99999
        
        # Should not raise an exception
        self.manager.clear_quiz_state(nonexistent_chat_id)
        
        # Should still return empty dict
        result = self.manager.load_quiz_state(nonexistent_chat_id)
        self.assertEqual(result, {})
    
    def test_migration_and_validation_integration(self):
        """Test integration of migration and validation"""
        # Create state missing some optional fields
        incomplete_state = {
            'active': True,
            'subject': 'Test',
            'difficulty': 'easy',
            'questions': [
                {
                    'question_text': 'Test?',
                    'options': ['A', 'B'],
                    'correct_answer': 'A'
                    # Missing 'answered' and 'answered_by'
                }
            ],
            'current_question': 0,
            'scores': {}
            # Missing 'created_at' and 'message_ids'
        }
        
        # Migrate the state
        migrated_state = self.manager.migrate_quiz_state(incomplete_state)
        
        # Validate the migrated state
        is_valid = self.manager.validate_quiz_state(migrated_state)
        self.assertTrue(is_valid)
        
        # Verify missing fields were added
        self.assertIn('created_at', migrated_state)
        self.assertIn('message_ids', migrated_state)
        self.assertTrue(migrated_state['questions'][0]['answered'] is False)
        self.assertIsNone(migrated_state['questions'][0]['answered_by'])


if __name__ == '__main__':
    print("Starting QuizStateManager tests...")
    unittest.main(verbosity=2)