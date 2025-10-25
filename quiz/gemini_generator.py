"""
Gemini Question Generator - Handles all Gemini API interactions for question generation
"""

import json
import logging
import time
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Import google-generativeai with fallback
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    logger.warning("google-generativeai not available - quiz functionality will be limited")
    genai = None
    GENAI_AVAILABLE = False

# Import google.api_core exceptions with fallback
try:
    from google.api_core import exceptions as google_exceptions
    API_CORE_AVAILABLE = True
except ImportError:
    logger.warning("google.api_core not available - using generic exception handling")
    google_exceptions = None
    API_CORE_AVAILABLE = False


class GeminiQuestionGenerator:
    """Handles all Gemini API interactions for question generation"""
    
    def __init__(self, api_key: str):
        """Initialize with Gemini API key"""
        self.api_key = api_key
        self.model = None
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize the Gemini API client"""
        if not GENAI_AVAILABLE:
            logger.error("google-generativeai library not available")
            raise Exception("google-generativeai library not installed")
        
        try:
            genai.configure(api_key=self.api_key)
            # Try the current free model names
            model_names = ['gemini-1.5-flash-latest', 'gemini-1.5-flash', 'gemini-pro']
            
            for model_name in model_names:
                try:
                    self.model = genai.GenerativeModel(model_name)
                    logger.info(f"Gemini API client initialized successfully with model: {model_name}")
                    break
                except Exception as model_error:
                    logger.warning(f"Failed to initialize model {model_name}: {model_error}")
                    continue
            else:
                raise Exception("No valid Gemini model found")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini API client: {e}")
            raise
    
    def generate_questions(self, subject: str, num_questions: int, difficulty: str) -> List[Dict[str, Any]]:
        """
        Generate quiz questions using Gemini API with comprehensive error handling
        
        Args:
            subject: The topic/subject for questions
            num_questions: Number of questions to generate
            difficulty: Difficulty level (easy, medium, hard, expert)
            
        Returns:
            List of question dictionaries with structure:
            {
                "question_text": str,
                "options": List[str],
                "correct_answer": str
            }
            
        Raises:
            Exception: If API call fails after retries or response is invalid
        """
        if not self.model:
            logger.error("Gemini API client not initialized")
            raise Exception("Gemini API client not initialized")
        
        # Validate input parameters
        if not subject or not subject.strip():
            raise ValueError("Subject cannot be empty")
        
        if not isinstance(num_questions, int) or num_questions < 1 or num_questions > 20:
            raise ValueError("Number of questions must be between 1 and 20")
        
        if difficulty not in ['easy', 'medium', 'hard', 'expert']:
            raise ValueError("Difficulty must be one of: easy, medium, hard, expert")
        
        prompt = self._build_prompt(subject, num_questions, difficulty)
        
        # Generate questions with exponential backoff retry logic
        max_retries = 3
        base_delay = 1.0
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"Generating questions for '{subject}' (attempt {attempt + 1}/{max_retries})")
                
                response = self.model.generate_content(prompt)
                
                if not response:
                    raise Exception("No response received from Gemini API")
                
                if not response.text:
                    raise Exception("Empty response text from Gemini API")
                
                questions = self._parse_response(response.text)
                
                if not questions:
                    raise Exception("No valid questions parsed from response")
                
                if len(questions) != num_questions:
                    logger.warning(f"Expected {num_questions} questions, got {len(questions)} for subject: {subject}")
                
                logger.info(f"Successfully generated {len(questions)} questions for subject: {subject}")
                return questions
                
            except Exception as api_error:
                # Handle specific Google API errors if available
                error_str = str(api_error).lower()
                
                if API_CORE_AVAILABLE and hasattr(google_exceptions, 'ResourceExhausted') and isinstance(api_error, google_exceptions.ResourceExhausted):
                    logger.error(f"API quota exceeded on attempt {attempt + 1}: {api_error}")
                    last_exception = Exception(f"API quota exceeded: {str(api_error)}")
                    if attempt == max_retries - 1:
                        break
                    # Longer delay for quota issues
                    delay = base_delay * (3 ** attempt)
                    logger.info(f"Quota exceeded, waiting {delay} seconds before retry")
                    time.sleep(delay)
                    continue
                    
                elif API_CORE_AVAILABLE and hasattr(google_exceptions, 'DeadlineExceeded') and isinstance(api_error, google_exceptions.DeadlineExceeded):
                    logger.warning(f"API timeout on attempt {attempt + 1}: {api_error}")
                    last_exception = Exception(f"API timeout: {str(api_error)}")
                    if attempt == max_retries - 1:
                        break
                    delay = base_delay * (2 ** attempt)
                    logger.debug(f"Timeout occurred, waiting {delay} seconds before retry")
                    time.sleep(delay)
                    continue
                    
                elif API_CORE_AVAILABLE and hasattr(google_exceptions, 'ServiceUnavailable') and isinstance(api_error, google_exceptions.ServiceUnavailable):
                    logger.warning(f"API service unavailable on attempt {attempt + 1}: {api_error}")
                    last_exception = Exception(f"API service unavailable: {str(api_error)}")
                    if attempt == max_retries - 1:
                        break
                    delay = base_delay * (2 ** attempt)
                    logger.debug(f"Service unavailable, waiting {delay} seconds before retry")
                    time.sleep(delay)
                    continue
                    
                elif API_CORE_AVAILABLE and hasattr(google_exceptions, 'InvalidArgument') and isinstance(api_error, google_exceptions.InvalidArgument):
                    logger.error(f"Invalid API request on attempt {attempt + 1}: {api_error}")
                    # Don't retry for invalid arguments
                    raise Exception(f"Invalid API request: {str(api_error)}")
                    
                elif API_CORE_AVAILABLE and hasattr(google_exceptions, 'PermissionDenied') and isinstance(api_error, google_exceptions.PermissionDenied):
                    logger.error(f"API permission denied on attempt {attempt + 1}: {api_error}")
                    # Don't retry for permission issues
                    raise Exception(f"API permission denied - check API key: {str(api_error)}")
                
                # Fallback error handling based on error message content
                elif 'quota' in error_str or 'limit' in error_str:
                    logger.error(f"API quota/limit error on attempt {attempt + 1}: {api_error}")
                    last_exception = Exception(f"API quota exceeded: {str(api_error)}")
                    if attempt == max_retries - 1:
                        break
                    delay = base_delay * (3 ** attempt)
                    logger.info(f"Quota/limit error, waiting {delay} seconds before retry")
                    time.sleep(delay)
                    continue
                    
                elif 'timeout' in error_str or 'deadline' in error_str:
                    logger.warning(f"API timeout on attempt {attempt + 1}: {api_error}")
                    last_exception = Exception(f"API timeout: {str(api_error)}")
                    if attempt == max_retries - 1:
                        break
                    delay = base_delay * (2 ** attempt)
                    logger.debug(f"Timeout, waiting {delay} seconds before retry")
                    time.sleep(delay)
                    continue
                    
                elif 'unavailable' in error_str or 'service' in error_str:
                    logger.warning(f"API service issue on attempt {attempt + 1}: {api_error}")
                    last_exception = Exception(f"API service unavailable: {str(api_error)}")
                    if attempt == max_retries - 1:
                        break
                    delay = base_delay * (2 ** attempt)
                    logger.debug(f"Service issue, waiting {delay} seconds before retry")
                    time.sleep(delay)
                    continue
                    
                elif 'permission' in error_str or 'denied' in error_str or 'unauthorized' in error_str:
                    logger.error(f"API permission error on attempt {attempt + 1}: {api_error}")
                    # Don't retry for permission issues
                    raise Exception(f"API permission denied - check API key: {str(api_error)}")
                
                # Handle as generic error
                logger.warning(f"API error on attempt {attempt + 1}: {api_error}")
                last_exception = api_error
                if attempt == max_retries - 1:
                    break
                delay = base_delay * (2 ** attempt)
                logger.debug(f"Generic API error, waiting {delay} seconds before retry")
                time.sleep(delay)
                continue
                
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parsing error on attempt {attempt + 1}: {e}")
                last_exception = Exception(f"Invalid JSON response: {str(e)}")
                if attempt == max_retries - 1:
                    break
                delay = base_delay * (2 ** attempt)
                logger.debug(f"JSON error, waiting {delay} seconds before retry")
                time.sleep(delay)
                
            except Exception as e:
                logger.warning(f"Unexpected error on attempt {attempt + 1}: {e}")
                last_exception = e
                if attempt == max_retries - 1:
                    break
                
                # Exponential backoff for general errors
                delay = base_delay * (2 ** attempt)
                logger.debug(f"General error, waiting {delay} seconds before retry")
                time.sleep(delay)
        
        # All retries failed
        logger.error(f"All {max_retries} attempts failed to generate questions for subject: {subject}")
        if last_exception:
            raise Exception(f"Failed to generate questions after {max_retries} attempts: {str(last_exception)}")
        else:
            raise Exception(f"Failed to generate questions after {max_retries} attempts: Unknown error")
    
    def _build_prompt(self, subject: str, num_questions: int, difficulty: str) -> str:
        """
        Build the prompt for Gemini API
        
        Args:
            subject: The topic/subject for questions
            num_questions: Number of questions to generate
            difficulty: Difficulty level
            
        Returns:
            Formatted prompt string
        """
        difficulty_descriptions = {
            'easy': 'basic knowledge, simple concepts, commonly known facts',
            'medium': 'intermediate knowledge, some analysis required, moderately challenging',
            'hard': 'advanced knowledge, complex concepts, detailed understanding required',
            'expert': 'expert-level knowledge, highly specialized, very challenging'
        }
        
        difficulty_desc = difficulty_descriptions.get(difficulty, difficulty_descriptions['medium'])
        
        prompt = f"""Generate {num_questions} multiple choice quiz questions about {subject}.

