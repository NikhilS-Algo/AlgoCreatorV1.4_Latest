# from pptx import Presentation
# from pptx.util import Inches, Pt
# from pptx.dml.color import RGBColor
# from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
# from pptx.oxml import parse_xml
# from pptx.enum.shapes import MSO_SHAPE
# from PIL import Image
# import json
# import os
# import tempfile

# class JSONAdapter:
#     @staticmethod
#     def adapt_json_for_ppt(input_json_path, output_json_path):
#         """Adapt the image retrieval JSON structure to match PPT generator expectations"""
#         with open(input_json_path, 'r', encoding='utf-8') as f:
#             data = json.load(f)
        
#         # Transform the structure
#         adapted_data = {
#             "presentation_title": data.get("presentation_title", "AI Presentation"),
#             "slides": []
#         }
        
#         for slide in data.get("slides", []):
#             # Convert content to list format expected by PPT generator
#             content_list = []
#             if slide.get("content"):
#                 content_text = slide["content"]
#                 if isinstance(content_text, str):
#                     # Split content by sentences or newlines for bullet points
#                     sentences = [s.strip() for s in content_text.split('\n') if s.strip()]
#                     content_list = sentences[:6]  # Limit to 6 bullet points
#                 else:
#                     content_list = content_text
            
#             # Adapt images structure
#             suggested_images = []
#             for img in slide.get("images", []):
#                 suggested_images.append({
#                     "image_path": img.get("image_path", ""),
#                     "caption": img.get("caption", "Image"),
#                     "similarity_score": img.get("similarity_score", 0)
#                 })
            
#             adapted_slide = {
#                 "slide_number": slide.get("slide_number", len(adapted_data["slides"]) + 1),
#                 "slide_title": slide.get("slide_title", "Untitled Slide"),
#                 "content": content_list,
#                 "suggested_images": suggested_images
#             }
            
#             adapted_data["slides"].append(adapted_slide)
        
#         # Save adapted JSON
#         with open(output_json_path, 'w', encoding='utf-8') as f:
#             json.dump(adapted_data, f, indent=2)
        
#         print(f"✅ JSON adapted successfully for template3!")
#         return adapted_data

# class ProfessionalBluePresentationGenerator:
#     def __init__(self, json_file_path):
#         self.json_file_path = json_file_path
#         self.presentation_data = self.load_json_data()
#         self.prs = None
        
#     def load_json_data(self):
#         """Load JSON data"""
#         with open(self.json_file_path, 'r', encoding='utf-8') as file:
#             return json.load(file)
    
#     def create_presentation(self, output_path):
#         """Main method - creates presentation with the creative layout"""
#         self.prs = Presentation()
#         self.slide_width = Inches(13.33)
#         self.slide_height = Inches(7.5)
#         self.prs.slide_width = self.slide_width
#         self.prs.slide_height = self.slide_height
        
#         print("🎨 Creating Creative Professional Presentation")
        
#         # Analyze content first
#         has_images = self.analyze_content()
        
#         # Create template based on content analysis
#         template_path, template_type = self.create_dynamic_template(has_images)
        
#         # Populate presentation
#         self.populate_presentation(template_path, output_path, template_type)
        
#         print(f"✅ Creative Professional Presentation created!")
    
#     def analyze_content(self):
#         """Analyze if presentation has images"""
#         has_images = False
#         for slide_data in self.presentation_data["slides"]:
#             available_images = self.get_available_images(slide_data)
#             if available_images:
#                 has_images = True
#                 break
#         return has_images
    
#     def get_available_images(self, slide_data):
#         """Get list of available images that actually exist"""
#         available = []
#         for img in slide_data.get("suggested_images", []):
#             img_path = img.get("image_path", "")
#             if img_path and os.path.exists(img_path):
#                 available.append(img)
#         return available
    
#     def create_dynamic_template(self, has_images=True):
#         """Create dynamic template with curved design"""
#         output_path = "temp_template.pptx"
        
#         slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        
#         # Base background - light gray
#         background = slide.background
#         fill = background.fill
#         fill.solid()
#         fill.fore_color.rgb = RGBColor(240, 240, 240)

