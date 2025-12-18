from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
import json
import os

class JSONAdapter:
    @staticmethod
    def adapt_json_for_ppt(input_json_path, output_json_path):
        """Adapt the image retrieval JSON structure to match PPT generator expectations"""
        with open(input_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Transform the structure
        adapted_data = {
            "presentation_title": data.get("presentation_title", "AI Surveillance Presentation"),
            "slides": []
        }
        
        for slide in data.get("slides", []):
            # Convert content to list format expected by PPT generator
            content_list = []
            if slide.get("content"):
                # Split content by bullet points (•)
                content_text = slide["content"]
                # Split by bullet points and clean up
                bullet_points = [point.strip() for point in content_text.split('•') if point.strip()]
                content_list = bullet_points[:6]  # Limit to 6 bullet points
            
            # Adapt images structure - use the "images" array from your JSON
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
                "suggested_images": suggested_images  # This is what the PPT generator expects
            }
            
            adapted_data["slides"].append(adapted_slide)
        
        # Save adapted JSON
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(adapted_data, f, indent=2)
        
        print(f"✅ JSON adapted successfully!")
        print(f"📊 Original slides: {len(data.get('slides', []))}")
        print(f"📊 Adapted slides: {len(adapted_data['slides'])}")
        
        return adapted_data