Difficulty level: {difficulty} ({difficulty_desc})

Requirements:
1. Each question must have exactly 4 answer options (A, B, C, D)
2. Only one option should be correct
3. Questions should be appropriate for the {difficulty} difficulty level
4. Avoid ambiguous or trick questions
5. Make sure incorrect options are plausible but clearly wrong
6. Questions should be factual and verifiable

Return the response as a valid JSON array with this exact structure:
[
  {{
    "question_text": "Your question here?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_answer": "Option A"
  }}
]

Important: 
- Return ONLY the JSON array, no additional text or formatting
- The correct_answer must exactly match one of the options
- Ensure all JSON is properly formatted and valid"""

        return prompt
    
    def _parse_response(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Parse and validate the JSON response from Gemini API
        
        Args:
            response_text: Raw response text from API
            
        Returns:
            List of validated question dictionaries
            
        Raises:
            Exception: If response cannot be parsed or is invalid
        """
        try:
            # Clean up the response text - remove any markdown formatting or extra text
            cleaned_text = response_text.strip()
            
            # Look for JSON array in the response
            start_idx = cleaned_text.find('[')
            end_idx = cleaned_text.rfind(']')
            
            if start_idx == -1 or end_idx == -1:
                raise Exception("No JSON array found in response")
            
            json_text = cleaned_text[start_idx:end_idx + 1]
            
            # Parse JSON
            questions_data = json.loads(json_text)
            
            if not isinstance(questions_data, list):
                raise Exception("Response is not a JSON array")
            
            # Validate each question
            validated_questions = []
            for i, question in enumerate(questions_data):
                try:
                    validated_question = self._validate_question(question, i)
                    validated_questions.append(validated_question)
                except Exception as e:
                    logger.warning(f"Skipping invalid question {i}: {e}")
                    continue
            
            if not validated_questions:
                raise Exception("No valid questions found in response")
            
            return validated_questions
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            logger.debug(f"Response text: {response_text}")
            raise Exception(f"Invalid JSON response: {e}")
        except Exception as e:
            logger.error(f"Response parsing error: {e}")
            raise
    
    def _validate_question(self, question: Dict[str, Any], index: int) -> Dict[str, Any]:
        """
        Validate and clean a single question
        
        Args:
            question: Question dictionary to validate
            index: Question index for error reporting
            
        Returns:
            Validated and cleaned question dictionary
            
        Raises:
            Exception: If question is invalid
        """
        if not isinstance(question, dict):
            raise Exception(f"Question {index} is not a dictionary")
        
        # Check required fields
        required_fields = ['question_text', 'options', 'correct_answer']
        for field in required_fields:
            if field not in question:
                raise Exception(f"Question {index} missing required field: {field}")
        
        # Validate question_text
        question_text = question['question_text']
        if not isinstance(question_text, str) or not question_text.strip():
            raise Exception(f"Question {index} has invalid question_text")
        
        # Validate options
        options = question['options']
        if not isinstance(options, list):
            raise Exception(f"Question {index} options must be a list")
        
        if len(options) < 2:
            raise Exception(f"Question {index} must have at least 2 options")
        
        # Clean and validate options
        cleaned_options = []
        for j, option in enumerate(options):
            if not isinstance(option, str) or not option.strip():
                raise Exception(f"Question {index} option {j} is invalid")
            cleaned_options.append(option.strip())
        
        # Check for duplicate options
        if len(set(cleaned_options)) != len(cleaned_options):
            raise Exception(f"Question {index} has duplicate options")
        
        # Validate correct_answer
        correct_answer = question['correct_answer']
        if not isinstance(correct_answer, str) or not correct_answer.strip():
            raise Exception(f"Question {index} has invalid correct_answer")
        
        correct_answer = correct_answer.strip()
        if correct_answer not in cleaned_options:
            raise Exception(f"Question {index} correct_answer not found in options")
        
        # Return cleaned question
        return {
            'question_text': question_text.strip(),
            'options': cleaned_options,
            'correct_answer': correct_answer
        }
    
    def list_available_models(self) -> list:
        """
        List available Gemini models for debugging
        
        Returns:
            List of available model names
        """
        try:
            if not GENAI_AVAILABLE:
                return []
            
            models = genai.list_models()
            model_names = []
            for model in models:
                if 'generateContent' in model.supported_generation_methods:
                    model_names.append(model.name)
                    logger.info(f"Available model: {model.name}")
            
            return model_names
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []
    
    def test_api_connection(self) -> bool:
        """
        Test the API connection with a simple request
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            if not self.model:
                logger.warning("API connection test failed - model not initialized")
                # Try to list available models for debugging
                logger.info("Attempting to list available models...")
                available_models = self.list_available_models()
                if available_models:
                    logger.info(f"Available models: {available_models}")
                return False
            
            test_response = self.model.generate_content("Say 'API test successful'")
            
            if test_response and test_response.text:
                logger.info("Gemini API connection test successful")
                return True
            else:
                logger.warning("Gemini API connection test failed - empty response")
                return False
                
        except Exception as e:
            error_str = str(e).lower()
            if 'permission' in error_str or 'denied' in error_str:
                logger.error(f"API connection test failed - permission denied: {e}")
            elif 'quota' in error_str or 'limit' in error_str:
                logger.error(f"API connection test failed - quota exceeded: {e}")
            elif 'unavailable' in error_str or 'service' in error_str:
                logger.error(f"API connection test failed - service unavailable: {e}")
            else:
                logger.error(f"API connection test failed: {e}")
                # Try to list available models for debugging
                logger.info("Attempting to list available models...")
                available_models = self.list_available_models()
                if available_models:
                    logger.info(f"Available models: {available_models}")
            return False
        except Exception as e:
            logger.error(f"Gemini API connection test failed: {e}")
            return False
    
    def get_api_status(self) -> Dict[str, Any]:
        """
        Get current API status information
        
        Returns:
            Dictionary with API status information
        """
        return {
            'initialized': self.model is not None,
            'api_key_configured': bool(self.api_key),
            'connection_test': self.test_api_connection() if self.model else False
        }
    
    def handle_api_error(self, error: Exception, context: str = "") -> str:
        """
        Handle and categorize API errors for user-friendly messages
        
        Args:
            error: The exception that occurred
            context: Additional context about when the error occurred
            
        Returns:
            User-friendly error message
        """
        context_prefix = f"{context}: " if context else ""
        error_str = str(error).lower()
        
        # Check for specific Google API exceptions if available
        if API_CORE_AVAILABLE and google_exceptions:
            if hasattr(google_exceptions, 'PermissionDenied') and isinstance(error, google_exceptions.PermissionDenied):
                logger.error(f"{context_prefix}API permission denied: {error}")
                return "❌ API access denied. Please check your Gemini API key configuration."
            
            elif hasattr(google_exceptions, 'ResourceExhausted') and isinstance(error, google_exceptions.ResourceExhausted):
                logger.error(f"{context_prefix}API quota exceeded: {error}")
                return "❌ API quota exceeded. Please try again later or check your API usage limits."
            
            elif hasattr(google_exceptions, 'ServiceUnavailable') and isinstance(error, google_exceptions.ServiceUnavailable):
                logger.warning(f"{context_prefix}API service unavailable: {error}")
                return "❌ Gemini API is temporarily unavailable. Please try again in a few minutes."
            
            elif hasattr(google_exceptions, 'DeadlineExceeded') and isinstance(error, google_exceptions.DeadlineExceeded):
                logger.warning(f"{context_prefix}API timeout: {error}")
                return "❌ Request timed out. The API took too long to respond. Please try again."
            
            elif hasattr(google_exceptions, 'InvalidArgument') and isinstance(error, google_exceptions.InvalidArgument):
                logger.error(f"{context_prefix}Invalid API request: {error}")
                return "❌ Invalid request parameters. Please check your quiz settings and try again."
        
        # Fallback error categorization based on error message content
        if 'permission' in error_str or 'denied' in error_str or 'unauthorized' in error_str:
            logger.error(f"{context_prefix}API permission denied: {error}")
            return "❌ API access denied. Please check your Gemini API key configuration."
        
        elif 'quota' in error_str or 'limit' in error_str or 'exhausted' in error_str:
            logger.error(f"{context_prefix}API quota exceeded: {error}")
            return "❌ API quota exceeded. Please try again later or check your API usage limits."
        
        elif 'unavailable' in error_str or 'service' in error_str:
            logger.warning(f"{context_prefix}API service unavailable: {error}")
            return "❌ Gemini API is temporarily unavailable. Please try again in a few minutes."
        
        elif 'timeout' in error_str or 'deadline' in error_str:
            logger.warning(f"{context_prefix}API timeout: {error}")
            return "❌ Request timed out. The API took too long to respond. Please try again."
        
        elif isinstance(error, json.JSONDecodeError):
            logger.error(f"{context_prefix}JSON parsing error: {error}")
            return "❌ Received invalid response format from API. Please try again."
        
        elif isinstance(error, ValueError):
            logger.error(f"{context_prefix}Validation error: {error}")
            return f"❌ Invalid input: {str(error)}"
        
        else:
            logger.error(f"{context_prefix}Unexpected error: {error}")
            return "❌ An unexpected error occurred while generating questions. Please try again."
    
    def recover_from_partial_failure(self, subject: str, requested_count: int, 
                                   generated_questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Attempt to recover from partial question generation failure
        
        Args:
            subject: Original subject
            requested_count: Number of questions originally requested
            generated_questions: Questions that were successfully generated
            
        Returns:
            List of questions (may be fewer than requested)
        """
        if not generated_questions:
            logger.warning("No questions to recover from partial failure")
            return []
        
        missing_count = requested_count - len(generated_questions)
        
        if missing_count <= 0:
            return generated_questions
        
        logger.info(f"Attempting to generate {missing_count} additional questions for recovery")
        
        try:
            # Try to generate the missing questions with a simpler prompt
            additional_questions = self.generate_questions(subject, missing_count, "medium")
            
            # Combine with existing questions
            all_questions = generated_questions + additional_questions
            logger.info(f"Successfully recovered {len(additional_questions)} additional questions")
            return all_questions[:requested_count]  # Ensure we don't exceed the requested count
            
        except Exception as e:
            logger.warning(f"Recovery attempt failed: {e}")
            # Return what we have
            return generated_questions
    
    def validate_api_configuration(self) -> Dict[str, Any]:
        """
        Validate the current API configuration
        
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check API key
        if not self.api_key:
            validation_result['valid'] = False
            validation_result['errors'].append("API key not configured")
        elif len(self.api_key) < 10:  # Basic length check
            validation_result['valid'] = False
            validation_result['errors'].append("API key appears to be invalid (too short)")
        
        # Check model initialization
        if not self.model:
            validation_result['valid'] = False
            validation_result['errors'].append("Gemini model not initialized")
        
        # Test connection if basic checks pass
        if validation_result['valid']:
            if not self.test_api_connection():
                validation_result['valid'] = False
                validation_result['errors'].append("API connection test failed")
        
        return validation_result
    
    def get_error_recovery_suggestions(self, error: Exception) -> List[str]:
        """
        Get recovery suggestions for specific errors
        
        Args:
            error: The exception that occurred
            
        Returns:
            List of suggested recovery actions
        """
        suggestions = []
        
        if isinstance(error, google_exceptions.PermissionDenied):
            suggestions.extend([
                "Verify your Gemini API key is correct",
                "Check that the API key has the necessary permissions",
                "Ensure the Gemini API is enabled in your Google Cloud project"
            ])
        
        elif isinstance(error, google_exceptions.ResourceExhausted):
            suggestions.extend([
                "Wait a few minutes before trying again",
                "Check your API quota limits in Google Cloud Console",
                "Consider upgrading your API plan if needed"
            ])
        
        elif isinstance(error, google_exceptions.ServiceUnavailable):
            suggestions.extend([
                "Wait a few minutes and try again",
                "Check Google Cloud Status page for service issues",
                "Try with a simpler request (fewer questions)"
            ])
        
        elif isinstance(error, json.JSONDecodeError):
            suggestions.extend([
                "Try again with a different subject or difficulty",
                "The API response may have been malformed - retry should work",
                "Check if the subject contains special characters"
            ])
        
        else:
            suggestions.extend([
                "Try again in a few minutes",
                "Check your internet connection",
                "Contact support if the problem persists"
            ])
        
        return suggestions