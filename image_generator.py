import os
import random
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps
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
        """Generate an unreadable chaotic image for any difficulty"""
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
        
        # Random font
        font_size = random.randint(60, 90)
        font = self.get_font(font_size)

        # Center text
        bbox = draw.textbbox((0, 0), number_str, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (width - text_width) // 2
        y = (height - text_height) // 2

        text_color = self.get_contrasting_color(bg_color)
        draw.text((x, y), number_str, fill=text_color, font=font)

        # Apply extreme chaotic effects (all levels)
        image = self.apply_difficulty_effects(image, difficulty)

        # Save image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"digits_{number_str}_{difficulty}_{timestamp}.png"
        filepath = os.path.join(self.output_dir, filename)
        image.save(filepath, "PNG")
        return filename

    # --------------------- Font & Color Utilities ---------------------

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

    # --------------------- Universal Chaos Logic ---------------------

    def apply_difficulty_effects(self, image, difficulty):
        """All difficulty levels look impossible but vary in chaos style"""
        styles = {
            'easy':   self.chaos_style_1,
            'medium': self.chaos_style_2,
            'hard':   self.chaos_style_3,
            'expert': self.chaos_style_4,
            'insane': self.chaos_style_5
        }
        func = styles.get(difficulty, self.chaos_style_2)
        return func(image)

    # --------------------- Chaos Styles (All Extreme) ---------------------

    def chaos_style_1(self, image):
        """Soft-color chaos with blur and inversion"""
        return self._obliterate(image, noise=0.25, blur=3, lines=12, swirl=True, invert=True)

    def chaos_style_2(self, image):
        """Pixelated mosaic noise and heavy contrast shifts"""
        return self._obliterate(image, noise=0.3, blur=2.5, lines=14, pixelate=True, contrast=True)

    def chaos_style_3(self, image):
        """Wave distortion with random hue inversion"""
        return self._obliterate(image, noise=0.2, blur=3.5, lines=15, wave=True, invert=True)

    def chaos_style_4(self, image):
        """High brightness flicker and full swirl chaos"""
        return self._obliterate(image, noise=0.35, blur=4, lines=16, swirl=True, invert=True, brightness=True)

    def chaos_style_5(self, image):
        """Extreme distortion, blur, and color corruption"""
        return self._obliterate(image, noise=0.4, blur=5, lines=18, pixelate=True, wave=True, invert=True)

    # --------------------- Core Obliteration Engine ---------------------

    def _obliterate(self, image, noise=0.2, blur=3, lines=10, swirl=False, wave=False,
                    pixelate=False, invert=False, contrast=False, brightness=False):
        """Apply extreme chaos to destroy visual meaning"""
        width, height = image.size
        img = image.convert("RGB")

        # Rotate randomly
        img = img.rotate(random.uniform(-40, 40), expand=1, fillcolor=(255, 255, 255))

        np_img = np.array(img).astype(np.uint8)

        # Heavy noise
        noise_matrix = np.random.randint(0, 256, np_img.shape, dtype=np.uint8)
        mixed = np_img * (1 - noise) + noise_matrix * noise
        np_img = np.clip(mixed, 0, 255).astype(np.uint8)

        # Pixelation
        if pixelate:
            factor = random.randint(6, 18)
            small = Image.fromarray(np_img).resize((width // factor, height // factor), Image.BILINEAR)
            np_img = np.array(small.resize((width, height), Image.NEAREST))

        img = Image.fromarray(np_img)

        # Random inversion
        if invert and random.random() > 0.3:
            img = ImageOps.invert(img)

        # Contrast/Brightness flickers
        if contrast:
            img = ImageEnhance.Contrast(img).enhance(random.uniform(0.2, 3.0))
        if brightness:
            img = ImageEnhance.Brightness(img).enhance(random.uniform(0.3, 2.0))

        # Swirl/Wave distortions
        if swirl:
            img = self.apply_swirl(img)
        if wave:
            img = self.apply_wave(img)

        # Add crossing lines
        img = self.add_random_lines(img, lines)

        # Random Gaussian blur
        img = img.filter(ImageFilter.GaussianBlur(blur))

        # Random channel inversion
        if random.random() > 0.5:
            arr = np.array(img)
            ch = random.randint(0, 2)
            arr[:, :, ch] = 255 - arr[:, :, ch]
            img = Image.fromarray(arr)

        return img

    # --------------------- Distortion Functions ---------------------

    def apply_wave(self, image):
        """Wave distortion"""
        width, height = image.size
        src = np.array(image)
        dst = np.zeros_like(src)
        for y in range(height):
            for x in range(width):
                offset_x = int(10 * np.sin(2 * np.pi * y / 30))
                offset_y = int(8 * np.cos(2 * np.pi * x / 25))
                new_x = max(0, min(width - 1, x + offset_x))
                new_y = max(0, min(height - 1, y + offset_y))
                dst[y, x] = src[new_y, new_x]
        return Image.fromarray(dst)

    def apply_swirl(self, image):
        """Swirl effect"""
        width, height = image.size
        cx, cy = width // 2, height // 2
        src = np.array(image)
        dst = np.zeros_like(src)
        strength = random.uniform(3, 6)
        for y in range(height):
            for x in range(width):
                dx, dy = x - cx, y - cy
                r = np.sqrt(dx*dx + dy*dy)
                angle = np.arctan2(dy, dx) + strength * r / width
                new_x = int(cx + r * np.cos(angle))
                new_y = int(cy + r * np.sin(angle))
                if 0 <= new_x < width and 0 <= new_y < height:
                    dst[y, x] = src[new_y, new_x]
        return Image.fromarray(dst)

    def add_random_lines(self, image, num_lines):
        """Add chaotic lines"""
        draw = ImageDraw.Draw(image)
        width, height = image.size
        for _ in range(num_lines):
            color = tuple(random.randint(0, 255) for _ in range(3))
            draw.line(
                [(random.randint(0, width), random.randint(0, height)),
                 (random.randint(0, width), random.randint(0, height))],
                fill=color,
                width=random.randint(2, 6)
            )
        return image

    # --------------------- Cleanup ---------------------

    def cleanup_old_images(self, max_age_minutes=60):
        """Delete generated images older than given minutes"""
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
