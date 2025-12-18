# # # 


# # # custom_template_generator.py

# # from pptx import Presentation
# # from pptx.util import Inches, Pt
# # from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
# # from pptx.dml.color import RGBColor
# # from PIL import Image, ImageDraw
# # import json, os, tempfile

# # def generate_presentation_with_custom_template(json_path: str, template_path: str, output_path: str):
# #     """
# #     Generate presentation using custom template without user input
# #     """
# #     print(f"🎨 Generating presentation with custom template: {template_path}")
    
# #     # Load the template
# #     prs = Presentation(template_path)
# #     slide_width = prs.slide_width
# #     slide_height = prs.slide_height

# #     # Remove all existing slides
# #     for i in range(len(prs.slides) - 1, -1, -1):
# #         rId = prs.slides._sldIdLst[i].rId
# #         prs.part.drop_rel(rId)
# #         del prs.slides._sldIdLst[i]

# #     # Choose Title + Content layout
# #     title_content_layout = None
# #     for layout in prs.slide_layouts:
# #         if "title" in (layout.name or "").lower() and "content" in (layout.name or "").lower():
# #             title_content_layout = layout
# #             break
# #     if not title_content_layout:
# #         title_content_layout = prs.slide_layouts[0]

# #     # Load slides data from JSON
# #     with open(json_path, "r", encoding="utf-8") as f:
# #         slides_data = json.load(f).get("slides", [])

# #     def create_rounded_image(image_path, radius=40):
# #         with Image.open(image_path).convert("RGBA") as im:
# #             mask = Image.new("L", im.size, 0)
# #             draw = ImageDraw.Draw(mask)
# #             draw.rounded_rectangle((0, 0, *im.size), radius=radius, fill=255)
# #             im.putalpha(mask)
# #             tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
# #             im.save(tmp.name, format="PNG")
# #         return tmp.name

# #     # Layout constants
# #     LEFT_MARGIN = Inches(0.6)
# #     TOP_MARGIN = Inches(1.0)
# #     IMAGE_MARGIN = Inches(0.3)
# #     TITLE_HEIGHT = Inches(1.0)
# #     MAX_IMAGE_WIDTH = slide_width * 0.38
# #     MAX_IMAGE_HEIGHT = slide_height * 0.30
# #     TEXT_WIDTH = slide_width * 0.52

# #     # Detect theme brightness (dark/light)
# #     def get_brightness(r, g, b):
# #         return (0.299 * r + 0.587 * g + 0.114 * b)

# #     def detect_background_color(slide):
# #         fill = slide.background.fill
# #         if not fill:
# #             return RGBColor(255, 255, 255)
# #         try:
# #             if fill.type == 1 and fill.fore_color and fill.fore_color.rgb:
# #                 return fill.fore_color.rgb
# #         except Exception:
# #             pass
# #         return RGBColor(255, 255, 255)

# #     def detect_theme_brightness(pptx_path):
# #         prs_check = Presentation(pptx_path)
# #         slide = prs_check.slides[0]
# #         bg_color = detect_background_color(slide)
# #         r, g, b = bg_color
# #         brightness = get_brightness(r, g, b)
# #         if brightness <= 85:
# #             return "dark"
# #         elif brightness <= 170:
# #             return "medium"
# #         else:
# #             return "light"

# #     theme_type = detect_theme_brightness(template_path)
# #     border_color = RGBColor(255, 255, 255) if theme_type == "dark" else RGBColor(0, 0, 0)

# #     for idx, slide_info in enumerate(slides_data):
# #         slide = prs.slides.add_slide(title_content_layout)

# #         # Remove placeholders
# #         for shape in list(slide.shapes):
# #             if shape.has_text_frame or shape.is_placeholder:
# #                 try:
# #                     sp = shape._element
# #                     sp.getparent().remove(sp)
# #                 except Exception:
# #                     pass

# #         # Check if this is the first slide (title slide)
# #         is_first_slide = (idx == 0)

