

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml import parse_xml
from pptx.enum.shapes import MSO_SHAPE
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import json
import os
import tempfile

class JSONAdapter:
    @staticmethod
    def adapt_json_for_ppt(input_json_path, output_json_path):
        """Adapt the image retrieval JSON structure to match PPT generator expectations"""
        with open(input_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Transform the structure
        adapted_data = {
            "presentation_title": data.get("presentation_title", "AI Presentation"),
            "slides": []
        }
        
        for slide in data.get("slides", []):
            # Convert content to list format expected by PPT generator
            content_list = []
            if slide.get("content"):
                content_text = slide["content"]
                if isinstance(content_text, str):
                    # Split content by sentences or newlines for bullet points
                    sentences = [s.strip() for s in content_text.split('\n') if s.strip()]
                    content_list = sentences[:6]  # Limit to 6 bullet points
                else:
                    content_list = content_text
            
            # Adapt images structure
            suggested_images = []
            for img in slide.get("images", []):
                suggested_images.append({
                    "image_path": img.get("image_path", ""),
                    "caption": img.get("caption", "Image"),
                    "similarity_score": img.get("similarity_score", 0)
                })
            
            adapted_slide = {
                "slide_number": slide.get("slide_number", len(adapted_data["slides"]) + 1),
                "slide_title": slide.get("slide_title", "Untitled Slide"),
                "content": content_list,
                "suggested_images": suggested_images
            }
            
            adapted_data["slides"].append(adapted_slide)
        
        # Save adapted JSON
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(adapted_data, f, indent=2)
        
        print(f"✅ JSON adapted successfully for template4!")
        return adapted_data

class MinimalDarkPresentationGenerator:
    def __init__(self, json_file_path):
        self.json_file_path = json_file_path
        self.presentation_data = self.load_json_data()
        self.prs = None
        self.slide_width = Inches(13.33)
        self.slide_height = Inches(7.5)
        
    def load_json_data(self):
        """Load JSON data"""
        with open(self.json_file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    
    def create_presentation(self, output_path):
        """Main method - creates presentation with minimal dark theme"""
        print("🎨 Creating Minimal Dark Theme Presentation")
        
        # Create template and populate presentation
        template_path = self.create_clean_modern_template()
        self.populate_presentation(template_path, output_path)
        
        # Cleanup template
        if os.path.exists(template_path):
            os.remove(template_path)
            
        print(f"✅ Minimal Dark Presentation created: {output_path}")
    
    def create_clean_modern_template(self):
        """Create clean modern template with dark theme"""
        output_path = "temp_template_modern_dark.pptx"
        prs = Presentation()
        prs.slide_width = self.slide_width
        prs.slide_height = self.slide_height

        slide_layout = prs.slide_layouts[6]
        slide = prs.slides.add_slide(slide_layout)

        # Dark theme background
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(18, 18, 18)  # Dark background

        prs.save(output_path)
        return output_path

    def create_blurry_background(self, image_path, blur_radius=25, brightness=0.6):
        """Create a blurry background image from source image for dark theme"""
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # Calculate dimensions to maintain aspect ratio while covering slide
                slide_ratio = 13.33 / 7.5  # Widescreen ratio
                img_ratio = img.width / img.height

                if img_ratio > slide_ratio:
                    # Image is wider, crop height
                    new_height = img.height
                    new_width = int(new_height * slide_ratio)
                    left = (img.width - new_width) // 2
                    top = 0
                else:
                    # Image is taller, crop width
                    new_width = img.width
                    new_height = int(new_width / slide_ratio)
                    left = 0
                    top = (img.height - new_height) // 2

                # Crop and resize
                img_cropped = img.crop((left, top, left + new_width, top + new_height))
                img_resized = img_cropped.resize((1920, 1080), Image.Resampling.LANCZOS)

                # Apply blur and brightness (darker for dark theme)
                img_blurred = img_resized.filter(ImageFilter.GaussianBlur(blur_radius))

                # Adjust brightness for dark theme
                enhancer = ImageEnhance.Brightness(img_blurred)
                img_final = enhancer.enhance(brightness)

                # Save temporary file
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                img_final.save(temp_file.name, 'JPEG', quality=90)
                return temp_file.name

        except Exception as e:
            print(f"❌ Error creating blurry background: {e}")
            return None

    def create_rounded_image(self, image_path, radius=25):
        """Create rounded corner image"""
        try:
            with Image.open(image_path).convert("RGBA") as im:
                mask = Image.new("L", im.size, 0)
                draw = ImageDraw.Draw(mask)
                draw.rounded_rectangle((0, 0, *im.size), radius=radius, fill=255)
                im.putalpha(mask)
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                im.save(tmp.name, format="PNG")
                return tmp.name
        except Exception as e:
            print(f"❌ Error creating rounded image: {e}")
            return image_path

    def create_textbox_with_rounded_corners(self, slide, x, y, width, height, text, font_size, text_color):
        """Create individual textbox for each bullet point with rounded corners"""
        try:
            textbox = slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE,
                x, y, width, height
            )
            try:
                textbox.adjustments[0] = 0.05
            except Exception:
                pass

            # Dark theme styling
            textbox.fill.solid()
            textbox.fill.fore_color.rgb = RGBColor(30, 30, 30)  # Dark card background
            textbox.line.color.rgb = RGBColor(100, 100, 100)    # Gray border for dark theme
            textbox.line.width = Pt(1.2)

            # Clear and set text properly
            tf = textbox.text_frame
            tf.clear()
            p = tf.paragraphs[0]
            
            # FIXED: Remove double bullets and keep only one
            clean_text = str(text).replace('•', '').replace('▸', '').strip()
            p.text = "• " + clean_text  # Single bullet only
            
            tf.word_wrap = True
            tf.vertical_anchor = MSO_ANCHOR.MIDDLE  # Center text vertically

            # Small margins so text doesn't touch edges
            tf.margin_left = Inches(0.12)
            tf.margin_right = Inches(0.12)
            tf.margin_top = Inches(0.08)
            tf.margin_bottom = Inches(0.08)

            # Format paragraph - CENTERED TEXT
            p.font.name = "Segoe UI"
            p.font.size = Pt(font_size)
            p.font.color.rgb = text_color
            p.alignment = PP_ALIGN.CENTER  # Center aligned text

            return textbox
        except Exception as e:
            print(f"❌ Error creating textbox: {e}")
            return None

    def calculate_textbox_height(self, text, font_size, max_width):
        """Calculate dynamic height for textbox based on text content"""
        # INCREASED base height calculation
        base_height = Inches(0.8)  # Increased from 0.7 to 0.8

        # Adjust height based on text length and font size
        text_length = len(text)

        if text_length < 50:
            height = base_height
        elif text_length < 100:
            height = base_height + Inches(0.2)
        elif text_length < 150:
            height = base_height + Inches(0.3)
        elif text_length < 200:
            height = base_height + Inches(0.4)
        else:
            height = base_height + Inches(0.5)

        # Adjust for font size
        if font_size < 12:
            height += Inches(0.05)
        elif font_size > 16:
            height -= Inches(0.05)

        # Ensure minimum and maximum heights
        min_height = Inches(0.7)   # Increased minimum
        max_height = Inches(1.7)   # Increased maximum

        return max(min_height, min(height, max_height))

    def calculate_font_size(self, text, textbox_height):
        """Calculate optimal font size based on text length and textbox height"""
        text_length = len(text)

        # INCREASED font sizes for better readability
        if text_length < 30:
            font_size = 20
        elif text_length < 60:
            font_size = 19
        elif text_length < 100:
            font_size = 18
        elif text_length < 150:
            font_size = 17
        elif text_length < 200:
            font_size = 16
        else:
            font_size = 15

        # Adjust based on textbox height
        if textbox_height < Inches(0.7):
            font_size = max(14, font_size - 1)
        elif textbox_height > Inches(1.0):
            font_size = min(22, font_size + 1)

        return font_size

    def get_available_images(self, slide_data):
        """Get list of available images that actually exist"""
        available = []
        for img in slide_data.get("suggested_images", []):
            img_path = img.get("image_path", "")
            if img_path and os.path.exists(img_path):
                available.append(img)
        return available

    def populate_presentation(self, template_path, output_pptx):
        """Populate presentation with dark theme content"""
        prs = Presentation(template_path)
        slide_width = prs.slide_width
        slide_height = prs.slide_height
        base_slide = prs.slides[0]

        # Layout constants for dark theme
        LEFT_MARGIN = Inches(0.8)
        RIGHT_MARGIN = Inches(0.8)
        TOP_MARGIN = Inches(1.0)
        IMAGE_GAP = Inches(0.4)
        TEXT_GAP_DEFAULT = Inches(0.8)
        TEXT_GAP_REDUCED = Inches(0.4)

        # Dark theme color scheme
        TITLE_COLOR = RGBColor(255, 255, 255)      # White
        BODY_COLOR = RGBColor(220, 220, 220)       # Light gray
        ACCENT_COLOR = RGBColor(100, 150, 255)     # Blue accent
        CARD_BG_COLOR = RGBColor(30, 30, 30)       # Dark card background
        BORDER_COLOR = RGBColor(100, 100, 100)     # Gray border

        # INCREASED image size
        MAX_IMAGE_WIDTH = slide_width * 0.42  # Increased from 0.38 to 0.42
        MAX_IMAGE_HEIGHT = slide_height * 0.32  # Increased from 0.30 to 0.32

        # Find a background image from available images
        background_image_path = None
        for slide_data in self.presentation_data["slides"]:
            available_images = self.get_available_images(slide_data)
            if available_images:
                background_image_path = available_images[0]["image_path"]
                break

        # Create blurry background if image found
        blurry_bg_path = None
        if background_image_path and os.path.exists(background_image_path):
            print(f"🎨 Creating dark theme blurry background")
            blurry_bg_path = self.create_blurry_background(background_image_path, blur_radius=30, brightness=0.6)

        for idx, slide_data in enumerate(self.presentation_data["slides"]):
            if idx == 0:
                # Use the first slide as template for title slide
                slide = base_slide
            else:
                # Create new slide for content slides
                slide_layout = prs.slide_layouts[6]
                slide = prs.slides.add_slide(slide_layout)

            print(f"🧩 Creating Slide {idx + 1}/{len(self.presentation_data['slides'])}")

            # Add blurry background to ALL slides if available
            if blurry_bg_path:
                try:
                    # Clear any existing background first
                    background = slide.background
                    fill = background.fill
                    fill.solid()
                    fill.fore_color.rgb = RGBColor(18, 18, 18)

                    # Add blurry background image
                    pic = slide.shapes.add_picture(blurry_bg_path, 0, 0, width=slide_width, height=slide_height)
                    # Move background to back
                    slide.shapes._spTree.remove(pic._element)
                    slide.shapes._spTree.insert(0, pic._element)
                except Exception as e:
                    print(f"⚠️ Could not add blurry background to slide {idx + 1}: {e}")

            title = slide_data.get("slide_title", "")
            content = slide_data.get("content", [])
            if isinstance(content, str):
                content = [line.replace("•", "").replace('▸', '').strip() for line in content.split("\n") if line.strip()]

            available_images = self.get_available_images(slide_data)
            img_paths = [img["image_path"] for img in available_images]

            # ✅ Title-only first slide with dark theme styling
            if idx == 0:
                # Create elegant title card with dark theme
                card_width = Inches(10.0)
                card_height = Inches(4.0)
                card_x = (slide_width - card_width) / 2
                card_y = (slide_height - card_height) / 2

                # Semi-transparent dark background card
                title_card = slide.shapes.add_shape(
                    MSO_SHAPE.RECTANGLE,
                    card_x, card_y, card_width, card_height
                )
                title_card.fill.solid()
                title_card.fill.fore_color.rgb = RGBColor(30, 30, 30)
                title_card.line.color.rgb = BORDER_COLOR
                title_card.line.width = Pt(2.0)

                # Centered title box - REDUCED FONT SIZE
                title_box = slide.shapes.add_textbox(
                    card_x,
                    card_y + Inches(1.0),
                    card_width,
                    Inches(2.0)
                )
                tf = title_box.text_frame
                tf.text = self.presentation_data["presentation_title"]
                tf.word_wrap = True
                tf.vertical_anchor = MSO_ANCHOR.MIDDLE
                p = tf.paragraphs[0]
                p.font.name = "Segoe UI"
                p.font.size = Pt(38)  # REDUCED from 42 to 38
                p.font.bold = True
                p.font.color.rgb = TITLE_COLOR
                p.alignment = PP_ALIGN.CENTER

                # Add subtitle
                subtitle_box = slide.shapes.add_textbox(
                    card_x,
                    card_y + Inches(2.8),
                    card_width,
                    Inches(0.8)
                )
                tf_sub = subtitle_box.text_frame
                tf_sub.text = "AI-Powered Solution"
                tf_sub.vertical_anchor = MSO_ANCHOR.MIDDLE
                p_sub = tf_sub.paragraphs[0]
                p_sub.font.name = "Segoe UI"
                p_sub.font.size = Pt(20)
                p_sub.font.color.rgb = ACCENT_COLOR
                p_sub.alignment = PP_ALIGN.CENTER
                continue

            # ---- Clean Modern Title ----
            if title:
                title_box = slide.shapes.add_textbox(LEFT_MARGIN, Inches(0.5),
                                                     slide_width - RIGHT_MARGIN * 2, Inches(0.8))
                tf = title_box.text_frame
                p = tf.paragraphs[0]
                p.text = title
                p.font.name = "Segoe UI"
                p.font.size = Pt(28)
                p.font.bold = True
                p.font.color.rgb = TITLE_COLOR
                p.alignment = PP_ALIGN.CENTER

            # ============ CONTENT HANDLING WITH INDIVIDUAL TEXTBOXES ============
            if content:
                # Maximum 6 bullet points
                num_points = min(len(content), 6)

                if img_paths:
                    # ============ IMAGES PRESENT: USE GRID LAYOUT ============
                    print(f"   📷 Images found: {len(img_paths)} - Using grid layout")

                    # Layout positioning
                    is_image_left = (idx % 2 == 0)
                    text_gap = TEXT_GAP_REDUCED if is_image_left else TEXT_GAP_DEFAULT
                    image_x = LEFT_MARGIN if is_image_left else slide_width - MAX_IMAGE_WIDTH - RIGHT_MARGIN
                    text_x = image_x + MAX_IMAGE_WIDTH + text_gap if is_image_left else LEFT_MARGIN

                    # Grid configuration - 2 columns, rows computed
                    cols = 2
                    rows = (num_points + cols - 1) // cols

                    # Compute available width for text area
                    text_area_width = slide_width - (LEFT_MARGIN + RIGHT_MARGIN + MAX_IMAGE_WIDTH + text_gap)

                    # INCREASED textbox width and height
                    textbox_width = (text_area_width - Inches(0.3)) / cols

                    # Compute dynamic textbox height - INCREASED
                    available_vert = slide_height - TOP_MARGIN - Inches(1.0)
                    per_row_height = max(Inches(1.1), min(Inches(1.9), available_vert / max(rows, 1)))  # Increased
                    textbox_height = per_row_height - Inches(0.15)

                    textbox_gap = Inches(0.2)

                    # Calculate starting position for grid (centered vertically)
                    grid_total_height = (textbox_height * rows) + (textbox_gap * (rows - 1))
                    start_y = (slide_height - grid_total_height) / 2

                    # Create individual textboxes in 2x2 grid
                    for i, line in enumerate(content[:num_points]):
                        row = i // cols
                        col = i % cols
                        current_x = text_x + (col * (textbox_width + textbox_gap))
                        current_y = start_y + row * (textbox_height + textbox_gap)

                        # INCREASED font sizes for better readability
                        base_font = 16 if num_points <= 4 else 15
                        if len(line) > 140:
                            font_size = max(13, base_font - 3)
                        elif len(line) > 90:
                            font_size = max(14, base_font - 2)
                        elif len(line) > 60:
                            font_size = max(15, base_font - 1)
                        else:
                            font_size = base_font

                        # FIXED: Remove double bullets before creating textbox
                        clean_line = str(line).replace('•', '').replace('▸', '').strip()
                        
                        # Create individual textbox for each bullet point
                        self.create_textbox_with_rounded_corners(
                            slide=slide,
                            x=current_x,
                            y=current_y,
                            width=textbox_width,
                            height=textbox_height,
                            text=clean_line,
                            font_size=font_size,
                            text_color=BODY_COLOR
                        )

                else:
                    # ============ NO IMAGES: VERTICAL CENTERED TEXTBOXES ============
                    print(f"   ⚠️ No images found - Using vertical centered textboxes")

                    if num_points == 0:
                        content = ["No content available"]
                        num_points = 1

                    # Calculate dimensions for vertical layout
                    textbox_width = slide_width * 0.60
                    textbox_gap = Inches(0.15)

                    # Calculate dynamic heights and font sizes for each textbox
                    textbox_heights = []
                    font_sizes = []

                    for line in content[:num_points]:
                        temp_height = Inches(0.7)
                        font_size = self.calculate_font_size(line, temp_height)
                        height = self.calculate_textbox_height(line, font_size, textbox_width)
                        textbox_heights.append(height)
                        font_sizes.append(font_size)

                    # Calculate total height needed
                    total_height = sum(textbox_heights) + (textbox_gap * (num_points - 1))

                    # Center vertically
                    start_y = (slide_height - total_height) / 2
                    center_x = (slide_width - textbox_width) / 2

                    # Create individual textboxes in vertical stack
                    current_y = start_y
                    for i, line in enumerate(content[:num_points]):
                        textbox_height = textbox_heights[i]
                        font_size = font_sizes[i]

                        # FIXED: Remove double bullets
                        clean_line = str(line).replace('•', '').replace('▸', '').strip()
                        
                        self.create_textbox_with_rounded_corners(
                            slide=slide,
                            x=center_x,
                            y=current_y,
                            width=textbox_width,
                            height=textbox_height,
                            text=clean_line,
                            font_size=font_size,
                            text_color=BODY_COLOR
                        )

                        current_y += textbox_height + textbox_gap

            # ---- Add dark theme image cards (only if images available) ----
            if img_paths:
                # Calculate total height for all images with gaps
                image_heights = []
                for img_path in img_paths:
                    try:
                        with Image.open(img_path) as im:
                            w, h = im.size
                            aspect = w / h
                            width = MAX_IMAGE_WIDTH
                            height = width / aspect
                            if height > MAX_IMAGE_HEIGHT:
                                height = MAX_IMAGE_HEIGHT
                                width = height * aspect
                            image_heights.append((width, height))
                    except Exception as e:
                        image_heights.append((MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT))

                # Calculate total height including gaps
                total_height = sum(height for _, height in image_heights) + (IMAGE_GAP * (len(img_paths) - 1))

                # Center images properly
                current_top = (slide_height - total_height) / 2

                # Image position
                is_image_left = (idx % 2 == 0)
                image_x = LEFT_MARGIN if is_image_left else slide_width - MAX_IMAGE_WIDTH - RIGHT_MARGIN

                for img_idx, (img_path, (width, height)) in enumerate(zip(img_paths, image_heights)):
                    try:
                        rounded_path = self.create_rounded_image(img_path, radius=20)

                        # Dark theme card design
                        card_padding = Inches(0.1)
                        card_shape = slide.shapes.add_shape(
                            MSO_SHAPE.RECTANGLE,
                            image_x - card_padding,
                            current_top - card_padding,
                            width + card_padding * 2,
                            height + card_padding * 2
                        )
                        card_shape.fill.solid()
                        card_shape.fill.fore_color.rgb = RGBColor(30, 30, 30)
                        card_shape.line.color.rgb = BORDER_COLOR
                        card_shape.line.width = Pt(2.0)

                        slide.shapes.add_picture(rounded_path, image_x, current_top, width=width, height=height)
                        if rounded_path != img_path:
                            try:
                                os.remove(rounded_path)
                            except:
                                pass
                        current_top += height + IMAGE_GAP

                    except Exception as e:
                        print(f"  ❌ Error adding image {img_path}: {e}")
                        # Add dark theme placeholder
                        placeholder = slide.shapes.add_shape(
                            MSO_SHAPE.RECTANGLE,
                            image_x, current_top,
                            MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT * 0.5
                        )
                        placeholder.fill.solid()
                        placeholder.fill.fore_color.rgb = RGBColor(50, 50, 50)
                        placeholder.line.color.rgb = BORDER_COLOR
                        placeholder.line.width = Pt(2.0)

                        placeholder_text = slide.shapes.add_textbox(
                            image_x, current_top + MAX_IMAGE_HEIGHT * 0.25 - Inches(0.2),
                            MAX_IMAGE_WIDTH, Inches(0.4)
                        )
                        tf_placeholder = placeholder_text.text_frame
                        p_placeholder = tf_placeholder.paragraphs[0]
                        p_placeholder.text = "Image Not Available"
                        p_placeholder.font.name = "Segoe UI"
                        p_placeholder.font.size = Pt(12)
                        p_placeholder.font.color.rgb = RGBColor(150, 150, 150)
                        p_placeholder.alignment = PP_ALIGN.CENTER

                        current_top += MAX_IMAGE_HEIGHT * 0.5 + IMAGE_GAP

            # ---- Add Dark Theme Footer ----
            try:
                footer_line = slide.shapes.add_shape(
                    MSO_SHAPE.RECTANGLE,
                    Inches(0.0),
                    slide_height - Inches(0.3),
                    slide_width,
                    Inches(0.01)
                )
                footer_line.fill.solid()
                footer_line.fill.fore_color.rgb = RGBColor(80, 80, 80)
                footer_line.line.fill.background()

                # Add slide number
                slide_num = slide.shapes.add_textbox(
                    slide_width - Inches(0.8),
                    slide_height - Inches(0.25),
                    Inches(0.6), Inches(0.2)
                )
                tf_num = slide_num.text_frame
                p_num = tf_num.paragraphs[0]
                p_num.text = str(idx + 1)
                p_num.font.name = "Segoe UI"
                p_num.font.size = Pt(10)
                p_num.font.color.rgb = RGBColor(150, 150, 150)
                p_num.alignment = PP_ALIGN.RIGHT

                # Add project name
                project_text = slide.shapes.add_textbox(
                    Inches(0.3),
                    slide_height - Inches(0.25),
                    Inches(2.0), Inches(0.2)
                )
                tf_project = project_text.text_frame
                p_project = tf_project.paragraphs[0]
                p_project.text = "AI Presentation"
                p_project.font.name = "Segoe UI"
                p_project.font.size = Pt(10)
                p_project.font.color.rgb = RGBColor(150, 150, 150)
                p_project.alignment = PP_ALIGN.LEFT
            except Exception as e:
                print(f"⚠️ Error adding footer to slide {idx + 1}: {e}")

        # Clean up blurry background temp file
        if blurry_bg_path and os.path.exists(blurry_bg_path):
            try:
                os.remove(blurry_bg_path)
            except:
                pass

        # Save the presentation
        prs.save(output_pptx)