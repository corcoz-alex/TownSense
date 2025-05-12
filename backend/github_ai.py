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
import math
from PIL import ImageFilter, ImageEnhance

# Add imports for the feedback handling
from datetime import datetime, timedelta
from db import feedback_collection

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
        self.max_image_dimension = int(os.getenv("MAX_IMAGE_DIMENSION", "1280"))
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
            
            # Resize image if needed
            if base64_image:
                base64_image = self._ensure_image_size(base64_image)
            
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
                    
                    # More robust coordinate parsing - handle multiple formats
                    # Remove any non-numeric characters except commas, periods, and spaces
                    coords_str = ''.join(c for c in coords_str if c.isdigit() or c in ',.[] \t')
                    # Split by comma and filter out empty strings
                    coords_parts = [p.strip() for p in coords_str.split(',') if p.strip()]
                    
                    # Ensure we have exactly 4 coordinates
                    if len(coords_parts) != 4:
                        logger.warning(f"Invalid coordinate format: {coords_str} (expected 4 values)")
                        continue
                        
                    # Parse coordinates with better error handling
                    coords = []
                    for part in coords_parts:
                        try:
                            value = float(part)
                            # Validate coordinate percentage is between 0-100
                            if 0 <= value <= 100:
                                coords.append(value)
                            else:
                                logger.warning(f"Coordinate value out of range (0-100): {value}")
                                raise ValueError("Coordinate out of range")
                        except ValueError:
                            logger.warning(f"Failed to parse coordinate value: {part}")
                            raise
                    
                    # Ensure we have 4 valid coordinates
                    if len(coords) != 4:
                        continue
                    
                    # Validate that x2 > x1 and y2 > y1
                    if coords[2] <= coords[0] or coords[3] <= coords[1]:
                        logger.warning(f"Invalid coordinate ordering: {coords}")
                        # Fix the ordering to ensure valid rectangle
                        coords = [
                            min(coords[0], coords[2]),  # x1
                            min(coords[1], coords[3]),  # y1
                            max(coords[0], coords[2]),  # x2
                            max(coords[1], coords[3])   # y2
                        ]
                        
                    issue_locations.append({
                        "type": issue_type,
                        "coords": coords  # [x1, y1, x2, y2] as percentages
                    })
                    logger.info(f"Extracted issue location: {issue_type} at {coords}")
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
        """Mark detected issues on the image with visually appealing pointers and callouts"""
        try:
            logger.info(f"Marking {len(issue_locations)} issues on image")
            
            # Verify we have locations to mark
            if not issue_locations or len(issue_locations) == 0:
                logger.warning("No issue locations to mark on image")
                return None
                
            # Decode base64 image
            image_data = base64.b64decode(base64_image)
            img = Image.open(io.BytesIO(image_data))
            img_width, img_height = img.size
            logger.info(f"Original image dimensions: {img_width}x{img_height}")
            
            # Convert to RGBA if not already
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
                
            # Create a semi-transparent overlay layer
            overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            
            # Try to load a font, use default if not available
            try:
                # Attempt to load fonts with different sizes
                title_font = ImageFont.truetype("arial.ttf", 24)
                label_font = ImageFont.truetype("arial.ttf", 18)
                small_font = ImageFont.truetype("arial.ttf", 14)
                logger.info("Loaded Arial fonts successfully")
            except IOError:
                try:
                    # Try system fonts as fallback
                    title_font = ImageFont.truetype("DejaVuSans.ttf", 24)
                    label_font = ImageFont.truetype("DejaVuSans.ttf", 18)
                    small_font = ImageFont.truetype("DejaVuSans.ttf", 14)
                    logger.info("Loaded DejaVuSans fonts successfully")
                except IOError:
                    # Use default font as last resort
                    title_font = label_font = small_font = None
                    logger.warning("Could not load fonts, using default")
            
            # Enhanced color map with more noticeable colors
            color_map = {
                "pothole": (255, 0, 0, 220),          # Brighter Red
                "garbage": (255, 120, 0, 220),        # Brighter Orange
                "graffiti": (0, 120, 255, 220),       # Brighter Blue
                "damaged": (138, 43, 226, 220),       # Brighter Purple
                "broken": (138, 43, 226, 220),        # Brighter Purple
                "crack": (255, 215, 0, 220),          # Brighter Gold
                "litter": (255, 140, 0, 220),         # Brighter Orange
                "sidewalk": (0, 200, 83, 220),        # Brighter Green
                "road": (255, 0, 0, 220),             # Brighter Red
                "hazard": (255, 0, 0, 220),           # Brighter Red
                "vandalism": (0, 120, 255, 220),      # Brighter Blue
                "bench": (165, 42, 42, 220),          # Brighter Brown
                "hole": (255, 0, 0, 220),             # Brighter Red
            }
            
            # Default color for unmatched issue types (more noticeable)
            default_color = (255, 50, 50, 220)
            
            # Create a legend for the issues
            legend_items = {}
            
            # Draw each issue with increased visibility
            for i, issue in enumerate(issue_locations):
                issue_type = issue["type"].lower()
                x1_pct, y1_pct, x2_pct, y2_pct = issue["coords"]
                
                # Convert percentage coordinates to pixel coordinates with bounds checking
                x1 = max(0, min(int(x1_pct * img_width / 100), img_width-1))
                y1 = max(0, min(int(y1_pct * img_height / 100), img_height-1))
                x2 = max(0, min(int(x2_pct * img_width / 100), img_width-1))
                y2 = max(0, min(int(y2_pct * img_height / 100), img_height-1))
                
                # Ensure minimum box size for visibility (at least 10x10 pixels)
                if (x2 - x1) < 10:
                    x2 = min(x1 + 10, img_width-1)
                if (y2 - y1) < 10:
                    y2 = min(y1 + 10, img_height-1)
                
                logger.debug(f"Marking issue {i+1}: {issue_type} at coordinates {x1},{y1},{x2},{y2}")
                
                # Determine color based on issue type
                color = None
                for key, value in color_map.items():
                    if key in issue_type:
                        color = value
                        break
                
                # Use default color if no matching type
                if not color:
                    color = default_color
                
                # Calculate center of issue for pointer origin
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                
                # Draw semi-transparent rectangle around the issue
                draw.rectangle([(x1, y1), (x2, y2)], outline=color, width=2, fill=(*color[:3], 40))
                
                # Draw enhanced highlight visual effects around the issue
                self._draw_highlight_effects(draw, x1, y1, x2, y2, color)
                
                # Calculate callout position to avoid overlay with the issue box
                callout_x, callout_y, pointer_coords = self._calculate_callout_position(
                    center_x, center_y, img_width, img_height, i, len(issue_locations)
                )
                
                # Draw enhanced arrow pointer from callout to issue
                self._draw_arrow(draw, pointer_coords, (center_x, center_y), color, 2)
                
                # Draw animated attention marker at the issue center
                self._draw_attention_marker(draw, center_x, center_y, color)
                
                # Draw stylish callout bubble
                label = issue["type"]
                self._draw_callout_bubble(draw, callout_x, callout_y, label, color, label_font)
                
                # Add to legend
                if issue_type not in legend_items:
                    legend_items[issue_type] = color
            
            # Draw a legend at the bottom of the image if we have items
            if legend_items and small_font:
                logger.info(f"Drawing legend with {len(legend_items)} items")
                self._draw_legend(draw, legend_items, img_width, img_height, small_font)
            
            # Composite the original image with the overlay
            marked_img = Image.alpha_composite(img, overlay)
            
            # Apply a slight sharpening filter to make markings clearer
            enhancer = ImageEnhance.Sharpness(marked_img.convert('RGB'))
            marked_img = enhancer.enhance(1.2)
            
            # Convert back to base64
            buffered = io.BytesIO()
            marked_img.save(buffered, format="JPEG", quality=95)
            marked_image_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            logger.info("Successfully marked image with issues")
            return marked_image_base64
            
        except Exception as e:
            logger.exception(f"Error marking issues on image: {str(e)}")
            return None

    def _draw_highlight_effects(self, draw, x1, y1, x2, y2, color):
        """Draw enhanced highlight effects around the issue"""
        # Draw concentric rectangles with decreasing opacity (pulsing effect)
        for i in range(1, 4):
            outline_color = (*color[:3], max(color[3] - 40 * i, 0))
            offset = i * 3  # Increased offset for more visibility
            draw.rectangle(
                [(x1-offset, y1-offset), (x2+offset, y2+offset)], 
                outline=outline_color, 
                width=2
            )
        
        # Draw corner brackets for additional emphasis
        bracket_length = min((x2 - x1), (y2 - y1)) // 4
        bracket_length = max(bracket_length, 15)  # Ensure minimum size
        line_width = 3
        
        # Top-left corner
        draw.line([(x1, y1 + bracket_length), (x1, y1), (x1 + bracket_length, y1)], 
                 fill=color, width=line_width)
        
        # Top-right corner
        draw.line([(x2 - bracket_length, y1), (x2, y1), (x2, y1 + bracket_length)], 
                 fill=color, width=line_width)
        
        # Bottom-left corner
        draw.line([(x1, y2 - bracket_length), (x1, y2), (x1 + bracket_length, y2)], 
                 fill=color, width=line_width)
        
        # Bottom-right corner
        draw.line([(x2 - bracket_length, y2), (x2, y2), (x2, y2 - bracket_length)], 
                 fill=color, width=line_width)

    def _draw_attention_marker(self, draw, x, y, color):
        """Draw an attention-grabbing marker at the center of an issue"""
        # Draw a small circular marker at the center
        radius = 8
        draw.ellipse([(x-radius, y-radius), (x+radius, y+radius)], 
                    fill=(*color[:3], 230), outline=(255, 255, 255, 200), width=2)
        
        # Draw a cross inside the circle
        line_length = radius - 3
        draw.line([(x-line_length, y), (x+line_length, y)], fill=(255, 255, 255, 230), width=2)
        draw.line([(x, y-line_length), (x, y+line_length)], fill=(255, 255, 255, 230), width=2)
        
        # Draw radiating lines for emphasis
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            inner_x = x + int((radius + 2) * math.cos(rad))
            inner_y = y + int((radius + 2) * math.sin(rad))
            outer_x = x + int((radius + 10) * math.cos(rad))
            outer_y = y + int((radius + 10) * math.sin(rad))
            
            draw.line([(inner_x, inner_y), (outer_x, outer_y)], 
                     fill=(*color[:3], 150), width=2)

    def _draw_arrow(self, draw, points, target, color, width=2):
        """Draw an enhanced arrow pointer from callout to issue"""
        # Create gradient-like effect with multiple lines
        segments = 5
        alpha_step = 80 // segments
        
        # Draw the main line segments with full opacity
        if len(points) >= 2:
            for i in range(len(points) - 1):
                draw.line([points[i], points[i+1]], fill=color, width=width+1)
        
        # Draw the final segment to the target
        if points:
            draw.line([points[-1], target], fill=color, width=width+1)
        
        # Extract the last segment for the arrowhead
        x1, y1 = points[-1] if points else (target[0] - 20, target[1] - 20)
        x2, y2 = target
        
        # Calculate arrow direction
        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        if length < 1:  # Avoid division by zero
            dx, dy = 1, 0
        else:
            dx, dy = dx/length, dy/length
        
        # Arrow head size - increased for better visibility
        arrow_size = 16
        
        # Calculate arrowhead points
        angle = math.atan2(dy, dx)
        arrow_points = [
            (x2, y2),
            (
                int(x2 - arrow_size * math.cos(angle - math.pi/6)),
                int(y2 - arrow_size * math.sin(angle - math.pi/6))
            ),
            (
                int(x2 - arrow_size * math.cos(angle + math.pi/6)),
                int(y2 - arrow_size * math.sin(angle + math.pi/6))
            ),
        ]
        
        # Draw filled arrowhead with white border for contrast
        draw.polygon(arrow_points, fill=color)
        draw.line([arrow_points[0], arrow_points[1], arrow_points[2], arrow_points[0]], 
                 fill=(255, 255, 255, 200), width=1)

    def _draw_callout_bubble(self, draw, x, y, text, color, font):
        """Draw a stylish callout bubble with text"""
        if not font:
            # Fallback if no font is available
            draw.ellipse((x-5, y-5, x+5, y+5), fill=color)
            return
            
        # Measure text dimensions
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        # Bubble dimensions with padding
        padding = 10  # Increased padding
        bubble_width = text_width + padding * 2
        bubble_height = text_height + padding * 2
        
        # Bubble coordinates
        x1 = x - bubble_width // 2
        y1 = y - bubble_height // 2
        x2 = x + bubble_width // 2
        y2 = y + bubble_height // 2
        
        # Draw bubble shadow for depth
        shadow_offset = 3
        shadow_color = (0, 0, 0, 100)  # Semi-transparent black
        draw.rounded_rectangle(
            [(x1+shadow_offset, y1+shadow_offset), (x2+shadow_offset, y2+shadow_offset)],
            radius=12,
            fill=shadow_color
        )
        
        # Draw bubble with rounded corners
        radius = 12  # Increased radius for smoother corners
        # Filled background with semi-transparency
        draw.rounded_rectangle(
            [(x1, y1), (x2, y2)],
            radius=radius,
            fill=(*color[:3], 230),  # More opaque
            outline=(255, 255, 255, 220),
            width=2
        )
        
        # Add a highlight effect on top edge
        highlight_points = [
            (x1+radius, y1+1),  # Start after the corner
            (x2-radius, y1+1)   # End before the corner
        ]
        draw.line(highlight_points, fill=(255, 255, 255, 120), width=1)
        
        # Draw text centered in bubble with better contrast
        text_x = x - text_width // 2
        text_y = y - text_height // 2
        
        # Draw text shadow for legibility
        draw.text((text_x+1, text_y+1), text, fill=(0, 0, 0, 100), font=font)
        # Main text
        draw.text((text_x, text_y), text, fill=(255, 255, 255, 255), font=font)

    def _ensure_image_size(self, base64_image):
        """Resize base64 encoded image if dimensions exceed maximum allowed size
        
        Args:
            base64_image (str): Base64 encoded image string
            
        Returns:
            str: Potentially resized base64 encoded image string
        """
        try:
            # Decode base64 image
            image_data = base64.b64decode(base64_image)
            img = Image.open(io.BytesIO(image_data))
            
            # Check if image needs resizing
            width, height = img.size
            if width <= self.max_image_dimension and height <= self.max_image_dimension:
                # Image is already within size limits
                return base64_image
            
            # Calculate new dimensions while maintaining aspect ratio
            if width > height:
                new_width = self.max_image_dimension
                new_height = int(height * (self.max_image_dimension / width))
            else:
                new_height = self.max_image_dimension
                new_width = int(width * (self.max_image_dimension / height))
            
            # Perform resize
            logger.info(f"Resizing image from {width}x{height} to {new_width}x{new_height}")
            resized_img = img.resize((new_width, new_height), Image.LANCZOS)
            
            # Convert back to base64
            buffered = io.BytesIO()
            resized_img.save(buffered, format=img.format or "JPEG")
            return base64.b64encode(buffered.getvalue()).decode()
            
        except Exception as e:
            logger.error(f"Error resizing image: {str(e)}")
            # Return original image if resizing fails
            return base64_image

    def _calculate_callout_position(self, center_x, center_y, img_width, img_height, issue_index, total_issues):
        """
        Calculate the optimal position for a callout bubble based on the issue position.
        Positions callouts away from the issue to prevent overlapping.
        """
        # Determine which quadrant the issue is in
        in_right_half = center_x > img_width / 2
        in_bottom_half = center_y > img_height / 2
        
        # Calculate distance from edges
        dist_from_left = center_x
        dist_from_right = img_width - center_x
        dist_from_top = center_y
        dist_from_bottom = img_height - center_y
        
        # Place callout in the opposite quadrant from issue
        # This ensures the callout is far from the issue
        margin = max(img_width, img_height) * 0.05
        margin = max(margin, 30)  # Minimum margin
        
        # Offset by issue_index to prevent callouts from overlapping
        offset_x = (issue_index % 3) * 30
        offset_y = (issue_index % 3) * 20
        
        # Place callout in quadrant opposite to where issue is
        if in_right_half and in_bottom_half:
            # Issue in bottom-right, place callout in top-left
            callout_x = margin + offset_x
            callout_y = margin + offset_y
        elif in_right_half and not in_bottom_half:
            # Issue in top-right, place callout in bottom-left
            callout_x = margin + offset_x
            callout_y = img_height - margin - offset_y
        elif not in_right_half and in_bottom_half:
            # Issue in bottom-left, place callout in top-right
            callout_x = img_width - margin - offset_x
            callout_y = margin + offset_y
        else:
            # Issue in top-left, place callout in bottom-right
            callout_x = img_width - margin - offset_x
            callout_y = img_height - margin - offset_y
            
        # Create a bent pointer with intermediate points
        # This makes a smoother curve from callout to issue
        mid1_x = (2*callout_x + center_x) // 3
        mid1_y = (2*callout_y + center_y) // 3
        
        mid2_x = (callout_x + 2*center_x) // 3
        mid2_y = (callout_y + 2*center_y) // 3
        
        # Define pointer path with multiple points for a curved line
        pointer_points = [
            (int(callout_x), int(callout_y)),
            (int(mid1_x), int(mid1_y)),
            (int(mid2_x), int(mid2_y)),
        ]
        
        return int(callout_x), int(callout_y), pointer_points

    def _draw_legend(self, draw, legend_items, img_width, img_height, font):
        """Draw a legend explaining the marked issues at the bottom of the image"""
        if not legend_items:
            return
        
        # Configuration
        legend_margin = 20
        item_padding = 10
        color_box_size = 15
        line_height = 25
        
        # Calculate legend position (bottom of image)
        legend_y = img_height - legend_margin - (line_height * len(legend_items))
        
        # Draw semi-transparent background for legend
        padding = 10
        legend_width = img_width - (legend_margin * 2)
        legend_height = (line_height * len(legend_items)) + line_height + padding * 2  # Extra for title
        
        # Draw rounded rectangle background
        draw.rounded_rectangle(
            [(legend_margin - padding, legend_y - line_height - padding),
             (legend_margin + legend_width, legend_y + (line_height * len(legend_items)) + padding)],
            radius=10,
            fill=(0, 0, 0, 160)  # Semi-transparent black
        )
        
        # Draw legend title
        title = "Detected Issues:"
        draw.text((legend_margin, legend_y - line_height), title, 
                 fill=(255, 255, 255, 230), font=font)
        
        # Draw each legend item
        current_y = legend_y
        for issue_type, color in legend_items.items():
            # Draw color box
            draw.rectangle(
                [(legend_margin, current_y), 
                 (legend_margin + color_box_size, current_y + color_box_size)],
                fill=color, outline=(255, 255, 255, 200), width=1
            )
            
            # Draw issue type text
            text_x = legend_margin + color_box_size + item_padding
            draw.text((text_x, current_y), issue_type.capitalize(), 
                     fill=(255, 255, 255, 230), font=font)
            
            # Move to next line
            current_y += line_height

