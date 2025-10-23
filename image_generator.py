import os
import random
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import numpy as np

class ImageGenerator:
    def __init__(self, output_dir=None):
        """Initialize the image generator"""
        if output_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            output_dir = os.path.join(base_dir, 'static', 'images', 'generated')

        self.output_dir = os.path.abspath(output_dir)
        self.ensure_directory_exists()
        
    def ensure_directory_exists(self):
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def generate_image(self, number_str=None, number=None, difficulty="medium"):
        """Generate a distorted digit image with difficulty scaling"""
        if number_str is None:
            if number is None:
                raise ValueError("Either number_str or number must be provided")
            number_str = str(number)
        elif number is not None:
            number_str = str(number)
        
        width, height = 400, 200
        bg_color = self.get_random_background()
        image = Image.new('RGB', (width, height), color=bg_color)
        draw = ImageDraw.Draw(image)
        
        # Choose random font size and font
        font_size = random.randint(60, 90)
        font = self.get_font(font_size)

        # Calculate text position (center)
        bbox = draw.textbbox((0, 0), number_str, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (width - text_width) // 2
        y = (height - text_height) // 2

        text_color = self.get_contrasting_color(bg_color)
        draw.text((x, y), number_str, fill=text_color, font=font)

        # Apply difficulty effects
        image = self.apply_difficulty_effects(image, difficulty)

        # Save
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"digits_{number_str}_{difficulty}_{timestamp}.png"
        filepath = os.path.join(self.output_dir, filename)
        image.save(filepath, "PNG")
        return filename

    # --------------------- Utility Functions ---------------------

    def get_font(self, font_size):
        """Try multiple font options"""
        font_paths = [
            "Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf"
        ]
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    return ImageFont.truetype(fp, font_size)
                except:
                    pass
        return ImageFont.load_default()

    def get_random_background(self):
        return tuple(random.randint(160, 255) for _ in range(3))
    
    def get_contrasting_color(self, bg_color):
        brightness = sum(bg_color) / 3
        return (0, 0, 0) if brightness > 180 else (255, 255, 255)
    
    # --------------------- Difficulty Logic ---------------------

    def apply_difficulty_effects(self, image, difficulty):
        """Apply multiple distortion and noise effects"""
        effects = {
            'easy':   {'noise': 0.01, 'lines': 1, 'blur': 0.2, 'distortion': 0.05, 'rotate': 2},
            'medium': {'noise': 0.03, 'lines': 2, 'blur': 0.5, 'distortion': 0.15, 'rotate': 5},
            'hard':   {'noise': 0.07, 'lines': 3, 'blur': 0.8, 'distortion': 0.3, 'rotate': 10},
            'expert': {'noise': 0.1,  'lines': 5, 'blur': 1.2, 'distortion': 0.5, 'rotate': 15},
            'insane': {'noise': 0.15, 'lines': 6, 'blur': 2.0, 'distortion': 0.8, 'rotate': 20}
        }

        params = effects.get(difficulty, effects['medium'])
        
        # Random slight rotation
        image = image.rotate(random.uniform(-params['rotate'], params['rotate']), expand=1, fillcolor=(255, 255, 255))

        # Random brightness and contrast adjustment
        image = ImageEnhance.Contrast(image).enhance(random.uniform(0.7, 1.3))
        image = ImageEnhance.Brightness(image).enhance(random.uniform(0.8, 1.2))

        # Add visual confusion elements
        image = self.add_random_lines(image, params['lines'])
        image = self.add_noise(image, params['noise'])
        image = self.apply_distortion(image, params['distortion'])

        if params['blur'] > 0:
            image = image.filter(ImageFilter.GaussianBlur(params['blur']))
        return image

    # --------------------- Visual Effects ---------------------

    def add_random_lines(self, image, num_lines):
        """Add colored random crossing lines"""
        draw = ImageDraw.Draw(image)
        width, height = image.size
        for _ in range(num_lines):
            line_color = tuple(random.randint(0, 255) for _ in range(3))
            draw.line(
                [(random.randint(0, width), random.randint(0, height)),
                 (random.randint(0, width), random.randint(0, height))],
                fill=line_color,
                width=random.randint(1, 3)
            )
        return image

    def add_noise(self, image, noise_level):
        """Add random colored noise"""
        if noise_level <= 0:
            return image

        np_image = np.array(image).astype(np.int16)
        noise = np.random.randint(-50, 50, np_image.shape)
        noisy = np.clip(np_image + noise * noise_level * 10, 0, 255).astype(np.uint8)
        return Image.fromarray(noisy)

    def apply_distortion(self, image, distortion_level):
        """Apply wave-like distortion"""
        if distortion_level <= 0:
            return image
        width, height = image.size
        src = np.array(image)
        dst = np.zeros_like(src)
        
        for y in range(height):
            for x in range(width):
                offset_x = int(distortion_level * 15 * np.sin(2 * np.pi * y / 40))
                offset_y = int(distortion_level * 10 * np.cos(2 * np.pi * x / 50))
                new_x = max(0, min(width - 1, x + offset_x))
                new_y = max(0, min(height - 1, y + offset_y))
                dst[y, x] = src[new_y, new_x]
        return Image.fromarray(dst)

    # --------------------- Cleanup ---------------------

    def cleanup_old_images(self, max_age_minutes=60):
        """Delete images older than given minutes"""
        try:
            now = datetime.now()
            for filename in os.listdir(self.output_dir):
                if filename.startswith("digits_"):
                    filepath = os.path.join(self.output_dir, filename)
                    file_time = datetime.fromtimestamp(os.path.getctime(filepath))
                    if (now - file_time).total_seconds() / 60 > max_age_minutes:
                        os.remove(filepath)
        except Exception as e:
            print(f"Cleanup error: {e}")