# #         if is_first_slide:
# #             # First slide - title centered in middle
# #             title = slide_info.get("slide_title", "")
# #             if title:
# #                 # Center the title vertically and horizontally
# #                 title_box = slide.shapes.add_textbox(
# #                     left=Inches(0),
# #                     top=(slide_height - Inches(2)) / 2,  # Center vertically
# #                     width=slide_width,
# #                     height=Inches(2)
# #                 )
# #                 p = title_box.text_frame.paragraphs[0]
# #                 p.text = title
# #                 p.font.size = Pt(32)  # Larger font for title slide
# #                 p.font.bold = True
# #                 p.font.color.rgb = RGBColor(0, 51, 102)
# #                 p.alignment = PP_ALIGN.CENTER
# #                 p.vertical_anchor = MSO_ANCHOR.MIDDLE  # Center vertically within textbox

# #         else:
# #             # Other slides - normal layout
# #             is_image_left = ((idx + 1) % 2 == 1)
# #             image_x = LEFT_MARGIN if is_image_left else slide_width - MAX_IMAGE_WIDTH - LEFT_MARGIN
# #             text_x = slide_width - TEXT_WIDTH - LEFT_MARGIN if is_image_left else LEFT_MARGIN

# #             # Title for non-first slides
# #             title = slide_info.get("slide_title", "")
# #             if title:
# #                 title_box = slide.shapes.add_textbox(left=Inches(0), top=Inches(0.3),
# #                                                      width=slide_width, height=TITLE_HEIGHT)
# #                 p = title_box.text_frame.paragraphs[0]
# #                 p.text = title
# #                 p.font.size = Pt(26)
# #                 p.font.bold = True
# #                 p.font.color.rgb = RGBColor(0, 51, 102)
# #                 p.alignment = PP_ALIGN.CENTER

# #             # Content (Parse bullet points from content string)
# #             content_text = slide_info.get("content", "")
# #             if content_text:
# #                 # Parse bullet points from the content string
# #                 bullet_points = [line.strip('• \n') for line in content_text.split('\n') if line.strip()]

# #                 # Dynamic textbox height based on number of bullet points
# #                 if len(bullet_points) <= 3:
# #                     text_height = slide_height * 0.30
# #                 elif len(bullet_points) <= 7:
# #                     text_height = slide_height * 0.45
# #                 else:
# #                     text_height = slide_height * 0.65

# #                 text_y = (slide_height - text_height) / 2 if len(bullet_points) <= 3 else TOP_MARGIN + Inches(0.5)

# #                 text_box = slide.shapes.add_textbox(text_x, text_y, TEXT_WIDTH, text_height)
# #                 tf = text_box.text_frame
# #                 tf.word_wrap = True
# #                 tf.vertical_anchor = MSO_ANCHOR.MIDDLE if len(bullet_points) <= 3 else MSO_ANCHOR.TOP

# #                 font_size = 18 if len(bullet_points) <= 5 else 14 if len(bullet_points) <= 10 else 12
# #                 for point in bullet_points:
# #                     p = tf.add_paragraph()
# #                     p.text = f"• {point}"
# #                     p.font.size = Pt(font_size)
# #                     p.font.color.rgb = RGBColor(40, 40, 40)

# #             # Images with border (using "images" array from JSON)
# #             images_data = slide_info.get("images", [])
# #             img_paths = []
# #             for img_info in images_data[:2]:  # Max 2 images per slide
# #                 img_path = img_info.get("image_path", "")
# #                 if os.path.exists(img_path):
# #                     img_paths.append(img_path)
            
# #             if img_paths:
# #                 total_height = MAX_IMAGE_HEIGHT * len(img_paths) + IMAGE_MARGIN * (len(img_paths) - 1)
# #                 current_top = (slide_height - total_height) / 2
# #                 for img_path in img_paths:
# #                     try:
# #                         with Image.open(img_path) as im:
# #                             w, h = im.size
# #                             aspect = w / h
# #                             width = MAX_IMAGE_WIDTH
# #                             height = width / aspect
# #                             if height > MAX_IMAGE_HEIGHT:
# #                                 height = MAX_IMAGE_HEIGHT
# #                                 width = height * aspect
# #                         rounded_path = create_rounded_image(img_path)
# #                         picture = slide.shapes.add_picture(rounded_path, image_x, current_top, width=width, height=height)