#         if has_images:
#             path_xml = f"""
#             <p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
#                   xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
#               <p:nvSpPr>
#                 <p:cNvPr id="5" name="RightCornerCurveDarkGray"/>
#                 <p:cNvSpPr/>
#                 <p:nvPr/>
#               </p:nvSpPr>
#               <p:spPr>
#                 <a:xfrm><a:off x="0" y="0"/><a:ext cx="{self.slide_width}" cy="{self.slide_height}"/></a:xfrm>
#                 <a:custGeom>
#                   <a:avLst/>
#                   <a:pathLst>
#                     <a:path w="{self.slide_width}" h="{self.slide_height}">
#                       <a:moveTo><a:pt x="{int(self.slide_width * 0.85)}" y="0"/></a:moveTo>
#                       <a:cubicBezTo>
#                         <a:pt x="{int(self.slide_width * 0.9)}" y="{int(self.slide_height * 0.3)}"/>
#                         <a:pt x="{int(self.slide_width * 0.95)}" y="{int(self.slide_height * 0.6)}"/>
#                         <a:pt x="{int(self.slide_width * 0.85)}" y="{self.slide_height}"/>
#                       </a:cubicBezTo>
#                       <a:lnTo><a:pt x="{self.slide_width}" y="{self.slide_height}"/></a:lnTo>
#                       <a:lnTo><a:pt x="{self.slide_width}" y="0"/></a:lnTo>
#                       <a:close/>
#                     </a:path>
#                   </a:pathLst>
#                 </a:custGeom>
#                 <a:gradFill rotWithShape="1">
#                   <a:gsLst>
#                     <a:gs pos="0"><a:srgbClr val="444444"/></a:gs>
#                     <a:gs pos="100000"><a:srgbClr val="1C1C1C"/></a:gs>
#                   </a:gsLst>
#                   <a:lin ang="2700000" scaled="1"/>
#                 </a:gradFill>
#                 <a:ln w="0"><a:noFill/></a:ln>
#               </p:spPr>
#             </p:sp>
#             """
#             slide.shapes._spTree.insert_element_before(parse_xml(path_xml), 'p:extLst')
#             template_type = "with_images"
#         else:
#             path_xml = f"""
#             <p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
#                   xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
#               <p:nvSpPr>
#                 <p:cNvPr id="5" name="FullWidthBackground"/>
#                 <p:cNvSpPr/>
#                 <p:nvPr/>
#               </p:nvSpPr>
#               <p:spPr>
#                 <a:xfrm><a:off x="0" y="0"/><a:ext cx="{self.slide_width}" cy="{self.slide_height}"/></a:xfrm>
#                 <a:rect/>
#                 <a:solidFill>
#                   <a:srgbClr val="F5F5F5"/>
#                 </a:solidFill>
#                 <a:ln w="0"><a:noFill/></a:ln>
#               </p:spPr>
#             </p:sp>
#             """
#             slide.shapes._spTree.insert_element_before(parse_xml(path_xml), 'p:extLst')
#             template_type = "text_only"

#         self.prs.save(output_path)
#         return output_path, template_type
    
#     def duplicate_slide(self, prs, source_slide):
#         """Duplicate slide"""
#         blank = prs.slide_layouts[6]
#         new_slide = prs.slides.add_slide(blank)
#         for shape in source_slide.shapes:
#             new_shape = parse_xml(shape.element.xml)
#             new_slide.shapes._spTree.insert_element_before(new_shape, 'p:extLst')
#         return new_slide
    
#     def create_textbox_with_rounded_corners(self, slide, x, y, width, height, text, font_size, text_color):
#         """Create rounded corner textbox"""
#         textbox = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, width, height)
#         try:
#             textbox.adjustments[0] = 0.05
#         except Exception:
#             pass
#         textbox.fill.solid()
#         textbox.fill.fore_color.rgb = RGBColor(255, 255, 255)
#         textbox.line.color.rgb = RGBColor(0, 0, 0)
#         textbox.line.width = Pt(1.5)
#         text_frame = textbox.text_frame
#         text_frame.clear()
#         text_frame.word_wrap = True
#         text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
#         text_frame.margin_left = Inches(0.1)
#         text_frame.margin_right = Inches(0.1)
#         text_frame.margin_top = Inches(0.05)
#         text_frame.margin_bottom = Inches(0.05)
        