def update_model_based_on_feedback(feedback_entry):
    """Update the AI model or its behavior based on user feedback."""
    try:
        # Extract key information from feedback
        is_correct = feedback_entry.get("correct") == "Yes"
        username = feedback_entry.get("username", "anonymous")
        comments = feedback_entry.get("comments", "")
        detections = feedback_entry.get("detections", {})
        timestamp = feedback_entry.get("timestamp", datetime.utcnow().isoformat())
        
        # Log detailed feedback information
        logger.info(f"Processing feedback from {username}: Correct={is_correct}, Comments={comments}")
        
        # Store enriched feedback data with metadata for analysis
        enriched_feedback = {
            "original_feedback": feedback_entry,
            "metadata": {
                "processed_at": datetime.utcnow().isoformat(),
                "detection_count": sum(len(objs) for objs in detections.values()),
                "has_comments": bool(comments.strip()),
                "comment_length": len(comments) if comments else 0,
                "models_used": list(detections.keys())
            },
            "analysis": {
                "feedback_type": "positive" if is_correct else "negative",
                "requires_attention": not is_correct and bool(comments.strip()),
                "keywords": extract_keywords_from_comment(comments) if comments else []
            }
        }
        
        # Store the enriched feedback for future analysis
        feedback_collection.insert_one(enriched_feedback)
        
        # Calculate and update feedback statistics
        update_feedback_statistics()
        
        # Check if model behavior adjustment is needed based on recent feedback
        if should_adjust_model_behavior():
            adjust_model_parameters()
            
        logger.info(f"Feedback processing completed for user {username}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating model based on feedback: {str(e)}")
        return False