# #                         # Add border rectangle around image only
# #                         border = slide.shapes.add_shape(
# #                             1,  # MSO_SHAPE.RECTANGLE
# #                             image_x - Inches(0.05),
# #                             current_top - Inches(0.05),
# #                             width + Inches(0.1),
# #                             height + Inches(0.1)
# #                         )
# #                         border.fill.background()
# #                         border.line.color.rgb = border_color
# #                         border.line.width = Pt(3)
# #                         # Move border behind image
# #                         slide.shapes._spTree.remove(border._element)
# #                         slide.shapes._spTree.insert(0, border._element)

# #                         os.remove(rounded_path)
# #                         current_top += height + IMAGE_MARGIN
# #                     except Exception as e:
# #                         print(f"❌ Error adding image {img_path}: {e}")

# #     prs.save(output_path)
# #     print(f"✅ Final presentation saved: {output_path}")




# from pptx import Presentation
# from pptx.util import Inches, Pt
# from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
# from pptx.dml.color import RGBColor
# from pptx.enum.shapes import MSO_SHAPE
# from PIL import Image, ImageDraw
# import json, os, tempfile

# def generate_presentation_with_custom_template(json_path: str, template_path: str, output_path: str):
#     """
#     Generate presentation using custom template without user input
#     This function matches the FastAPI endpoint signature
#     """
#     print(f"🎨 Generating presentation with custom template: {template_path}")
    
#     # Load the template
#     prs = Presentation(template_path)
#     slide_width = prs.slide_width
#     slide_height = prs.slide_height

#     # Remove all existing slides
#     for i in range(len(prs.slides) - 1, -1, -1):
#         rId = prs.slides._sldIdLst[i].rId
#         prs.part.drop_rel(rId)
#         del prs.slides._sldIdLst[i]

#     # Choose Title + Content layout
#     title_content_layout = None
#     for layout in prs.slide_layouts:
#         if "title" in (layout.name or "").lower() and "content" in (layout.name or "").lower():
#             title_content_layout = layout
#             break
#     if not title_content_layout:
#         title_content_layout = prs.slide_layouts[0]

#     # Load slides data from JSON
#     with open(json_path, "r", encoding="utf-8") as f:
#         slides_data = json.load(f).get("slides", [])

#     def create_rounded_image(image_path, radius=40):
#         with Image.open(image_path).convert("RGBA") as im:
#             mask = Image.new("L", im.size, 0)
#             draw = ImageDraw.Draw(mask)
#             draw.rounded_rectangle((0, 0, *im.size), radius=radius, fill=255)
#             im.putalpha(mask)
#             tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
#             im.save(tmp.name, format="PNG")
#         return tmp.name

#     # Layout constants
#     LEFT_MARGIN = Inches(0.6)
#     TOP_MARGIN = Inches(1.0)
#     IMAGE_MARGIN = Inches(0.3)
#     TITLE_HEIGHT = Inches(1.0)
#     MAX_IMAGE_WIDTH = slide_width * 0.38
#     MAX_IMAGE_HEIGHT = slide_height * 0.30
#     TEXT_WIDTH = slide_width * 0.52

#     # Default settings (no user input)
#     USER_FONT_CHOICE = "Calibri"
#     TITLE_COLOR = RGBColor(0, 51, 102)
#     BODY_COLOR = RGBColor(40, 40, 40)
#     IMAGE_BORDER_COLOR = RGBColor(0, 0, 0)

#     for idx, slide_info in enumerate(slides_data):
#         slide = prs.slides.add_slide(title_content_layout)

#         # Remove placeholders
#         for shape in list(slide.shapes):
#             if shape.has_text_frame or shape.is_placeholder:
#                 try:
#                     sp = shape._element
#                     sp.getparent().remove(sp)
#                 except Exception:
#                     pass

#         # Check if this is the first slide (title slide)
#         is_first_slide = (idx == 0)