#         if isinstance(text, str):
#             p = text_frame.paragraphs[0]
#             p.text = text
#             p.font.name = "Calibri"
#             p.font.size = Pt(font_size)
#             p.font.color.rgb = text_color
#             p.alignment = PP_ALIGN.LEFT
#         else:
#             for i, line in enumerate(text):
#                 p = text_frame.add_paragraph() if i > 0 else text_frame.paragraphs[0]
#                 p.text = line
#                 p.font.name = "Calibri"
#                 p.font.size = Pt(font_size)
#                 p.font.color.rgb = text_color
#                 p.alignment = PP_ALIGN.LEFT
#         return textbox
    
#     def populate_presentation(self, template_path, output_pptx, template_type):
#         """Populate presentation with content"""
#         prs = Presentation(template_path)
#         base_slide = prs.slides[0]

#         # Layout constants
#         LEFT_MARGIN = Inches(0.8)
#         RIGHT_MARGIN = Inches(0.8)
#         IMAGE_GAP = Inches(0.4)
#         TEXT_GAP_DEFAULT = Inches(0.8)
#         TEXT_GAP_REDUCED = Inches(0.4)
#         FOOTER_LINE_COLOR = RGBColor(160, 160, 160)
#         IMAGE_BORDER_COLOR = RGBColor(0, 0, 0)

#         MAX_IMAGE_WIDTH = self.slide_width * 0.38
#         MAX_IMAGE_HEIGHT = self.slide_height * 0.32

#         # Default colors (professional blue theme)
#         title_color = RGBColor(0, 0, 0)
#         body_color = RGBColor(0, 0, 0)

#         for idx, slide_data in enumerate(self.presentation_data["slides"]):
#             slide = self.duplicate_slide(prs, base_slide)
#             print(f"🧩 Creating Slide {idx + 1}/{len(self.presentation_data['slides'])}")

#             title = slide_data.get("slide_title", "")
#             content = slide_data.get("content", [])
#             if isinstance(content, str):
#                 content = [line.replace("•", "").strip() for line in content.split("\n") if line.strip()]

#             available_images = self.get_available_images(slide_data)
#             img_paths = [img["image_path"] for img in available_images]

#             # Title-only first slide
#             if idx == 0:
#                 title_box = slide.shapes.add_textbox(
#                     Inches(1.0), Inches(0),
#                     self.slide_width - Inches(2.0), self.slide_height
#                 )
#                 tf = title_box.text_frame
#                 tf.text = self.presentation_data["presentation_title"]
#                 tf.word_wrap = True
#                 tf.vertical_anchor = MSO_ANCHOR.MIDDLE
#                 p = tf.paragraphs[0]
#                 p.font.name = "Calibri"
#                 p.font.size = Pt(44)
#                 p.font.bold = True
#                 p.font.color.rgb = title_color
#                 p.alignment = PP_ALIGN.CENTER
#                 continue

#             # ---- Title ----
#             if title:
#                 title_box = slide.shapes.add_textbox(LEFT_MARGIN, Inches(0.4),
#                                                      self.slide_width - RIGHT_MARGIN * 2, Inches(1))
#                 p = title_box.text_frame.paragraphs[0]
#                 p.text = title
#                 p.font.name = "Calibri"
#                 p.font.size = Pt(28)
#                 p.font.bold = True
#                 p.font.color.rgb = title_color
#                 p.alignment = PP_ALIGN.CENTER

#             # --------- MAIN LAYOUT LOGIC ----------
#             if img_paths:
#                 # IMAGES PRESENT: image+text layout
#                 print(f"   📷 Images found: {len(img_paths)} - Using image layout")
#                 image_on_left = (idx % 2 == 0)
#                 text_gap = TEXT_GAP_REDUCED if image_on_left else TEXT_GAP_DEFAULT
#                 image_x = LEFT_MARGIN if image_on_left else self.slide_width - MAX_IMAGE_WIDTH - RIGHT_MARGIN
#                 text_x = image_x + MAX_IMAGE_WIDTH + text_gap if image_on_left else LEFT_MARGIN

#                 # Create 2x2 grid textboxes
#                 if content:
#                     num_points = min(len(content), 6)
#                     cols = 2
#                     rows = (num_points + 1) // 2
#                     textbox_width = (self.slide_width - (MAX_IMAGE_WIDTH + text_gap + LEFT_MARGIN + RIGHT_MARGIN + Inches(0.4))) / cols
#                     textbox_height = Inches(1.3)
#                     textbox_gap = Inches(0.2)
#                     font_size = 15 if num_points <= 4 else 13
#                     grid_height = (textbox_height * rows) + (textbox_gap * (rows - 1))
#                     start_x = text_x
#                     start_y = (self.slide_height - grid_height) / 2
                    