def extract_keywords_from_comment(comment):
    """Extract important keywords from feedback comments"""
    # Simple keyword extraction - in production this could use NLP
    keywords = []
    important_terms = [
        "missed", "wrong", "incorrect", "false", "positive", "negative", 
        "pothole", "garbage", "graffiti", "accurate", "good", "bad",
        "detection", "slow", "fast", "error"
    ]
    
    if comment:
        comment_lower = comment.lower()
        for term in important_terms:
            if term in comment_lower:
                keywords.append(term)
                
    return keywords

def update_feedback_statistics():
    """Update aggregate statistics on feedback for monitoring model performance"""
    try:
        # Define time windows for analysis
        now = datetime.utcnow()
        last_day = now - timedelta(days=1)
        last_week = now - timedelta(days=7)
        
        # Query recent feedback
        day_feedback = feedback_collection.find({"original_feedback.timestamp": {"$gte": last_day.isoformat()}})
        week_feedback = feedback_collection.find({"original_feedback.timestamp": {"$gte": last_week.isoformat()}})
        
        # Calculate statistics
        day_stats = calculate_feedback_metrics(day_feedback)
        week_stats = calculate_feedback_metrics(week_feedback)
        
        # Store statistics in a special document
        feedback_collection.update_one(
            {"_id": "statistics"},
            {"$set": {
                "last_updated": now.isoformat(),
                "daily_stats": day_stats,
                "weekly_stats": week_stats,
            }},
            upsert=True
        )
        
        logger.info(f"Updated feedback statistics: daily accuracy {day_stats.get('accuracy', 0):.2f}, weekly accuracy {week_stats.get('accuracy', 0):.2f}")
        
    except Exception as e:
        logger.error(f"Error updating feedback statistics: {str(e)}")

