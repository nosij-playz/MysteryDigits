import os
import random
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import numpy as np

class ImageGenerator:
    def __init__(self, output_dir="static/images/generated"):
        self.output_dir = output_dir
        self.ensure_directory_exists()
        
    def ensure_directory_exists(self):
        """Create output directory if it doesn't exist"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def generate_image(self, number_str=None, number=None, difficulty="medium"):
        """Generate a distorted digit image"""
        # Handle both number_str and number parameters
        if number_str is None:
            if number is None:
                raise ValueError("Either number_str or number must be provided")
            number_str = str(number)
        elif number is not None:
            number_str = str(number)
        
        # Image dimensions
        width, height = 400, 200
        
        # Create blank image with random background color
        bg_color = self.get_random_background()
        image = Image.new('RGB', (width, height), color=bg_color)
        draw = ImageDraw.Draw(image)
        
        # Try to use a system font, fallback to default
        try:
            font_size = random.randint(60, 80)
            font = ImageFont.truetype("Arial.ttf", font_size)
        except:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
            except:
                font = ImageFont.load_default()
        
        # Calculate text position (centered)
        bbox = draw.textbbox((0, 0), number_str, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (width - text_width) // 2 - bbox[0]
        y = (height - text_height) // 2 - bbox[1]
        
        # Draw the text
        text_color = self.get_contrasting_color(bg_color)
        draw.text((x, y), number_str, fill=text_color, font=font)
        
        # Apply difficulty-based distortions
        image = self.apply_difficulty_effects(image, difficulty)
        
        # Generate filename and save
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"digits_{number_str}_{difficulty}_{timestamp}.png"
        filepath = os.path.join(self.output_dir, filename)
        
        image.save(filepath, "PNG")
        return filename
    
    def get_random_background(self):
        """Generate a random background color"""
        return tuple(random.randint(180, 255) for _ in range(3))
    
    def get_contrasting_color(self, bg_color):
        """Get a contrasting text color"""
        brightness = sum(bg_color) / 3
        return (0, 0, 0) if brightness > 200 else (255, 255, 255)
    
    def apply_difficulty_effects(self, image, difficulty):
        """Apply effects based on difficulty level"""
        effects = {
            'easy': {'noise': 0.01, 'lines': 1, 'blur': 0, 'distortion': 0.1},
            'medium': {'noise': 0.03, 'lines': 2, 'blur': 0.5, 'distortion': 0.3},
            'hard': {'noise': 0.06, 'lines': 3, 'blur': 1, 'distortion': 0.5},
            'expert': {'noise': 0.1, 'lines': 5, 'blur': 1.5, 'distortion': 0.8}
        }
        
        params = effects.get(difficulty, effects['medium'])
        
        # Add random lines
        image = self.add_random_lines(image, params['lines'])
        
        # Add noise
        image = self.add_noise(image, params['noise'])
        
        # Apply distortion
        image = self.apply_distortion(image, params['distortion'])
        
        # Apply blur
        if params['blur'] > 0:
            image = image.filter(ImageFilter.GaussianBlur(params['blur']))
        
        return image
    
    def add_random_lines(self, image, num_lines):
        """Add random crossing lines"""
        draw = ImageDraw.Draw(image)
        width, height = image.size
        
        for _ in range(num_lines):
            # Random line color (semi-transparent)
            line_color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), 128)
            
            # Random start and end points
            x1 = random.randint(0, width)
            y1 = random.randint(0, height)
            x2 = random.randint(0, width)
            y2 = random.randint(0, height)
            
            # Draw line
            draw.line([(x1, y1), (x2, y2)], fill=line_color, width=random.randint(1, 3))
        
        return image
    
    def add_noise(self, image, noise_level):
        """Add random noise to the image"""
        if noise_level <= 0:
            return image
            
        width, height = image.size
        pixels = image.load()
        
        for _ in range(int(width * height * noise_level)):
            x = random.randint(0, width - 1)
            y = random.randint(0, height - 1)
            pixels[x, y] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        
        return image
    
    def apply_distortion(self, image, distortion_level):
        """Apply wave-like distortion"""
        if distortion_level <= 0:
            return image
            
        width, height = image.size
        distorted = Image.new('RGB', (width, height))
        
        # Convert to numpy for manipulation
        src_array = np.array(image)
        dst_array = np.zeros_like(src_array)
        
        for y in range(height):
            for x in range(width):
                # Sine wave distortion
                offset_x = int(distortion_level * 10 * np.sin(2 * np.pi * y / 50))
                offset_y = int(distortion_level * 5 * np.cos(2 * np.pi * x / 60))
                
                new_x = max(0, min(width - 1, x + offset_x))
                new_y = max(0, min(height - 1, y + offset_y))
                
                dst_array[y, x] = src_array[new_y, new_x]
        
        return Image.fromarray(dst_array)
    
    def cleanup_old_images(self, max_age_minutes=60):
        """Remove images older than specified minutes"""
        try:
            current_time = datetime.now()
            for filename in os.listdir(self.output_dir):
                if filename.startswith("digits_"):
                    filepath = os.path.join(self.output_dir, filename)
                    file_time = datetime.fromtimestamp(os.path.getctime(filepath))
                    age_minutes = (current_time - file_time).total_seconds() / 60
                    
                    if age_minutes > max_age_minutes:
                        os.remove(filepath)
        except Exception as e:
            print(f"Cleanup error: {e}")