#         if is_first_slide:
#             # First slide - title centered in middle
#             title = slide_info.get("slide_title", "")
#             if title:
#                 # Center the title vertically and horizontally
#                 title_box = slide.shapes.add_textbox(
#                     left=Inches(0),
#                     top=(slide_height - Inches(2)) / 2,  # Center vertically
#                     width=slide_width,
#                     height=Inches(2)
#                 )
#                 p = title_box.text_frame.paragraphs[0]
#                 p.text = title
#                 p.font.size = Pt(32)  # Larger font for title slide
#                 p.font.bold = True
#                 p.font.color.rgb = TITLE_COLOR
#                 p.alignment = PP_ALIGN.CENTER
#                 p.vertical_anchor = MSO_ANCHOR.MIDDLE  # Center vertically within textbox

#         else:
#             # Other slides - normal layout
#             is_image_left = ((idx + 1) % 2 == 1)
#             image_x = LEFT_MARGIN if is_image_left else slide_width - MAX_IMAGE_WIDTH - LEFT_MARGIN
#             text_x = slide_width - TEXT_WIDTH - LEFT_MARGIN if is_image_left else LEFT_MARGIN

#             # Title for non-first slides
#             title = slide_info.get("slide_title", "")
#             if title:
#                 title_box = slide.shapes.add_textbox(left=Inches(0), top=Inches(0.3),
#                                                      width=slide_width, height=TITLE_HEIGHT)
#                 p = title_box.text_frame.paragraphs[0]
#                 p.text = title
#                 p.font.size = Pt(26)
#                 p.font.bold = True
#                 p.font.color.rgb = TITLE_COLOR
#                 p.alignment = PP_ALIGN.CENTER

#             # Content (Parse bullet points from content string)
#             content_text = slide_info.get("content", "")
#             if content_text:
#                 # Parse bullet points from the content string - CLEAN existing bullets
#                 bullet_points = [line.replace("•", "").replace("▸", "").strip() for line in content_text.split('\n') if line.strip()]

#                 # Dynamic textbox height based on number of bullet points
#                 if len(bullet_points) <= 3:
#                     text_height = slide_height * 0.30
#                 elif len(bullet_points) <= 7:
#                     text_height = slide_height * 0.45
#                 else:
#                     text_height = slide_height * 0.65

#                 text_y = (slide_height - text_height) / 2 if len(bullet_points) <= 3 else TOP_MARGIN + Inches(0.5)

#                 text_box = slide.shapes.add_textbox(text_x, text_y, TEXT_WIDTH, text_height)
#                 tf = text_box.text_frame
#                 tf.word_wrap = True
#                 tf.vertical_anchor = MSO_ANCHOR.MIDDLE if len(bullet_points) <= 3 else MSO_ANCHOR.TOP

#                 font_size = 18 if len(bullet_points) <= 5 else 14 if len(bullet_points) <= 10 else 12
#                 for point in bullet_points:
#                     p = tf.add_paragraph()
#                     # Add single bullet only
#                     p.text = f"• {point}"
#                     p.font.size = Pt(font_size)
#                     p.font.color.rgb = BODY_COLOR
#                     p.font.name = USER_FONT_CHOICE

#             # Images with border (using "images" array from JSON)
#             images_data = slide_info.get("images", []) or slide_info.get("suggested_images", [])
#             img_paths = []
#             for img_info in images_data[:2]:  # Max 2 images per slide
#                 img_path = img_info.get("image_path", "")
#                 if img_path and os.path.exists(img_path):
#                     img_paths.append(img_path)
                
#             if img_paths:
#                 total_height = MAX_IMAGE_HEIGHT * len(img_paths) + IMAGE_MARGIN * (len(img_paths) - 1)
#                 current_top = (slide_height - total_height) / 2
#                 for img_path in img_paths:
#                     try:
#                         with Image.open(img_path) as im:
#                             w, h = im.size
#                             aspect = w / h
#                             width = MAX_IMAGE_WIDTH
#                             height = width / aspect
#                             if height > MAX_IMAGE_HEIGHT:
#                                 height = MAX_IMAGE_HEIGHT
#                                 width = height * aspect
#                         rounded_path = create_rounded_image(img_path)
#                         picture = slide.shapes.add_picture(rounded_path, image_x, current_top, width=width, height=height)

