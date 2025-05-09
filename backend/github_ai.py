import os
import json
import requests
import logging
import time
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class GitHubAIClient:
    """Client for interacting with GitHub's AI models API"""
    
    def __init__(self):
        """Initialize the GitHub AI client with authentication"""
        load_dotenv()
        
        self.token = os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise ValueError("GITHUB_TOKEN environment variable not set")
            
        self.endpoint = "https://models.github.ai/inference"
        self.model = "openai/gpt-4.1"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        self.max_retries = int(os.getenv("GITHUB_AI_MAX_RETRIES", "2"))
        self.request_timeout = int(os.getenv("GITHUB_AI_TIMEOUT", "30"))
        logger.info(f"GitHub AI client initialized successfully (timeout={self.request_timeout}s, retries={self.max_retries})")
        
    def generate_interpretation(self, detections, base64_image=None):
        """Generate an interpretation of urban issues based on detection results and image
        
        Args:
            detections (dict): Dictionary of detection results from YOLO models
            base64_image (str, optional): Base64 encoded image data
            
        Returns:
            dict: Response with interpretation of urban issues
        """
        try:
            # Extract relevant detection information
            detection_summary = self._prepare_detection_summary(detections)
            
            # Create prompt for GitHub AI
            system_message = """You are an urban infrastructure analysis expert. Your task is to:
            1. Interpret detection results from AI models that identify urban issues like potholes, garbage, and other 
            problems in city environments.
            2. Analyze the provided image directly to identify any issues the detection models might have missed.
            
            Provide a detailed analysis including:
            1. Summary of detected issues (from both the detection models and your direct image analysis)
            2. Additional issues you can identify in the image that weren't detected by the models
            3. Potential impact on the community
            4. Recommended actions for city officials
            5. Priority level (low/medium/high)
            
            Format your response in Markdown."""
            
            # Prepare user message with detection results
            user_message = f"""Here are the detection results from our urban analysis AI models:
            
            {detection_summary}
            """
            
            # Prepare messages list
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ]
            
            # If we have an image, add it to the messages
            if base64_image:
                messages.append({
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": "Here's the image for you to analyze directly. Please identify any urban issues that might not have been detected by our models:"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                })
            
            # Prepare request payload
            payload = {
                "messages": messages,
                "temperature": 0.7,
                "top_p": 1.0,
                "model": self.model
            }
            
            # Implement retry logic with exponential backoff
            retry_count = 0
            while retry_count <= self.max_retries:
                try:
                    logger.info(f"Sending request to GitHub AI (attempt {retry_count+1}/{self.max_retries+1})")
                    
                    # Send request to GitHub AI with increased timeout
                    response = requests.post(
                        f"{self.endpoint}/chat/completions",
                        headers=self.headers,
                        json=payload,
                        timeout=self.request_timeout
                    )
                    
                    # Handle API response
                    if response.status_code == 200:
                        result = response.json()
                        if "choices" in result and len(result["choices"]) > 0:
                            content = result["choices"][0]["message"]["content"]
                            logger.info("Successfully received response from GitHub AI")
                            return {"status": "success", "evaluation": content}
                        else:
                            logger.warning(f"Unexpected GitHub AI response structure: {result}")
                            return {"status": "error", "message": "Invalid response format from GitHub AI"}
                    elif response.status_code == 429:  # Rate limit
                        retry_count += 1
                        wait_time = min(2 ** retry_count, 30)  # Exponential backoff, max 30 seconds
                        logger.warning(f"Rate limited by GitHub AI. Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"GitHub AI request failed with status {response.status_code}: {response.text}")
                        return {"status": "error", "message": f"GitHub AI request failed: {response.status_code}"}
                
                except requests.exceptions.Timeout:
                    retry_count += 1
                    if retry_count <= self.max_retries:
                        wait_time = min(2 ** retry_count, 30)
                        logger.warning(f"GitHub AI request timed out. Retrying in {wait_time} seconds... ({retry_count}/{self.max_retries})")
                        time.sleep(wait_time)
                    else:
                        logger.error("GitHub AI request timed out after all retries")
                        return {"status": "error", "message": "GitHub AI request timed out after multiple retries"}
                
                except Exception as e:
                    logger.error(f"Error during GitHub AI request: {str(e)}")
                    return {"status": "error", "message": f"Error during GitHub AI request: {str(e)}"}
            
            # If we've exhausted all retries
            return {"status": "error", "message": "Failed to get response from GitHub AI after multiple attempts"}
            
        except Exception as e:
            logger.error(f"Error in generate_interpretation: {str(e)}")
            return {"status": "error", "message": f"Failed to generate interpretation: {str(e)}"}
    
    def _prepare_detection_summary(self, detections):
        """Format detection results into a readable summary for the AI"""
        summary = []
        
        for model_name, objects in detections.items():
            if objects:
                model_line = f"**{model_name}**: Detected {len(objects)} objects:"
                summary.append(model_line)
                
                for obj in objects:
                    obj_line = f"- {obj['name']} (confidence: {obj['confidence']*100:.1f}%)"
                    summary.append(obj_line)
                
                summary.append("")  # Add blank line between models
        
        if not summary:
            return "No objects detected by any model."
            
        return "\n".join(summary)
