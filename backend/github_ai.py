import os
import json
import requests
import logging
import time
import base64
import io
from PIL import Image, ImageDraw, ImageFont
import numpy as np
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
            dict: Response with interpretation of urban issues and optional marked image
        """
        try:
            # Extract relevant detection information
            detection_summary = self._prepare_detection_summary(detections)
            
            # Create prompt for GitHub AI with instructions to identify issues regardless of detection results
            system_message = """You are an urban infrastructure analysis expert. Your task is to:
            1. Interpret detection results from AI models that identify urban issues like potholes, garbage, and other 
            problems in city environments.
            2. Analyze the provided image directly to identify ANY urban issues, even if the detection models didn't find any.
            
            Provide a detailed analysis including:
            1. Summary of detected issues (from both the detection models and your direct image analysis)
            2. Additional issues you can identify in the image that weren't detected by the models
            3. Potential impact on the community
            4. Recommended actions for city officials
            5. Priority level (low/medium/high)
            
            IMPORTANT: In your response, if you identify any issues (whether detected by models or by your analysis), 
            specify the locations of these issues in the image in the following format:
            
            [ISSUE_LOCATIONS]
            - Issue type 1: x1,y1,x2,y2 (coordinates as percentages of image width/height)
            - Issue type 2: x1,y1,x2,y2 (coordinates as percentages of image width/height)
            [/ISSUE_LOCATIONS]
            
            For example:
            [ISSUE_LOCATIONS]
            - Pothole: 45,60,55,70
            - Garbage: 20,30,25,35
            - Broken bench: 70,80,85,90
            [/ISSUE_LOCATIONS]
            
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
                        {"type": "text", "text": "Here's the image for you to analyze directly. Please identify any urban issues you can see, even if they were not detected by our models. Remember to provide coordinates for issues in the format requested:"},
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
                            
                            # Process the content to extract issue locations and mark the image
                            marked_image_base64 = None
                            if base64_image:
                                issue_locations = self._extract_issue_locations(content)
                                if issue_locations:
                                    marked_image_base64 = self._mark_issues_on_image(base64_image, issue_locations)
                            
                            # Remove the issue locations section from the content for display
                            clean_content = self._remove_issue_locations_section(content)
                            
                            # Prepare response
                            response_data = {"status": "success", "evaluation": clean_content}
                            if marked_image_base64:
                                response_data["marked_image"] = marked_image_base64
                                
                            return response_data
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
            return "No objects detected by any model. Please analyze the image directly to identify any urban issues that might be present."
            
        return "\n".join(summary)
    
    def _extract_issue_locations(self, content):
        """Extract issue locations from the AI-generated content"""
        try:
            # Look for the issue locations section
            start_marker = "[ISSUE_LOCATIONS]"
            end_marker = "[/ISSUE_LOCATIONS]"
            
            start_idx = content.find(start_marker)
            end_idx = content.find(end_marker)
            
            if start_idx == -1 or end_idx == -1:
                logger.warning("Issue locations section not found in AI response")
                return []
            
            # Extract the section content
            locations_text = content[start_idx + len(start_marker):end_idx].strip()
            
            # Parse the locations
            issue_locations = []
            for line in locations_text.split('\n'):
                line = line.strip()
                if not line or not line.startswith('-'):
                    continue
                    
                # Extract the issue type and coordinates
                try:
                    # Format is "- Issue type: x1,y1,x2,y2"
                    parts = line[1:].split(':')
                    if len(parts) != 2:
                        continue
                        
                    issue_type = parts[0].strip()
                    coords_str = parts[1].strip()
                    
                    # Parse coordinates
                    coords = [float(c) for c in coords_str.split(',')]
                    if len(coords) != 4:
                        continue
                        
                    issue_locations.append({
                        "type": issue_type,
                        "coords": coords  # [x1, y1, x2, y2] as percentages
                    })
                except Exception as e:
                    logger.warning(f"Failed to parse issue location: {line}, error: {str(e)}")
                    continue
            
            return issue_locations
            
        except Exception as e:
            logger.error(f"Error extracting issue locations: {str(e)}")
            return []
    
    def _remove_issue_locations_section(self, content):
        """Remove the issue locations section from the content for cleaner display"""
        try:
            start_marker = "[ISSUE_LOCATIONS]"
            end_marker = "[/ISSUE_LOCATIONS]"
            
            start_idx = content.find(start_marker)
            end_idx = content.find(end_marker)
            
            if start_idx == -1 or end_idx == -1:
                return content
                
            # Remove the section including markers
            return content[:start_idx] + content[end_idx + len(end_marker):]
            
        except Exception as e:
            logger.error(f"Error removing issue locations section: {str(e)}")
            return content
    
    def _mark_issues_on_image(self, base64_image, issue_locations):
        """Mark detected issues on the image"""
        try:
            # Decode base64 image
            image_data = base64.b64decode(base64_image)
            img = Image.open(io.BytesIO(image_data))
            img_width, img_height = img.size
            
            # Create a draw object
            draw = ImageDraw.Draw(img)
            
            # Try to load a font, use default if not available
            try:
                # Attempt to load Arial font with size 20
                font = ImageFont.truetype("arial.ttf", 20)
            except IOError:
                font = None
            
            # Define colors for different issue types
            # Use a default color mapping with some common urban issues
            color_map = {
                "pothole": (255, 0, 0),      # Red
                "garbage": (255, 165, 0),    # Orange
                "graffiti": (0, 0, 255),     # Blue
                "damaged": (128, 0, 128),    # Purple
                "broken": (128, 0, 128),     # Purple
                "crack": (255, 255, 0),      # Yellow
                "litter": (255, 165, 0),     # Orange
            }
            
            # Draw each issue
            for issue in issue_locations:
                issue_type = issue["type"].lower()
                x1, y1, x2, y2 = issue["coords"]
                
                # Convert percentage coordinates to pixel coordinates
                x1 = int(x1 * img_width / 100)
                y1 = int(y1 * img_height / 100)
                x2 = int(x2 * img_width / 100)
                y2 = int(y2 * img_height / 100)
                
                # Determine color based on issue type
                color = None
                for key, value in color_map.items():
                    if key in issue_type:
                        color = value
                        break
                
                # Default to red if no matching type
                if not color:
                    color = (255, 0, 0)  # Red
                
                # Draw rectangle
                draw.rectangle([(x1, y1), (x2, y2)], outline=color, width=3)
                
                # Draw label
                if font:
                    label = issue["type"]
                    text_bbox = draw.textbbox((0, 0), label, font=font)
                    text_width = text_bbox[2] - text_bbox[0]
                    text_height = text_bbox[3] - text_bbox[1]
                    
                    # Background for text
                    draw.rectangle(
                        [(x1, y1 - text_height - 4), (x1 + text_width + 4, y1)],
                        fill=color
                    )
                    
                    # Text
                    draw.text((x1 + 2, y1 - text_height - 2), label, fill=(255, 255, 255), font=font)
                
            # Convert back to base64
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            marked_image_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            return marked_image_base64
            
        except Exception as e:
            logger.error(f"Error marking issues on image: {str(e)}")
            return None