#                         # Add border rectangle around image only
#                         border = slide.shapes.add_shape(
#                             1,  # MSO_SHAPE.RECTANGLE
#                             image_x - Inches(0.05),
#                             current_top - Inches(0.05),
#                             width + Inches(0.1),
#                             height + Inches(0.1)
#                         )
#                         border.fill.background()
#                         border.line.color.rgb = IMAGE_BORDER_COLOR
#                         border.line.width = Pt(3)
#                         # Move border behind image
#                         slide.shapes._spTree.remove(border._element)
#                         slide.shapes._spTree.insert(0, border._element)

#                         os.remove(rounded_path)
#                         current_top += height + IMAGE_MARGIN
#                     except Exception as e:
#                         print(f"❌ Error adding image {img_path}: {e}")

#     prs.save(output_path)
#     print(f"✅ Final presentation saved: {output_path}")




from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from PIL import Image, ImageDraw
import json, os, tempfile

def generate_presentation_with_custom_template(json_path: str, template_path: str, output_path: str):
    """
    Generate presentation using custom template with dynamic layout
    - If images present: Image + Text layout  
    - If no images: Centered text only layout
    """
    print(f"🎨 Generating presentation with custom template: {template_path}")
    
    # Load the template
    prs = Presentation(template_path)
    slide_width = prs.slide_width
    slide_height = prs.slide_height

    # Remove all existing slides
    for i in range(len(prs.slides) - 1, -1, -1):
        rId = prs.slides._sldIdLst[i].rId
        prs.part.drop_rel(rId)
        del prs.slides._sldIdLst[i]

    # Choose Title + Content layout
    title_content_layout = None
    for layout in prs.slide_layouts:
        if "title" in (layout.name or "").lower() and "content" in (layout.name or "").lower():
            title_content_layout = layout
            break
    if not title_content_layout:
        title_content_layout = prs.slide_layouts[0]

    # Load slides data from JSON
    with open(json_path, "r", encoding="utf-8") as f:
        slides_data = json.load(f).get("slides", [])

    def create_rounded_image(image_path, radius=40):
        with Image.open(image_path).convert("RGBA") as im:
            mask = Image.new("L", im.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle((0, 0, *im.size), radius=radius, fill=255)
            im.putalpha(mask)
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            im.save(tmp.name, format="PNG")
        return tmp.name

    # Layout constants
    LEFT_MARGIN = Inches(0.8)
    RIGHT_MARGIN = Inches(0.8)
    TOP_MARGIN = Inches(1.0)
    IMAGE_GAP = Inches(0.4)
    TEXT_GAP_DEFAULT = Inches(0.8)
    TEXT_GAP_REDUCED = Inches(0.4)
    IMAGE_BORDER_COLOR = RGBColor(0, 0, 0)

    # Image size
    MAX_IMAGE_WIDTH = slide_width * 0.38
    MAX_IMAGE_HEIGHT = slide_height * 0.32

    # Default settings (no user input)
    USER_FONT_CHOICE = "Calibri"
    TITLE_COLOR = RGBColor(0, 51, 102)
    BODY_COLOR = RGBColor(40, 40, 40)

    # ======================== SLIDES ============================
    for idx, slide_info in enumerate(slides_data):
        slide = prs.slides.add_slide(title_content_layout)

        # Clear placeholders
        for shape in list(slide.shapes):
            if shape.has_text_frame or getattr(shape, 'is_placeholder', False):
                try:
                    sp = shape._element
                    sp.getparent().remove(sp)
                except:
                    pass

        # Title slide (first slide treated as big title)
        if idx == 0:
            title = slide_info.get("slide_title", "")
            if title:
                title_box = slide.shapes.add_textbox(
                    Inches(1.0), Inches(0),
                    slide_width - Inches(2.0), slide_height
                )
                tf = title_box.text_frame
                tf.text = title
                tf.word_wrap = True
                tf.vertical_anchor = MSO_ANCHOR.MIDDLE
                p = tf.paragraphs[0]
                p.font.name = USER_FONT_CHOICE
                p.font.size = Pt(44)
                p.font.bold = True
                p.font.color.rgb = TITLE_COLOR
                p.alignment = PP_ALIGN.CENTER
            continue

        # Check and populate img_paths with actual files
        images_data = slide_info.get("images", []) or slide_info.get("suggested_images", [])
        img_paths = []

        for img_info in images_data:
            raw_path = ""
            if isinstance(img_info, dict):
                raw_path = img_info.get("image_path", "").replace("./", "")
            elif isinstance(img_info, str):
                raw_path = img_info.replace("./", "")
            else:
                continue

            candidate_path = os.path.join(os.path.dirname(json_path), os.path.basename(raw_path))
            # ONLY add if it's an actual file, not a directory
            if os.path.isfile(candidate_path):
                img_paths.append(candidate_path)
            elif os.path.isfile(raw_path):
                img_paths.append(raw_path)

        # Title for regular slides
        title = slide_info.get("slide_title", "")
        if title:
            title_box = slide.shapes.add_textbox(LEFT_MARGIN, Inches(0.4),
                                                 slide_width - RIGHT_MARGIN * 2, Inches(1))
            p = title_box.text_frame.paragraphs[0]
            p.text = title
            p.font.name = USER_FONT_CHOICE
            p.font.size = Pt(28)
            p.font.bold = True
            p.font.color.rgb = TITLE_COLOR
            p.alignment = PP_ALIGN.CENTER

        # ---- CONTENT AND IMAGE HANDLING BASED ON IMAGE PRESENCE ----
        content_text = slide_info.get("content", "")
        content = []
        if content_text:
            if isinstance(content_text, str):
                # Clean content - remove existing bullets first
                content = [line.replace("•", "").replace("▸", "").strip() for line in content_text.split("\n") if line.strip()]
            else:
                content = content_text

        images_available = len(img_paths) > 0

        if images_available:
            # ============ IMAGES PRESENT: KEEP ORIGINAL IMAGE+TEXT LAYOUT ============
            print(f"   📷 Slide {idx+1}: Images + Text layout ({len(img_paths)} images)")

            is_image_left = (idx % 2 == 0)
            text_gap = TEXT_GAP_REDUCED if is_image_left else TEXT_GAP_DEFAULT
            image_x = LEFT_MARGIN if is_image_left else slide_width - MAX_IMAGE_WIDTH - RIGHT_MARGIN
            text_x = image_x + MAX_IMAGE_WIDTH + text_gap if is_image_left else LEFT_MARGIN

            # Grid configuration for text - 2 columns, rows computed
            num_points = min(len(content), 6)
            cols = 2
            rows = (num_points + cols - 1) // cols  # ceil division

            text_area_width = slide_width - (LEFT_MARGIN + RIGHT_MARGIN + MAX_IMAGE_WIDTH + text_gap)
            textbox_width = (text_area_width - Inches(0.4)) / cols

            available_vert = slide_height - TOP_MARGIN - Inches(1.2)
            per_row_height = max(Inches(0.9), min(Inches(1.6), available_vert / max(rows, 1)))
            textbox_height = per_row_height - Inches(0.2)
            textbox_gap = Inches(0.18)

            for i, line in enumerate(content[:num_points]):
                row = i // cols
                col = i % cols
                current_x = text_x + (col * (textbox_width + textbox_gap))
                start_y = (slide_height - (textbox_height * rows + textbox_gap * (rows - 1))) / 2
                current_y = start_y + row * (textbox_height + textbox_gap)

                base_font = 13 if num_points <= 4 else 12
                if len(line) > 140:
                    font_size = max(10, base_font - 3)
                elif len(line) > 90:
                    font_size = max(11, base_font - 2)
                elif len(line) > 60:
                    font_size = max(12, base_font - 1)
                else:
                    font_size = base_font

                # Create textbox with single bullet
                textbox = slide.shapes.add_shape(
                    MSO_SHAPE.ROUNDED_RECTANGLE,
                    current_x, current_y, textbox_width, textbox_height
                )
                try:
                    textbox.adjustments[0] = 0.05
                except Exception:
                    pass

                textbox.fill.solid()
                textbox.fill.fore_color.rgb = RGBColor(255, 255, 255)
                textbox.line.color.rgb = RGBColor(0, 0, 0)
                textbox.line.width = Pt(1.2)

                tf = textbox.text_frame
                tf.clear()
                p = tf.paragraphs[0]
                # Add single bullet only
                p.text = f"• {line}"
                tf.word_wrap = True
                tf.vertical_anchor = MSO_ANCHOR.TOP
                tf.margin_left = Inches(0.12)
                tf.margin_right = Inches(0.12)
                tf.margin_top = Inches(0.08)
                tf.margin_bottom = Inches(0.08)

                p.font.name = USER_FONT_CHOICE
                p.font.size = Pt(font_size)
                p.font.color.rgb = BODY_COLOR
                p.alignment = PP_ALIGN.LEFT

            # ---- Add image with sharp black border (only if images available) ----
            image_heights = []
            computed_total_img_height = 0
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
                        computed_total_img_height += height
                except Exception as e:
                    print(f"Error processing image {img_path}: {e}")
                    image_heights.append((MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT))
                    computed_total_img_height += MAX_IMAGE_HEIGHT

            computed_total_img_height += IMAGE_GAP * (len(img_paths) - 1)

            max_available_height = slide_height - TOP_MARGIN - Inches(1.0)
            if computed_total_img_height > max_available_height:
                scale = max_available_height / computed_total_img_height
                image_heights = [(w * scale, h * scale) for (w, h) in image_heights]
                computed_total_img_height = max_available_height

            current_top = (slide_height - computed_total_img_height) / 2

            for (img_path, (width, height)) in zip(img_paths, image_heights):
                try:
                    rounded_path = create_rounded_image(img_path)

                    border_pad = Inches(0.08)
                    border_shape = slide.shapes.add_shape(
                        MSO_SHAPE.RECTANGLE,
                        image_x - border_pad,
                        current_top - border_pad,
                        width + border_pad * 2,
                        height + border_pad * 2
                    )
                    border_shape.fill.background()
                    border_shape.line.color.rgb = IMAGE_BORDER_COLOR
                    border_shape.line.width = Pt(2)

                    pic = slide.shapes.add_picture(rounded_path, image_x, current_top, width=width, height=height)
                    if rounded_path != img_path:
                        try:
                            os.remove(rounded_path)
                        except:
                            pass

                    current_top += height + IMAGE_GAP
                except Exception as e:
                    print(f"Error adding image {img_path}: {e}")

        else:
            # ============ NO IMAGES: CENTERED TEXT LAYOUT ============
            print(f"   📝 Slide {idx+1}: Text-only layout (centered)")

            num_points = min(len(content), 6)
            if num_points == 0:
                content = [""]  # empty fallback
                num_points = 1

            # Center the text content
            centered_text_width = slide_width * 0.70  # 70% width for centered text
            centered_text_x = (slide_width - centered_text_width) / 2

            # Dynamic textbox height based on number of bullet points
            if len(content) <= 3:
                text_height = slide_height * 0.40
            elif len(content) <= 7:
                text_height = slide_height * 0.55
            else:
                text_height = slide_height * 0.70

            text_y = (slide_height - text_height) / 2  # Always center vertically

            text_box = slide.shapes.add_textbox(centered_text_x, text_y, centered_text_width, text_height)
            tf = text_box.text_frame
            tf.word_wrap = True
            tf.vertical_anchor = MSO_ANCHOR.MIDDLE  # Center vertically

            # Slightly larger font for text-only slides
            font_size = 20 if len(content) <= 5 else 16 if len(content) <= 10 else 14
            
            for point in content:
                p = tf.add_paragraph()
                # Add single bullet only
                p.text = f"• {point}"
                p.font.size = Pt(font_size)
                p.font.color.rgb = BODY_COLOR
                p.font.name = USER_FONT_CHOICE
                p.alignment = PP_ALIGN.CENTER  # Center align text
                p.space_after = Pt(8)  # Add spacing between bullets

    prs.save(output_path)
    print(f"✅ Final presentation saved with dynamic layout: {output_path}")