"""
PDF Generation Utilities for YummyTummy Recipe System

This module provides utilities for generating beautifully formatted recipe PDFs
with YummyTummy branding using ReportLab.
"""

import os
import io
from datetime import datetime
from django.conf import settings
from django.core.files.base import ContentFile
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.platypus.flowables import HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas
import pytz


class YummyTummyPDFGenerator:
    """PDF Generator for YummyTummy recipes with brand styling"""
    
    # YummyTummy Brand Colors
    PRIMARY_COLOR = HexColor('#593500')      # Brown
    SECONDARY_COLOR = HexColor('#ffffff')    # White  
    ACCENT_COLOR = HexColor('#f5f2ed')       # Cream
    HIGHLIGHT_COLOR = HexColor('#ffc107')    # Yellow
    TEXT_COLOR = HexColor('#333333')         # Dark gray for readability
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles with YummyTummy branding"""
        
        # Title style
        self.title_style = ParagraphStyle(
            'YummyTummyTitle',
            parent=self.styles['Title'],
            fontSize=24,
            textColor=self.PRIMARY_COLOR,
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        # Subtitle style
        self.subtitle_style = ParagraphStyle(
            'YummyTummySubtitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=self.PRIMARY_COLOR,
            spaceAfter=12,
            spaceBefore=16,
            fontName='Helvetica-Bold'
        )
        
        # Body text style
        self.body_style = ParagraphStyle(
            'YummyTummyBody',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=self.TEXT_COLOR,
            spaceAfter=6,
            alignment=TA_JUSTIFY,
            fontName='Helvetica'
        )
        
        # List item style
        self.list_style = ParagraphStyle(
            'YummyTummyList',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=self.TEXT_COLOR,
            spaceAfter=4,
            leftIndent=20,
            fontName='Helvetica'
        )
        
        # Highlight box style
        self.highlight_style = ParagraphStyle(
            'YummyTummyHighlight',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=self.PRIMARY_COLOR,
            spaceAfter=8,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
    
    def _add_header(self, story):
        """Add YummyTummy header with logo and branding"""
        # YummyTummy Logo/Title
        logo_text = Paragraph(
            '<font size="28" color="#593500"><b>YummyTummy</b></font><br/>'
            '<font size="12" color="#666666">Healthy Living Made Delicious</font>',
            self.styles['Normal']
        )
        story.append(logo_text)
        story.append(Spacer(1, 20))
        
        # Decorative line
        story.append(HRFlowable(width="100%", thickness=2, color=self.HIGHLIGHT_COLOR))
        story.append(Spacer(1, 20))
    
    def _add_recipe_info_table(self, story, recipe):
        """Add recipe information table (prep time, cook time, servings, difficulty)"""
        # Prepare recipe info data
        prep_time = f"{recipe.prep_time_minutes} min" if recipe.prep_time_minutes else "N/A"
        cook_time = f"{recipe.cook_time_minutes} min" if recipe.cook_time_minutes else "N/A"
        total_time = "N/A"
        if recipe.prep_time_minutes and recipe.cook_time_minutes:
            total_time = f"{recipe.prep_time_minutes + recipe.cook_time_minutes} min"
        
        info_data = [
            ['Prep Time', 'Cook Time', 'Total Time', 'Servings', 'Difficulty'],
            [prep_time, cook_time, total_time, str(recipe.servings), recipe.get_difficulty_display()]
        ]
        
        # Create table
        info_table = Table(info_data, colWidths=[1.2*inch, 1.2*inch, 1.2*inch, 1*inch, 1*inch])
        info_table.setStyle(TableStyle([
            # Header row styling
            ('BACKGROUND', (0, 0), (-1, 0), self.ACCENT_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), self.PRIMARY_COLOR),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Data row styling
            ('BACKGROUND', (0, 1), (-1, 1), self.SECONDARY_COLOR),
            ('TEXTCOLOR', (0, 1), (-1, 1), self.TEXT_COLOR),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, 1), 10),
            
            # Grid styling
            ('GRID', (0, 0), (-1, -1), 1, self.PRIMARY_COLOR),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [self.SECONDARY_COLOR, self.ACCENT_COLOR]),
        ]))
        
        story.append(info_table)
        story.append(Spacer(1, 20))
    
    def _add_ingredients_section(self, story, recipe):
        """Add ingredients section with proper formatting"""
        story.append(Paragraph("Ingredients", self.subtitle_style))
        
        if recipe.ingredients:
            for i, ingredient in enumerate(recipe.ingredients, 1):
                ingredient_text = f"• {ingredient}"
                story.append(Paragraph(ingredient_text, self.list_style))
        else:
            story.append(Paragraph("No ingredients listed.", self.body_style))
        
        story.append(Spacer(1, 16))
    
    def _add_instructions_section(self, story, recipe):
        """Add instructions section with step numbering"""
        story.append(Paragraph("Instructions", self.subtitle_style))
        
        if recipe.instructions:
            for i, instruction in enumerate(recipe.instructions, 1):
                instruction_text = f"<b>Step {i}:</b> {instruction}"
                story.append(Paragraph(instruction_text, self.body_style))
                story.append(Spacer(1, 8))
        else:
            story.append(Paragraph("No instructions provided.", self.body_style))
        
        story.append(Spacer(1, 16))
    
    def _add_footer(self, story):
        """Add footer with YummyTummy branding and timestamp"""
        # Add some space before footer
        story.append(Spacer(1, 30))
        
        # Decorative line
        story.append(HRFlowable(width="100%", thickness=1, color=self.HIGHLIGHT_COLOR))
        story.append(Spacer(1, 10))
        
        # Footer text with Kenya timezone
        kenya_tz = pytz.timezone('Africa/Nairobi')
        current_time = datetime.now(kenya_tz)
        
        footer_text = (
            f'<font size="9" color="#666666">'
            f'Generated by YummyTummy • {current_time.strftime("%B %d, %Y at %I:%M %p EAT")}<br/>'
            f'Visit us at www.yummytummy.co.ke • Follow @yummytummygoodies_ke'
            f'</font>'
        )
        
        footer_para = Paragraph(footer_text, self.styles['Normal'])
        footer_para.alignment = TA_CENTER
        story.append(footer_para)
    
    def generate_recipe_pdf(self, recipe):
        """
        Generate a PDF for the given recipe
        
        Args:
            recipe: Recipe model instance
            
        Returns:
            ContentFile: Django ContentFile containing the PDF data
        """
        # Create a BytesIO buffer to hold the PDF
        buffer = io.BytesIO()
        
        # Create the PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Build the story (content)
        story = []
        
        # Add header
        self._add_header(story)
        
        # Add recipe title
        story.append(Paragraph(recipe.title, self.title_style))
        
        # Add description if available
        if recipe.description:
            story.append(Paragraph(recipe.description, self.body_style))
            story.append(Spacer(1, 16))
        
        # Add recipe info table
        self._add_recipe_info_table(story, recipe)
        
        # Add ingredients section
        self._add_ingredients_section(story, recipe)
        
        # Add instructions section
        self._add_instructions_section(story, recipe)
        
        # Add footer
        self._add_footer(story)
        
        # Build the PDF
        doc.build(story)
        
        # Get the PDF data
        pdf_data = buffer.getvalue()
        buffer.close()
        
        # Create a Django ContentFile
        filename = f"{recipe.slug}_recipe.pdf"
        return ContentFile(pdf_data, name=filename)


def generate_recipe_pdf(recipe):
    """
    Convenience function to generate a PDF for a recipe
    
    Args:
        recipe: Recipe model instance
        
    Returns:
        ContentFile: Django ContentFile containing the PDF data
    """
    generator = YummyTummyPDFGenerator()
    return generator.generate_recipe_pdf(recipe)