def calculate_feedback_metrics(feedback_cursor):
    """Calculate metrics from feedback data"""
    try:
        total = 0
        positive = 0
        has_comments = 0
        
        for item in feedback_cursor:
            total += 1
            if item.get("analysis", {}).get("feedback_type") == "positive":
                positive += 1
            if item.get("metadata", {}).get("has_comments", False):
                has_comments += 1
        
        # Avoid division by zero
        accuracy = (positive / total) * 100 if total > 0 else 0
        comment_rate = (has_comments / total) * 100 if total > 0 else 0
        
        return {
            "total_feedback": total,
            "positive_feedback": positive,
            "accuracy": accuracy,
            "feedback_with_comments": has_comments,
            "comment_rate": comment_rate
        }
        
    except Exception as e:
        logger.error(f"Error calculating feedback metrics: {str(e)}")
        return {"error": str(e)}

def should_adjust_model_behavior():
    """Determine if model behavior should be adjusted based on feedback trends"""
    try:
        # Get statistics document
        stats = feedback_collection.find_one({"_id": "statistics"})
        if not stats:
            return False
        
        # Check if accuracy has dropped significantly
        daily_accuracy = stats.get("daily_stats", {}).get("accuracy", 0)
        weekly_accuracy = stats.get("weekly_stats", {}).get("accuracy", 0)
        
        # Adjust if daily accuracy is significantly lower than weekly average
        return daily_accuracy < (weekly_accuracy * 0.8) and stats.get("daily_stats", {}).get("total_feedback", 0) >= 5
        
    except Exception as e:
        logger.error(f"Error in should_adjust_model_behavior: {str(e)}")
        return False

def adjust_model_parameters():
    """Adjust model parameters based on feedback trends"""
    try:
        # Retrieve recent negative feedback for analysis
        recent_negative = list(feedback_collection.find({
            "analysis.feedback_type": "negative",
            "original_feedback.timestamp": {"$gte": (datetime.utcnow() - timedelta(days=2)).isoformat()}
        }))
        
        # In a real system, we would analyze patterns in negative feedback
        # and adjust model parameters accordingly
        
        # Log that an adjustment would be happening
        logger.info(f"Model behavior adjustment triggered based on {len(recent_negative)} recent negative feedback items")
        
        # For demonstration, we're just recording that an adjustment was needed
        feedback_collection.update_one(
            {"_id": "model_adjustments"},
            {"$push": {
                "adjustments": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "trigger": "feedback_trend",
                    "negative_count": len(recent_negative)
                }
            }},
            upsert=True
        )
        
    except Exception as e:
        logger.error(f"Error adjusting model parameters: {str(e)}")