class SplitDiagonalPresentationGenerator:
    def __init__(self, json_file_path):
        self.json_file_path = json_file_path
        self.presentation_data = self.load_json_data()
        self.prs = None
        
        # Black theme colors
        self.colors = {
            'background': RGBColor(18, 18, 18),
            'card_bg': RGBColor(30, 30, 30),
            'primary': RGBColor(0, 150, 255),
            'accent': RGBColor(255, 87, 34),
            'success': RGBColor(76, 175, 80),
            'text_primary': RGBColor(255, 255, 255),
            'text_secondary': RGBColor(180, 180, 180),
            'border': RGBColor(60, 60, 60),
            'image_border': RGBColor(0, 120, 215)
        }
        
    def load_json_data(self):
        """Load JSON data"""
        with open(self.json_file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    
    def create_presentation(self, output_path):
        """Main method - creates presentation with alternating split diagonal layout"""
        self.prs = Presentation()
        self.slide_width = Inches(13.33)
        self.slide_height = Inches(7.5)
        self.prs.slide_width = self.slide_width
        self.prs.slide_height = self.slide_height
        
        print("🎨 Creating Alternating Split Diagonal Layout Presentation")
        
        # Create title slide (this is the introduction/first slide)
        self.create_modern_title_slide()
        
        # Create all content slides with ALTERNATING layout (starting from slide 2)
        for slide_data in self.presentation_data["slides"]:
            # Skip the first content slide if it's the introduction
            # We already created the title slide, so start with actual content slides
            if slide_data["slide_number"] == 1:
                continue
                
            # Alternate between image left and image right based on slide number
            # Since we skipped slide 1, we adjust the numbering for alternation
            adjusted_slide_num = slide_data["slide_number"] - 1
            if adjusted_slide_num % 2 == 1:  # Odd slides: Image LEFT, Text RIGHT
                self.create_split_diagonal_slide(slide_data, image_on_left=True)
                print(f"   Created Slide {slide_data['slide_number']}: {slide_data['slide_title']} (Image LEFT)")
            else:  # Even slides: Image RIGHT, Text LEFT
                self.create_split_diagonal_slide(slide_data, image_on_left=False)
                print(f"   Created Slide {slide_data['slide_number']}: {slide_data['slide_title']} (Image RIGHT)")
        
        self.prs.save(output_path)
        total_slides = 1 + len([s for s in self.presentation_data["slides"] if s["slide_number"] != 1])
        print(f"✅ Presentation created with {total_slides} total slides!")
        print("🔄 Layout: Images alternate sides (LEFT/RIGHT)")
    
    def create_modern_title_slide(self):
        """Modern title slide with geometric elements - This is the introduction/first slide"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        
        # Set black background
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = self.colors['background']
        
        # Add geometric background elements
        self.add_geometric_background(slide)
        
        # Main title
        title_box = slide.shapes.add_textbox(Inches(1.0), Inches(2.0), 
                                           self.slide_width - Inches(2.0), Inches(1.5))
        title_frame = title_box.text_frame
        title_frame.text = self.presentation_data["presentation_title"]
        
        for paragraph in title_frame.paragraphs:
            paragraph.font.size = Pt(44)
            paragraph.font.color.rgb = self.colors['text_primary']
            paragraph.font.bold = True
            paragraph.font.name = "Segoe UI"
            paragraph.alignment = PP_ALIGN.CENTER
        
        # Subtitle with accent
        subtitle_box = slide.shapes.add_textbox(Inches(2.0), Inches(3.8), 
                                              self.slide_width - Inches(4.0), Inches(0.8))
        subtitle_frame = subtitle_box.text_frame
        subtitle_frame.text = "Advanced AI Solutions for Manufacturing Excellence"
        
        for paragraph in subtitle_frame.paragraphs:
            paragraph.font.size = Pt(20)
            paragraph.font.color.rgb = self.colors['primary']
            paragraph.font.name = "Segoe UI"
            paragraph.alignment = PP_ALIGN.CENTER
        
        # Decorative elements
        self.add_title_decoration(slide)
    
    def create_split_diagonal_slide(self, slide_data, image_on_left=True):
        """Split Diagonal Layout - Alternates based on image_on_left parameter"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        
        # Set black background
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = self.colors['background']
        
        # Add subtle background pattern
        self.add_diagonal_background(slide)
        
        # Title - Top Center
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), 
                                           self.slide_width - Inches(1.0), Inches(0.8))
        title_frame = title_box.text_frame
        title_frame.text = slide_data["slide_title"]
        self.style_slide_title(title_frame)
        
        if image_on_left:
            # Image on LEFT, Text on RIGHT
            self.create_image_left_layout(slide, slide_data)
        else:
            # Image on RIGHT, Text on LEFT
            self.create_image_right_layout(slide, slide_data)
        
        self.add_slide_number(slide, slide_data["slide_number"])
    
    def create_image_left_layout(self, slide, slide_data):
        """Layout with Image on LEFT, Text on RIGHT"""
        # LEFT Panel - IMAGE Content
        left_panel = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, 
            Inches(0.5), Inches(1.3), 
            Inches(5.3), Inches(5.2)
        )
        left_panel.fill.solid()
        left_panel.fill.fore_color.rgb = RGBColor(25, 25, 25)
        left_panel.line.fill.background()
        
        # RIGHT Panel - TEXT Content
        right_panel = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, 
            Inches(5.8), Inches(1.3), 
            Inches(7.0), Inches(5.2)
        )
        right_panel.fill.solid()
        right_panel.fill.fore_color.rgb = self.colors['card_bg']
        right_panel.line.color.rgb = self.colors['primary']
        right_panel.line.width = Pt(2)
        
        # Diagonal Accent Bar (on right side of image panel)
        diagonal_bar = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(5.6), Inches(1.3),
            Inches(0.4), Inches(5.2)
        )
        diagonal_bar.fill.solid()
        diagonal_bar.fill.fore_color.rgb = self.colors['primary']
        diagonal_bar.line.fill.background()
        
        # Add Content
        self.add_diagonal_image_content(slide, slide_data, image_on_left=True)
        self.add_diagonal_text_content(slide, slide_data, image_on_left=True)
    
    def create_image_right_layout(self, slide, slide_data):
        """Layout with Image on RIGHT, Text on LEFT"""
        # LEFT Panel - TEXT Content
        left_panel = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, 
            Inches(0.5), Inches(1.3), 
            Inches(7.0), Inches(5.2)
        )
        left_panel.fill.solid()
        left_panel.fill.fore_color.rgb = self.colors['card_bg']
        left_panel.line.color.rgb = self.colors['primary']
        left_panel.line.width = Pt(2)
        
        # RIGHT Panel - IMAGE Content
        right_panel = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, 
            Inches(7.5), Inches(1.3), 
            Inches(5.3), Inches(5.2)
        )
        right_panel.fill.solid()
        right_panel.fill.fore_color.rgb = RGBColor(25, 25, 25)
        right_panel.line.fill.background()
        
        # Diagonal Accent Bar (on left side of image panel)
        diagonal_bar = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(7.3), Inches(1.3),
            Inches(0.4), Inches(5.2)
        )
        diagonal_bar.fill.solid()
        diagonal_bar.fill.fore_color.rgb = self.colors['primary']
        diagonal_bar.line.fill.background()
        
        # Add Content
        self.add_diagonal_text_content(slide, slide_data, image_on_left=False)
        self.add_diagonal_image_content(slide, slide_data, image_on_left=False)
    
    def add_diagonal_text_content(self, slide, slide_data, image_on_left=True):
        """Add text content to panel"""
        if image_on_left:
            # Text on RIGHT
            text_left = Inches(6.3)
            header_left = Inches(6.3)
        else:
            # Text on LEFT
            text_left = Inches(1.0)
            header_left = Inches(1.0)
        
        # Text container with padding
        text_box = slide.shapes.add_textbox(
            text_left, Inches(1.8), 
            Inches(6.0), Inches(4.2)
        )
        text_frame = text_box.text_frame
        text_frame.word_wrap = True
        
        # Add all content points with attractive bullets
        content_items = slide_data.get("content", [])
        if not content_items:
            # Fallback: use key_takeaway if content is empty
            content_items = [slide_data.get("key_takeaway", "No content available")]
        
        for i, content_item in enumerate(content_items):
            if i == 0:
                p = text_frame.paragraphs[0]
            else:
                p = text_frame.add_paragraph()
            
            # Modern bullet points
            p.text = "▸ " + str(content_item)
            p.font.size = Pt(16)
            p.font.color.rgb = self.colors['text_primary']
            p.font.name = "Segoe UI"
            p.space_after = Pt(12)
            p.line_spacing = 1.4
        
        # Add subtle header to text panel
        text_header = slide.shapes.add_textbox(
            header_left, Inches(1.5),
            Inches(6.0), Inches(0.3)
        )
        text_header_frame = text_header.text_frame
        text_header_frame.text = "KEY POINTS"
        text_header_frame.paragraphs[0].font.size = Pt(12)
        text_header_frame.paragraphs[0].font.color.rgb = self.colors['primary']
        text_header_frame.paragraphs[0].font.bold = True
        text_header_frame.paragraphs[0].font.name = "Segoe UI"
    
    def add_diagonal_image_content(self, slide, slide_data, image_on_left=True):
        """Add image content to panel"""
        if image_on_left:
            # Image on LEFT
            container_left = Inches(0.8)
            image_left = Inches(1.0)
            caption_left = Inches(0.8)
        else:
            # Image on RIGHT
            container_left = Inches(7.8)
            image_left = Inches(8.0)
            caption_left = Inches(7.8)
        
        # Image container with padding
        image_container = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            container_left, Inches(1.8),
            Inches(4.7), Inches(3.5)
        )
        image_container.fill.solid()
        image_container.fill.fore_color.rgb = RGBColor(35, 35, 35)
        image_container.line.fill.background()
        
        # Try to add actual image from suggested_images
        suggested_images = slide_data.get("suggested_images", [])
        
        # Debug: Print available images
        print(f"🔍 Looking for images for slide {slide_data['slide_number']}: {slide_data['slide_title']}")
        print(f"   Found {len(suggested_images)} suggested images")
        
        image_paths = []
        for img in suggested_images:
            img_path = img.get("image_path", "")
            if img_path and os.path.exists(img_path):
                image_paths.append(img_path)
                print(f"   ✅ Valid image found: {img_path}")
            else:
                print(f"   ❌ Image not found or invalid path: {img_path}")
        
        if image_paths:
            try:
                # Add image with perfect fit
                print(f"   🖼️ Attempting to add image: {image_paths[0]}")
                img = slide.shapes.add_picture(
                    image_paths[0],
                    image_left, Inches(2.0),
                    width=Inches(4.3), height=Inches(3.1)
                )
                print(f"   ✅ Successfully added image to slide!")
                
                # Add image caption
                if suggested_images and suggested_images[0].get("caption"):
                    self.add_image_caption(slide, suggested_images[0]["caption"], caption_left, Inches(5.4))
                return
                
            except Exception as e:
                print(f"   ❌ Image error: {e}")
        else:
            print(f"   ⚠️ No valid images found, using placeholder")
        
        # Add attractive placeholder
        self.add_diagonal_image_placeholder(slide, container_left, Inches(1.8), Inches(4.7), Inches(3.5))
        
        # Add image caption even for placeholder
        if suggested_images and suggested_images[0].get("caption"):
            self.add_image_caption(slide, suggested_images[0]["caption"], caption_left, Inches(5.4))
    
    def add_diagonal_image_placeholder(self, slide, left, top, width, height):
        """Add attractive image placeholder for diagonal layout"""
        # Main placeholder box
        placeholder = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, left, top, width, height
        )
        placeholder.fill.solid()
        placeholder.fill.fore_color.rgb = RGBColor(40, 40, 40)
        placeholder.line.fill.background()
        
        # Icon
        icon_box = slide.shapes.add_textbox(
            left + width/2 - Inches(0.3), top + height/2 - Inches(0.4),
            Inches(0.6), Inches(0.6)
        )
        icon_frame = icon_box.text_frame
        icon_frame.text = "🖼️"
        icon_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
        icon_frame.paragraphs[0].font.size = Pt(24)
        icon_frame.paragraphs[0].font.color.rgb = self.colors['text_secondary']
        
        # Placeholder text
        text_box = slide.shapes.add_textbox(
            left, top + height/2 + Inches(0.2),
            width, Inches(0.3)
        )
        text_frame = text_box.text_frame
        text_frame.text = "Visual Content"
        text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
        text_frame.paragraphs[0].font.color.rgb = self.colors['text_secondary']
        text_frame.paragraphs[0].font.size = Pt(14)
        text_frame.paragraphs[0].font.name = "Segoe UI"
    
    def add_image_caption(self, slide, caption_text, left, top):
        """Add caption below image"""
        if caption_text:
            caption_box = slide.shapes.add_textbox(
                left, top, Inches(4.7), Inches(0.3)
            )
            caption_frame = caption_box.text_frame
            # Truncate long captions
            caption = caption_text[:80] + "..." if len(caption_text) > 80 else caption_text
            caption_frame.text = caption
            caption_frame.paragraphs[0].font.size = Pt(11)
            caption_frame.paragraphs[0].font.color.rgb = self.colors['text_secondary']
            caption_frame.paragraphs[0].font.italic = True
            caption_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
            caption_frame.paragraphs[0].font.name = "Segoe UI"
    
    # Background and styling methods
    def add_geometric_background(self, slide):
        """Add geometric elements to title slide background"""
        # Add decorative circles
        for i in range(3):
            circle = slide.shapes.add_shape(
                MSO_SHAPE.OVAL,
                Inches(2 + i*3), Inches(1 + i*0.5),
                Inches(1.2), Inches(1.2)
            )
            circle.fill.solid()
            circle.fill.fore_color.rgb = RGBColor(30, 30, 30)
            circle.line.fill.background()
    
    def add_diagonal_background(self, slide):
        """Add subtle background pattern for diagonal slides"""
        # Add diagonal pattern elements using rectangles instead of lines
        for i in range(4):
            pattern_bar = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE,
                Inches(0.5 + i*1.5), Inches(6.8),
                Inches(0.1), Inches(0.4)
            )
            pattern_bar.fill.solid()
            pattern_bar.fill.fore_color.rgb = RGBColor(35, 35, 35)
            pattern_bar.line.fill.background()
    
    def add_title_decoration(self, slide):
        """Add decorative elements to title slide"""
        # Bottom accent line
        line = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(3.0), self.slide_height - Inches(0.8),
            self.slide_width - Inches(6.0), Inches(0.03)
        )
        line.fill.solid()
        line.fill.fore_color.rgb = self.colors['primary']
        line.line.fill.background()
    
    def style_slide_title(self, title_frame):
        """Style slide titles"""
        for paragraph in title_frame.paragraphs:
            paragraph.font.size = Pt(28)
            paragraph.font.bold = True
            paragraph.font.color.rgb = self.colors['text_primary']
            paragraph.font.name = "Segoe UI"
            paragraph.alignment = PP_ALIGN.CENTER
    
    def add_slide_number(self, slide, slide_number):
        """Add slide number"""
        total_slides = 1 + len([s for s in self.presentation_data["slides"] if s["slide_number"] != 1])
        
        # Modern slide number indicator
        number_bg = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            self.slide_width - Inches(1.8), self.slide_height - Inches(0.5),
            Inches(1.3), Inches(0.35)
        )
        number_bg.fill.solid()
        number_bg.fill.fore_color.rgb = RGBColor(40, 40, 40)
        number_bg.line.color.rgb = self.colors['border']
        number_bg.line.width = Pt(1)
        
        number_box = slide.shapes.add_textbox(
            self.slide_width - Inches(1.8), self.slide_height - Inches(0.5),
            Inches(1.3), Inches(0.35)
        )
        text_frame = number_box.text_frame
        text_frame.text = f"{slide_number}/{total_slides}"
        text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
        text_frame.paragraphs[0].font.color.rgb = self.colors['text_secondary']
        text_frame.paragraphs[0].font.size = Pt(12)
        text_frame.paragraphs[0].font.name = "Segoe UI"

# USAGE
def main():
    # First, adapt the JSON structure
    input_json = "presentation_unlocking_business_potential_with_federated_learni_Nikhil_20251113_132853_with_images.json"
    adapted_json = "adapted_presentation.json"
    
    print("🔄 Adapting JSON structure...")
    # Adapt the JSON structure
    JSONAdapter.adapt_json_for_ppt(input_json, adapted_json)
    
    print("\n🎨 Generating presentation...")
    # Generate presentation with adapted JSON
    generator = SplitDiagonalPresentationGenerator(adapted_json)
    output_file = "Alternating_Split_Diagonal_Presentation4.pptx"
    generator.create_presentation(output_file)
    
    print(f"\n✅ Presentation generated successfully!")
    print(f"📄 Output file: {output_file}")
    print("📊 Layout Summary:")
    print("   - Slide 1: Title/Introduction Slide")
    print("   - Content slides: Images alternate sides")
    print("   - Odd slides: Image LEFT, Text RIGHT")
    print("   - Even slides: Image RIGHT, Text LEFT")

if __name__ == "__main__":
    main()