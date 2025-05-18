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
import datetime
from datetime import datetime, timedelta, timezone
from db import feedback_collection

logger = logging.getLogger(__name__)


class GitHubAIClient:
    """Client for interacting with GitHub's AI models API"""

    def __init__(self):
        """Initialize the GitHub AI client with authentication"""
        load_dotenv()

        # Load both tokens
        self.tokens = [
            os.getenv("GITHUB_TOKEN_A"),
            os.getenv("GITHUB_TOKEN_S")
        ]

        # Ensure both tokens are set
        if not all(self.tokens):
            raise ValueError("Both GITHUB_TOKEN_A and GITHUB_TOKEN_S environment variables must be set")

        self.token_index = 0  # Start with the first token
        self.endpoint = "https://models.github.ai/inference"
        self.model = "openai/gpt-4.1"
        self.max_retries = int(os.getenv("GITHUB_AI_MAX_RETRIES", "3"))
        self.request_timeout = int(os.getenv("GITHUB_AI_TIMEOUT", "30"))
        self.max_image_dimension = int(os.getenv("MAX_IMAGE_DIMENSION", "1280"))
        logger.info(f"GitHub AI client initialized successfully")

    def _switch_token(self):
        """Switch to the next token in the list"""
        self.token_index = (self.token_index + 1) % len(self.tokens)
        logger.warning(f"Switching to next GitHub token. Now using token index {self.token_index}")

    def _get_headers(self):
        """Return headers with the current token"""
        return {
            "Authorization": f"Bearer {self.tokens[self.token_index]}",
            "Content-Type": "application/json"
        }

    def generate_interpretation(self, detections, base64_image=None, location=None):
        """Generate an interpretation of urban issues based on detection results and image

        Args:
            detections (dict): Dictionary of detection results from YOLO models
            base64_image (str, optional): Base64 encoded image data
            location (str, optional): Location of the image (for context)

        Returns:
            dict: Response with interpretation of urban issues and optional marked image
        """
        try:
            # NEW: Fetch recent feedbacks and summarize for the prompt
            recent_feedbacks = self._get_recent_feedbacks(limit=10)
            feedback_summary = self._summarize_feedbacks_for_prompt(recent_feedbacks)

            # Extract relevant detection information
            detection_summary = self._prepare_detection_summary(detections)

            # Resize image if needed
            if base64_image:
                base64_image = self._ensure_image_size(base64_image)

            # Create prompt for GitHub AI with instructions to identify issues regardless of detection results
            system_message = f"""You are an urban infrastructure analysis expert. Your task is to:
            1. Interpret detection results from pre-trained YOLO models that identify urban issues like potholes, garbage, and other 
            problems in city environments.
            2. Analyze the provided image directly to identify ANY urban issues, even if the detection models didn't find any.

            Before analyzing, consider the following recent user feedback about previous analyses to improve your accuracy:
            {feedback_summary}

            Provide a detailed analysis including:
            1. Summary of detected issues (from both the detection models and your direct image analysis)
            2. Additional issues you can identify in the image that weren't detected by the models
            3. Potential impact on the community
            4. Recommended actions for city officials and cost estimates for repairs(with respect to Romanian standards)
            5. Priority level (low/medium/high)

            IMPORTANT: Do not write anything else except the analysis. Do not include any other text or explanations.
            Instead of saying BozukYol, say "pothole" in English. Do not use "---" to separate sections.

            Format your response in Markdown. Format it in such a way that it looks aesthetically pleasing and fits
            well in a minimalistic modern web app design. Do not use tables. Do not state the positions found with YOLO Do not use possessive pronouns such as "my" or "your". Make it seem
            professional and talk directly to the user. For example, do not say "Upon direct inspection of the image, I have identified...". Say
            "Upon direct inspection of the image, the following issues have been identified...".
            """

            # Prepare user message with detection results
            user_message = f"""Here are the detection results from our urban analysis YOLO AI models:

            {detection_summary}
            """

            if location:
                user_message += f"\n\nLocation: {location}"

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
                        {"type": "text",
                         "text": "Here's the image for you to analyze directly. Please identify any urban issues you can see, even if they were not detected by our models. Remember to provide coordinates for issues in the format requested:"},
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

            while retry_count < self.max_retries:
                try:
                    logger.info(f"Sending request to GitHub AI (attempt {retry_count + 1}/{self.max_retries})")

                    response = requests.post(
                        f"{self.endpoint}/chat/completions",
                        headers=self._get_headers(),
                        json=payload,
                        timeout=self.request_timeout
                    )

                    # Check for rate limit
                    if response.status_code == 429:
                        logger.warning("Rate limited by GitHub AI.")
                        self._switch_token()  # Switch token
                        retry_count += 1
                        wait_time = min(2 ** retry_count, 8)  # Exponential backoff
                        logger.warning(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue

                    # Handle successful response
                    if response.status_code == 200:
                        result = response.json()
                        if "choices" in result and len(result["choices"]) > 0:
                            content = result["choices"][0]["message"]["content"]
                            logger.info("Successfully received response from GitHub AI.")
                            return {"status": "success", "evaluation": content}

                        logger.error("Unexpected response structure from GitHub AI.")
                        return {"status": "error", "message": "Unexpected response structure from GitHub AI."}

                    # Handle other error responses
                    logger.error(f"GitHub AI request failed with status {response.status_code}: {response.text}")
                    return {"status": "error", "message": f"GitHub AI request failed: {response.status_code}"}

                except requests.exceptions.Timeout:
                    logger.warning("Request to GitHub AI timed out.")
                    retry_count += 1
                    wait_time = min(2 ** retry_count, 8)
                    logger.warning(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)

                except Exception as e:
                    logger.error(f"Error during GitHub AI request: {str(e)}")
                    return {"status": "error", "message": f"Error during request: {str(e)}"}

            # All retries exhausted
            logger.error("All retry attempts exhausted. No valid response from GitHub AI.")
            return {"status": "error", "message": "All retry attempts failed. No valid response from GitHub AI."}

        except Exception as e:
            logger.error(f"Error in generate_interpretation: {str(e)}")
            return {"status": "error", "message": f"Failed to generate interpretation: {str(e)}"}

    def _get_recent_feedbacks(self, limit=10):
        """Fetch recent feedbacks from the database"""
        try:
            # Sort by timestamp descending, get the most recent feedbacks
            feedbacks = list(feedback_collection.find().sort("timestamp", -1).limit(limit))
            return feedbacks
        except Exception as e:
            logger.error(f"Error fetching recent feedbacks: {str(e)}")
            return []

    def _summarize_feedbacks_for_prompt(self, feedbacks):
        """Summarize feedbacks for inclusion in the system prompt"""
        if not feedbacks:
            return "No recent feedback available."

        summary_lines = []
        for fb in feedbacks:
            correct = fb.get("correct", "Unknown")
            comments = fb.get("comments", "")
            # Only include feedback with comments or negative feedback
            if comments or correct == "No":
                line = f"- Feedback: {'Correct' if correct == "Yes" else 'Incorrect'}"
                if comments:
                    line += f"; Comment: {comments.strip()}"
                summary_lines.append(line)
        if not summary_lines:
            return "No significant feedback to consider."
        return "\n".join(summary_lines)

    def _prepare_detection_summary(self, detections):
        """Format detection results into a readable summary for the AI"""
        summary = []

        for model_name, objects in detections.items():
            if objects:
                model_line = f"**{model_name}**: Detected {len(objects)} objects:"
                summary.append(model_line)

                for obj in objects:
                    obj_line = f"- {obj['name']} (confidence: {obj['confidence'] * 100:.1f}%)"
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
                "pothole": (255, 0, 0),  # Red
                "garbage": (255, 165, 0),  # Orange
                "graffiti": (0, 0, 255),  # Blue
                "damaged": (128, 0, 128),  # Purple
                "broken": (128, 0, 128),  # Purple
                "crack": (255, 255, 0),  # Yellow
                "litter": (255, 165, 0),  # Orange
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

    def _ensure_image_size(self, base64_image):
        """Ensure image is not too large for processing"""
        try:
            # Decode base64 image
            image_data = base64.b64decode(base64_image)
            img = Image.open(io.BytesIO(image_data)).convert("RGB")

            width, height = img.size

            # If image is already small enough, return it as is
            if width <= self.max_image_dimension and height <= self.max_image_dimension:
                return base64_image

            logger.info(f"Resizing large image from {width}x{height} for GitHub AI processing")

            # Calculate resize factor
            if width > height:
                resize_factor = self.max_image_dimension / width
            else:
                resize_factor = self.max_image_dimension / height

            # Resize image
            new_width = int(width * resize_factor)
            new_height = int(height * resize_factor)
            img = img.resize((new_width, new_height), Image.LANCZOS)

            # Convert back to base64
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG", quality=85)
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
        timestamp = feedback_entry.get("timestamp", datetime.now(timezone.utc).isoformat())

        # Log detailed feedback information
        logger.info(f"Processing feedback from {username}: Correct={is_correct}, Comments={comments}")

        # Store enriched feedback data with metadata for analysis
        enriched_feedback = {
            "original_feedback": feedback_entry,
            "metadata": {
                "processed_at": datetime.now(timezone.utc).isoformat(),
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
        now = datetime.now(timezone.utc)
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
            "original_feedback.timestamp": {"$gte": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()}
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
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "trigger": "feedback_trend",
                    "negative_count": len(recent_negative)
                }
            }},
            upsert=True
        )

    except Exception as e:
        logger.error(f"Error adjusting model parameters: {str(e)}")