#                     for i, line in enumerate(content[:6]):
#                         row = i // cols
#                         col = i % cols
#                         current_x = start_x + (col * (textbox_width + textbox_gap))
#                         current_y = start_y + (row * (textbox_height + textbox_gap))
#                         self.create_textbox_with_rounded_corners(
#                             slide=slide,
#                             x=current_x,
#                             y=current_y,
#                             width=textbox_width,
#                             height=textbox_height,
#                             text=f"• {line}",
#                             font_size=font_size,
#                             text_color=body_color
#                         )

#                 # Add images with border
#                 total_images_height = 0
#                 image_dimensions_list = []

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
#                             image_dimensions_list.append((width, height))
#                             total_images_height += height
#                     except Exception as e:
#                         print(f"❌ Error processing image {img_path}: {e}")
#                         image_dimensions_list.append((MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT))
#                         total_images_height += MAX_IMAGE_HEIGHT

#                 total_images_height += IMAGE_GAP * (len(img_paths) - 1)
#                 current_top = (self.slide_height - total_images_height) / 2

#                 for i, img_path in enumerate(img_paths):
#                     try:
#                         width, height = image_dimensions_list[i]
#                         border_pad = Inches(0.1)
#                         border_shape = slide.shapes.add_shape(
#                             MSO_SHAPE.RECTANGLE,
#                             image_x - border_pad,
#                             current_top - border_pad,
#                             width + border_pad * 2,
#                             height + border_pad * 2
#                         )
#                         border_shape.fill.background()
#                         border_shape.line.color.rgb = IMAGE_BORDER_COLOR
#                         border_shape.line.width = Pt(2)
#                         slide.shapes.add_picture(img_path, image_x, current_top, width=width, height=height)
#                         current_top += height + IMAGE_GAP
#                     except Exception as e:
#                         print(f"❌ Error adding image {img_path}: {e}")

#             else:
#                 # NO IMAGES: Centered text layout
#                 print("   ⚠️ No images found - Centering all textboxes")
#                 num_points = len(content) or 1
#                 textbox_width = self.slide_width * 0.60
#                 textbox_height = Inches(1.0)
#                 textbox_gap = Inches(0.20)
#                 total_height = num_points * textbox_height + (num_points - 1) * textbox_gap
#                 start_y = (self.slide_height - total_height) / 2
#                 center_x = (self.slide_width - textbox_width) / 2

#                 for i, line in enumerate(content):
#                     current_y = start_y + i * (textbox_height + textbox_gap)
#                     self.create_textbox_with_rounded_corners(
#                         slide=slide,
#                         x=center_x,
#                         y=current_y,
#                         width=textbox_width,
#                         height=textbox_height,
#                         text=f"• {line}",
#                         font_size=15,
#                         text_color=body_color
#                     )

#             # ---- Footer Line ----
#             footer_line = slide.shapes.add_shape(
#                 MSO_SHAPE.RECTANGLE,
#                 Inches(0.0),
#                 self.slide_height - Inches(0.3),
#                 self.slide_width,
#                 Inches(0.05)
#             )
#             fill = footer_line.fill
#             fill.solid()
#             fill.fore_color.rgb = FOOTER_LINE_COLOR
#             footer_line.line.fill.background()

#         # Remove first template slide
#         xml_slides = prs.slides._sldIdLst
#         if len(xml_slides) > 0:
#             xml_slides.remove(xml_slides[0])
#         prs.save(output_pptx)
        
#         # Cleanup temp template
#         if os.path.exists(template_path):
#             os.remove(template_path)




from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml import parse_xml
from pptx.enum.shapes import MSO_SHAPE
from PIL import Image
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
        
        print(f"✅ JSON adapted successfully for template3!")
        return adapted_data

class ProfessionalBluePresentationGenerator:
    def __init__(self, json_file_path):
        self.json_file_path = json_file_path
        self.presentation_data = self.load_json_data()
        self.prs = None
        
    def load_json_data(self):
        """Load JSON data"""
        with open(self.json_file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    
    def create_presentation(self, output_path):
        """Main method - creates presentation with the creative layout"""
        self.prs = Presentation()
        self.slide_width = Inches(13.33)
        self.slide_height = Inches(7.5)
        self.prs.slide_width = self.slide_width
        self.prs.slide_height = self.slide_height
        
        print("🎨 Creating Creative Professional Presentation")
        
        # Analyze content first
        has_images = self.analyze_content()
        
        # Create template based on content analysis
        template_path, template_type = self.create_dynamic_template(has_images)
        
        # Populate presentation
        self.populate_presentation(template_path, output_path, template_type)
        
        print(f"✅ Creative Professional Presentation created!")
    
    def analyze_content(self):
        """Analyze if presentation has images"""
        has_images = False
        for slide_data in self.presentation_data["slides"]:
            available_images = self.get_available_images(slide_data)
            if available_images:
                has_images = True
                break
        return has_images
    
    def get_available_images(self, slide_data):
        """Get list of available images that actually exist"""
        available = []
        for img in slide_data.get("suggested_images", []):
            img_path = img.get("image_path", "")
            if img_path and os.path.exists(img_path):
                available.append(img)
        return available
    
    def create_dynamic_template(self, has_images=True):
        """Create dynamic template with curved design"""
        output_path = "temp_template.pptx"
        
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        
        # Base background - light gray
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(240, 240, 240)

        if has_images:
            path_xml = f"""
            <p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
                  xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
              <p:nvSpPr>
                <p:cNvPr id="5" name="RightCornerCurveDarkGray"/>
                <p:cNvSpPr/>
                <p:nvPr/>
              </p:nvSpPr>
              <p:spPr>
                <a:xfrm><a:off x="0" y="0"/><a:ext cx="{self.slide_width}" cy="{self.slide_height}"/></a:xfrm>
                <a:custGeom>
                  <a:avLst/>
                  <a:pathLst>
                    <a:path w="{self.slide_width}" h="{self.slide_height}">
                      <a:moveTo><a:pt x="{int(self.slide_width * 0.85)}" y="0"/></a:moveTo>
                      <a:cubicBezTo>
                        <a:pt x="{int(self.slide_width * 0.9)}" y="{int(self.slide_height * 0.3)}"/>
                        <a:pt x="{int(self.slide_width * 0.95)}" y="{int(self.slide_height * 0.6)}"/>
                        <a:pt x="{int(self.slide_width * 0.85)}" y="{self.slide_height}"/>
                      </a:cubicBezTo>
                      <a:lnTo><a:pt x="{self.slide_width}" y="{self.slide_height}"/></a:lnTo>
                      <a:lnTo><a:pt x="{self.slide_width}" y="0"/></a:lnTo>
                      <a:close/>
                    </a:path>
                  </a:pathLst>
                </a:custGeom>
                <a:gradFill rotWithShape="1">
                  <a:gsLst>
                    <a:gs pos="0"><a:srgbClr val="444444"/></a:gs>
                    <a:gs pos="100000"><a:srgbClr val="1C1C1C"/></a:gs>
                  </a:gsLst>
                  <a:lin ang="2700000" scaled="1"/>
                </a:gradFill>
                <a:ln w="0"><a:noFill/></a:ln>
              </p:spPr>
            </p:sp>
            """
            slide.shapes._spTree.insert_element_before(parse_xml(path_xml), 'p:extLst')
            template_type = "with_images"
        else:
            path_xml = f"""
            <p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
                  xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
              <p:nvSpPr>
                <p:cNvPr id="5" name="FullWidthBackground"/>
                <p:cNvSpPr/>
                <p:nvPr/>
              </p:nvSpPr>
              <p:spPr>
                <a:xfrm><a:off x="0" y="0"/><a:ext cx="{self.slide_width}" cy="{self.slide_height}"/></a:xfrm>
                <a:rect/>
                <a:solidFill>
                  <a:srgbClr val="F5F5F5"/>
                </a:solidFill>
                <a:ln w="0"><a:noFill/></a:ln>
              </p:spPr>
            </p:sp>
            """
            slide.shapes._spTree.insert_element_before(parse_xml(path_xml), 'p:extLst')
            template_type = "text_only"

        self.prs.save(output_path)
        return output_path, template_type
    
    def duplicate_slide(self, prs, source_slide):
        """Duplicate slide"""
        blank = prs.slide_layouts[6]
        new_slide = prs.slides.add_slide(blank)
        for shape in source_slide.shapes:
            new_shape = parse_xml(shape.element.xml)
            new_slide.shapes._spTree.insert_element_before(new_shape, 'p:extLst')
        return new_slide
    
    def create_textbox_with_rounded_corners(self, slide, x, y, width, height, text, font_size, text_color):
        """Create rounded corner textbox - FIXED: No bullet processing"""
        textbox = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, width, height)
        try:
            textbox.adjustments[0] = 0.05
        except Exception:
            pass
        textbox.fill.solid()
        textbox.fill.fore_color.rgb = RGBColor(255, 255, 255)
        textbox.line.color.rgb = RGBColor(0, 0, 0)
        textbox.line.width = Pt(1.5)
        text_frame = textbox.text_frame
        text_frame.clear()
        text_frame.word_wrap = True
        text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        text_frame.margin_left = Inches(0.1)
        text_frame.margin_right = Inches(0.1)
        text_frame.margin_top = Inches(0.05)
        text_frame.margin_bottom = Inches(0.05)
        
        # FIXED: Just set the text directly without any processing
        p = text_frame.paragraphs[0]
        p.text = text
        p.font.name = "Calibri"
        p.font.size = Pt(font_size)
        p.font.color.rgb = text_color
        p.alignment = PP_ALIGN.LEFT
        
        return textbox
    
    def populate_presentation(self, template_path, output_pptx, template_type):
        """Populate presentation with content"""
        prs = Presentation(template_path)
        base_slide = prs.slides[0]

        # Layout constants
        LEFT_MARGIN = Inches(0.8)
        RIGHT_MARGIN = Inches(0.8)
        IMAGE_GAP = Inches(0.4)
        TEXT_GAP_DEFAULT = Inches(0.8)
        TEXT_GAP_REDUCED = Inches(0.4)
        FOOTER_LINE_COLOR = RGBColor(160, 160, 160)
        IMAGE_BORDER_COLOR = RGBColor(0, 0, 0)

        MAX_IMAGE_WIDTH = self.slide_width * 0.38
        MAX_IMAGE_HEIGHT = self.slide_height * 0.32

        # Default colors (professional blue theme)
        title_color = RGBColor(0, 0, 0)
        body_color = RGBColor(0, 0, 0)

        for idx, slide_data in enumerate(self.presentation_data["slides"]):
            slide = self.duplicate_slide(prs, base_slide)
            print(f"🧩 Creating Slide {idx + 1}/{len(self.presentation_data['slides'])}")

            title = slide_data.get("slide_title", "")
            content = slide_data.get("content", [])
            if isinstance(content, str):
                # Clean content - remove existing bullets and split
                content = [line.replace("•", "").replace("▸", "").strip() for line in content.split("\n") if line.strip()]

            available_images = self.get_available_images(slide_data)
            img_paths = [img["image_path"] for img in available_images]

            # Title-only first slide
            if idx == 0:
                title_box = slide.shapes.add_textbox(
                    Inches(1.0), Inches(0),
                    self.slide_width - Inches(2.0), self.slide_height
                )
                tf = title_box.text_frame
                tf.text = self.presentation_data["presentation_title"]
                tf.word_wrap = True
                tf.vertical_anchor = MSO_ANCHOR.MIDDLE
                p = tf.paragraphs[0]
                p.font.name = "Calibri"
                p.font.size = Pt(44)
                p.font.bold = True
                p.font.color.rgb = title_color
                p.alignment = PP_ALIGN.CENTER
                continue

            # ---- Title ----
            if title:
                title_box = slide.shapes.add_textbox(LEFT_MARGIN, Inches(0.4),
                                                     self.slide_width - RIGHT_MARGIN * 2, Inches(1))
                p = title_box.text_frame.paragraphs[0]
                p.text = title
                p.font.name = "Calibri"
                p.font.size = Pt(28)
                p.font.bold = True
                p.font.color.rgb = title_color
                p.alignment = PP_ALIGN.CENTER

            # --------- MAIN LAYOUT LOGIC ----------
            if img_paths:
                # IMAGES PRESENT: image+text layout
                print(f"   📷 Images found: {len(img_paths)} - Using image layout")
                image_on_left = (idx % 2 == 0)
                text_gap = TEXT_GAP_REDUCED if image_on_left else TEXT_GAP_DEFAULT
                image_x = LEFT_MARGIN if image_on_left else self.slide_width - MAX_IMAGE_WIDTH - RIGHT_MARGIN
                text_x = image_x + MAX_IMAGE_WIDTH + text_gap if image_on_left else LEFT_MARGIN

                # Create 2x2 grid textboxes
                if content:
                    num_points = min(len(content), 6)
                    cols = 2
                    rows = (num_points + 1) // 2
                    textbox_width = (self.slide_width - (MAX_IMAGE_WIDTH + text_gap + LEFT_MARGIN + RIGHT_MARGIN + Inches(0.4))) / cols
                    textbox_height = Inches(1.3)
                    textbox_gap = Inches(0.2)
                    font_size = 15 if num_points <= 4 else 13
                    grid_height = (textbox_height * rows) + (textbox_gap * (rows - 1))
                    start_x = text_x
                    start_y = (self.slide_height - grid_height) / 2
                    
                    for i, line in enumerate(content[:6]):
                        row = i // cols
                        col = i % cols
                        current_x = start_x + (col * (textbox_width + textbox_gap))
                        current_y = start_y + (row * (textbox_height + textbox_gap))
                        # Clean the content and add single bullet
                        clean_line = str(line).replace('•', '').replace('▸', '').strip()
                        final_text = f"• {clean_line}"  # Single bullet only
                        self.create_textbox_with_rounded_corners(
                            slide=slide,
                            x=current_x,
                            y=current_y,
                            width=textbox_width,
                            height=textbox_height,
                            text=final_text,  # Pass the cleaned text with single bullet
                            font_size=font_size,
                            text_color=body_color
                        )

                # Add images with border
                total_images_height = 0
                image_dimensions_list = []

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
                            image_dimensions_list.append((width, height))
                            total_images_height += height
                    except Exception as e:
                        print(f"❌ Error processing image {img_path}: {e}")
                        image_dimensions_list.append((MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT))
                        total_images_height += MAX_IMAGE_HEIGHT

                total_images_height += IMAGE_GAP * (len(img_paths) - 1)
                current_top = (self.slide_height - total_images_height) / 2

                for i, img_path in enumerate(img_paths):
                    try:
                        width, height = image_dimensions_list[i]
                        border_pad = Inches(0.1)
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
                        slide.shapes.add_picture(img_path, image_x, current_top, width=width, height=height)
                        current_top += height + IMAGE_GAP
                    except Exception as e:
                        print(f"❌ Error adding image {img_path}: {e}")

            else:
                # NO IMAGES: Centered text layout
                print("   ⚠️ No images found - Centering all textboxes")
                num_points = len(content) or 1
                textbox_width = self.slide_width * 0.60
                textbox_height = Inches(1.0)
                textbox_gap = Inches(0.20)
                total_height = num_points * textbox_height + (num_points - 1) * textbox_gap
                start_y = (self.slide_height - total_height) / 2
                center_x = (self.slide_width - textbox_width) / 2

                for i, line in enumerate(content):
                    current_y = start_y + i * (textbox_height + textbox_gap)
                    # Clean the content and add single bullet
                    clean_line = str(line).replace('•', '').replace('▸', '').strip()
                    final_text = f"• {clean_line}"  # Single bullet only
                    self.create_textbox_with_rounded_corners(
                        slide=slide,
                        x=center_x,
                        y=current_y,
                        width=textbox_width,
                        height=textbox_height,
                        text=final_text,  # Pass the cleaned text with single bullet
                        font_size=15,
                        text_color=body_color
                    )

            # ---- Footer Line ----
            footer_line = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE,
                Inches(0.0),
                self.slide_height - Inches(0.3),
                self.slide_width,
                Inches(0.05)
            )
            fill = footer_line.fill
            fill.solid()
            fill.fore_color.rgb = FOOTER_LINE_COLOR
            footer_line.line.fill.background()

        # Remove first template slide
        xml_slides = prs.slides._sldIdLst
        if len(xml_slides) > 0:
            xml_slides.remove(xml_slides[0])
        prs.save(output_pptx)
        
        # Cleanup temp template
        if os.path.exists(template_path):
            os.remove(template_path)