import os
from typing import List, Tuple, Dict, Optional
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.chart.data import ChartData, CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.dml import MSO_THEME_COLOR
from pptx.dml.color import RGBColor
from . import config
import logging
import re

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def get_layout(prs: Presentation, name: str = "8_UPFRONT 3"):
    """Get a slide layout by name, falling back to a default if not found."""
    for layout in prs.slide_layouts:
        if layout.name == name:
            return layout
    return prs.slide_layouts[6] if len(prs.slide_layouts) > 6 else prs.slide_layouts[5]

def clear_text(slide):
    """Remove all text boxes from a slide."""
    # We need to convert to list because we're modifying the collection while iterating
    shapes_to_remove = []
    for shape in slide.shapes:
        if shape.has_text_frame:
            shapes_to_remove.append(shape)
    
    # Now remove the shapes
    for shape in shapes_to_remove:
        sp = shape._element
        sp.getparent().remove(sp)

def create_chart_slide(
    prs: Presentation,
    cats: List[str],
    series_list: List[Tuple[str, List[float]]]
) -> Tuple[Presentation, 'Chart']:
    """
    Create a clustered column chart with multiple series.
    
    Args:
        prs: Presentation object
        cats: List of category names
        series_list: List of (label, values) tuples, first expected to be Total
    
    Returns:
        Tuple containing:
        - Updated presentation
        - Created chart object
    """
    logger.debug(f"Creating chart with {len(cats)} categories and {len(series_list)} series")
    
    slide = prs.slides.add_slide(get_layout(prs))
    clear_text(slide)
    x = int((prs.slide_width - Inches(config.CHART_WIDTH)) / 2)
    y = int((prs.slide_height - Inches(config.CHART_HEIGHT)) / 2)

    # Create chart data
    cd = ChartData()
    cd.categories = list(cats)
    for label, vals in series_list:
        cd.add_series(label, list(vals))

    # Add chart to slide
    chart = slide.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED,
        x, y, Inches(config.CHART_WIDTH), Inches(config.CHART_HEIGHT),
        cd
    ).chart

    # Calculate total number of bars
    total_bars = len(cats) * len(series_list)
    
    # Determine data label font size based on number of bars
    if total_bars > 40:
        data_label_size = Pt(6)
    elif total_bars > 15:
        data_label_size = Pt(10)
    else:
        data_label_size = Pt(12)

    # Define available theme colors in order of preference
    accent_colors = [
        MSO_THEME_COLOR.ACCENT_1,
        MSO_THEME_COLOR.ACCENT_2,
        MSO_THEME_COLOR.ACCENT_3,
        MSO_THEME_COLOR.ACCENT_4,
        MSO_THEME_COLOR.ACCENT_5,
        MSO_THEME_COLOR.ACCENT_6
    ]
    
    secondary_colors = [
        MSO_THEME_COLOR.DARK_1,
        MSO_THEME_COLOR.DARK_2,
        MSO_THEME_COLOR.LIGHT_1,
        MSO_THEME_COLOR.LIGHT_2,
        MSO_THEME_COLOR.BACKGROUND_1,
        MSO_THEME_COLOR.BACKGROUND_2
    ]
    
    # Track used colors to ensure consistent cycling
    used_colors = set()
    
    # Style each series with consistent colors
    for idx, (label, _) in enumerate(series_list):
        ser = chart.series[idx]
        ser.format.fill.solid()
        
        # Assign or retrieve theme color
        if label not in config.theme_lookup:
            # Use a consistent color scheme based on the label
            if label == "Total":
                color = MSO_THEME_COLOR.ACCENT_1  # ACCENT_1 for Total
            else:
                # First try to use accent colors
                accent_index = (hash(label) % len(accent_colors))
                if accent_colors[accent_index] not in used_colors:
                    color = accent_colors[accent_index]
                else:
                    # If accent color is used, find next available accent color
                    for i in range(len(accent_colors)):
                        if accent_colors[i] not in used_colors:
                            color = accent_colors[i]
                            break
                    else:
                        # If all accent colors are used, use secondary colors
                        secondary_index = (hash(label) % len(secondary_colors))
                        if secondary_colors[secondary_index] not in used_colors:
                            color = secondary_colors[secondary_index]
                        else:
                            # If secondary color is used, find next available secondary color
                            for i in range(len(secondary_colors)):
                                if secondary_colors[i] not in used_colors:
                                    color = secondary_colors[i]
                                    break
                            else:
                                # If all colors are used, start reusing accent colors
                                color = accent_colors[0]
                
                used_colors.add(color)
            config.theme_lookup[label] = color
            
        ser.format.fill.fore_color.theme_color = config.theme_lookup[label]
        
        # Format data labels
        dl = ser.data_labels
        dl.show_value = True
        dl.number_format = '0%'
        dl.font.name = 'Calibri'
        dl.font.size = data_label_size

    # Remove gridlines & format axes
    chart.value_axis.visible = False
    chart.value_axis.has_major_gridlines = False
    chart.category_axis.has_major_gridlines = False
    
    # Format category axis labels
    tl = chart.category_axis.tick_labels
    tl.font.name = 'Calibri'
    tl.font.size = Pt(12)
    tl.font.color.rgb = RGBColor(0,0,0)
    tl.number_format = '@'  # Use text format
    tl.orientation = 45  # Angle the labels
    tl.offset = 100  # Add some space between labels and axis
    tl.wrap_text = True  # Enable text wrapping

    # Configure legend
    if len(series_list) > 1:
        chart.has_legend = True
        lg = chart.legend
        lg.position = XL_LEGEND_POSITION.TOP
        lg.include_in_layout = False
        lg.font.name = 'Calibri'
        lg.font.size = Pt(12)
    else:
        chart.has_legend = False

    return slide, chart

def add_raw_audience_slides(
    prs: Presentation,
    raw_audience_data: List[Tuple[str, List[str], List[Tuple[str, List[float], int]]]]
) -> Presentation:
    """Add raw audience slides to the presentation."""
    for title, categories, segments in raw_audience_data:
        for label, vals, n_resp in segments:
            series = [(label, vals)]
            slide, chart = create_chart_slide(prs, categories, series)
            
            # Set title
            chart.chart_title.text_frame.text = f"{title} ({label})"
            p = chart.chart_title.text_frame.paragraphs[0]
            p.font.name = 'Calibri'
            p.font.size = Pt(12)
            p.font.italic = True
            p.font.color.rgb = RGBColor(0,0,0)
            
            # Add footer
            y = prs.slide_height - Inches(config.FOOTER_OFFSET) - Inches(0.4)  # Move up by 0.4 inches
            tx = slide.shapes.add_textbox(Inches(0.5), y, Inches(8), Inches(0.3))
            pf = tx.text_frame.paragraphs[0]
            pf.text = f"Source: OnePulse, {label} ({n_resp})"
            pf.font.name = 'Calibri'
            pf.font.size = Pt(10)
            pf.font.color.rgb = RGBColor(0,0,0)
            
    return prs

def add_combined_slides_full_export(
    prs: Presentation,
    combined_data: List[Tuple[str, List[str], List[Tuple[str, List[float], int]]]],
    group_audience_names: set = None
) -> Presentation:
    """Add combined slides for full export: all segments + groups + individual segments."""
    group_audience_names = group_audience_names or set()
    for title, categories, segments in combined_data:
        # Create series list from all segments
        series_list = []
        footer_parts = ["Source: OnePulse"]
        
        for label, vals, n_resp in segments:
            series_list.append((label, vals))
            footer_parts.append(f"{label} ({n_resp})")
        
        # Add the main combined slide with all segments
        slide, chart = create_chart_slide(prs, categories, series_list)
        
        # Set title
        chart.chart_title.text_frame.text = f"{title} ({', '.join(label for label, _, _ in segments)})"
        p = chart.chart_title.text_frame.paragraphs[0]
        p.font.name = 'Calibri'
        p.font.size = Pt(12)
        p.font.italic = True
        p.font.color.rgb = RGBColor(0,0,0)
        
        # Add footer
        y = prs.slide_height - Inches(config.FOOTER_OFFSET) - Inches(0.4)  # Move up by 0.4 inches
        tx = slide.shapes.add_textbox(Inches(0.5), y, Inches(8), Inches(0.3))
        pf = tx.text_frame.paragraphs[0]
        pf.text = ', '.join(footer_parts)
        pf.font.name = 'Calibri'
        pf.font.size = Pt(10)
        pf.font.color.rgb = RGBColor(0,0,0)
        
        # Add group slides first (if any)
        group_segments = [s for s in segments if s[0] != "Total" and " - " in title]
        if group_segments:
            for label, vals, n_resp in group_segments:
                total_segment = next((s for s in segments if s[0] == "Total"), None)
                if total_segment:
                    segment_series = [
                        (total_segment[0], total_segment[1]),
                        (label, vals)
                    ]
                    slide, chart = create_chart_slide(prs, categories, segment_series)
                    chart.chart_title.text_frame.text = f"{title} ({label})"
                    p = chart.chart_title.text_frame.paragraphs[0]
                    p.font.name = 'Calibri'
                    p.font.size = Pt(12)
                    p.font.italic = True
                    p.font.color.rgb = RGBColor(0,0,0)
                    y = prs.slide_height - Inches(config.FOOTER_OFFSET) - Inches(0.4)
                    tx = slide.shapes.add_textbox(Inches(0.5), y, Inches(8), Inches(0.3))
                    pf = tx.text_frame.paragraphs[0]
                    pf.text = f"Source: OnePulse, {label} ({n_resp}), Total ({total_segment[2]})"
                    pf.font.name = 'Calibri'
                    pf.font.size = Pt(10)
                    pf.font.color.rgb = RGBColor(0,0,0)
        
        # Add individual segment slides (for ungrouped audiences)
        non_total_segments = [s for s in segments if s[0] != "Total"]
        is_group_chart = " - " in title  # Check if this is a group chart
        is_individual_chart = title.endswith(")")
        
        if len(non_total_segments) > 1 and not is_group_chart and not is_individual_chart:
            total_segment = None
            for label, vals, n_resp in segments:
                if label == "Total":
                    total_segment = (label, vals, n_resp)
                    break
            if total_segment:
                for label, vals, n_resp in segments:
                    if label != "Total" and label not in group_audience_names:
                        segment_series = [
                            (total_segment[0], total_segment[1]),
                            (label, vals)
                        ]
                        slide, chart = create_chart_slide(prs, categories, segment_series)
                        chart.chart_title.text_frame.text = f"{title} ({label} vs Total)"
                        p = chart.chart_title.text_frame.paragraphs[0]
                        p.font.name = 'Calibri'
                        p.font.size = Pt(12)
                        p.font.italic = True
                        p.font.color.rgb = RGBColor(0,0,0)
                        y = prs.slide_height - Inches(config.FOOTER_OFFSET) - Inches(0.4)
                        tx = slide.shapes.add_textbox(Inches(0.5), y, Inches(8), Inches(0.3))
                        pf = tx.text_frame.paragraphs[0]
                        pf.text = f"Source: OnePulse, {label} ({n_resp}), Total ({total_segment[2]})"
                        pf.font.name = 'Calibri'
                        pf.font.size = Pt(10)
                        pf.font.color.rgb = RGBColor(0,0,0)
    return prs


def add_combined_slides_condensed_export(
    prs: Presentation,
    combined_data: List[Tuple[str, List[str], List[Tuple[str, List[float], int]]]],
    group_audience_names: set = None,
    audience_defs: dict = None,
    raw_audience_data: List[Tuple[str, List[str], List[Tuple[str, List[float], int]]]] = None
) -> Presentation:
    """Add combined slides for condensed export: groups + ungrouped only (no duplication)."""
    group_audience_names = group_audience_names or set()
    ungrouped_audiences = set()
    if audience_defs:
        grouped_audiences = set()
        for group in audience_defs.get("__groups__", []):
            grouped_audiences.update(group.get("audiences", []))
        ungrouped_audiences = set(audience_defs.keys()) - grouped_audiences - {"__groups__"}
    
    # If no audiences are defined, show Total charts only
    if (not audience_defs or (len(audience_defs) == 1 and '__groups__' in audience_defs)) and raw_audience_data:
        for title, categories, segments in raw_audience_data:
            if segments and segments[0][0] == "Total":
                total_segment = segments[0]
                segment_series = [(total_segment[0], total_segment[1])]
                slide, chart = create_chart_slide(prs, categories, segment_series)
                chart.chart_title.text_frame.text = title
                p = chart.chart_title.text_frame.paragraphs[0]
                p.font.name = 'Calibri'
                p.font.size = Pt(12)
                p.font.italic = True
                p.font.color.rgb = RGBColor(0,0,0)
                y = prs.slide_height - Inches(config.FOOTER_OFFSET) - Inches(0.4)
                tx = slide.shapes.add_textbox(Inches(0.5), y, Inches(8), Inches(0.3))
                pf = tx.text_frame.paragraphs[0]
                pf.text = f"Source: OnePulse, Total ({total_segment[2]})"
                pf.font.name = 'Calibri'
                pf.font.size = Pt(10)
                pf.font.color.rgb = RGBColor(0,0,0)
        return prs
    
    slide_count = 0
    for title, categories, segments in combined_data:
        is_group_chart = " - " in title
        is_individual_chart = re.search(r"\([^)]+\)$", title) and not is_group_chart
        non_total_segments = [s for s in segments if s[0] != "Total"]
        if is_group_chart:
            group_name = title.split(" - ")[-1].strip()
            group_members = []
            if audience_defs:
                for group in audience_defs.get("__groups__", []):
                    if group["name"] == group_name:
                        group_members = group.get("audiences", [])
                        break
            segment_labels = [s[0] for s in segments]
            found_members = [m for m in group_members if m in segment_labels]
            total_segment = next((s for s in segments if s[0] == "Total"), None)
            group_segments = [s for s in segments if s[0] != "Total" and s[0] in group_members]
            if total_segment and group_segments:
                segment_series = [(total_segment[0], total_segment[1])]
                group_labels = []
                total_group_resp = 0
                for label, vals, n_resp in group_segments:
                    segment_series.append((label, vals))
                    group_labels.append(label)
                    total_group_resp += n_resp
                combined_group_label = " & ".join(group_labels)
                slide, chart = create_chart_slide(prs, categories, segment_series)
                chart.chart_title.text_frame.text = f"{title} ({combined_group_label})"
                p = chart.chart_title.text_frame.paragraphs[0]
                p.font.name = 'Calibri'
                p.font.size = Pt(12)
                p.font.italic = True
                p.font.color.rgb = RGBColor(0,0,0)
                y = prs.slide_height - Inches(config.FOOTER_OFFSET) - Inches(0.4)
                tx = slide.shapes.add_textbox(Inches(0.5), y, Inches(8), Inches(0.3))
                pf = tx.text_frame.paragraphs[0]
                pf.text = f"Source: OnePulse, {combined_group_label} ({total_group_resp}), Total ({total_segment[2]})"
                pf.font.name = 'Calibri'
                pf.font.size = Pt(10)
                pf.font.color.rgb = RGBColor(0,0,0)
                slide_count += 1
            continue  # Don't process this chart further
        # Skip 'all segments' charts (not group, not individual, more than one non-Total segment)
        if not is_group_chart and not is_individual_chart and len(non_total_segments) > 1:
            continue
        # Process individual charts for ungrouped audiences
        if is_individual_chart:
            total_segment = next((s for s in segments if s[0] == "Total"), None)
            if total_segment and len(segments) == 2:  # Total + one audience
                audience_segment = segments[1]  # The non-Total segment
                label, vals, n_resp = audience_segment
                # Only process if this audience is ungrouped
                if not audience_defs or label in ungrouped_audiences:
                    segment_series = [
                        (total_segment[0], total_segment[1]),
                        (label, vals)
                    ]
                    slide, chart = create_chart_slide(prs, categories, segment_series)
                    chart.chart_title.text_frame.text = f"{title} ({label} vs Total)"
                    p = chart.chart_title.text_frame.paragraphs[0]
                    p.font.name = 'Calibri'
                    p.font.size = Pt(12)
                    p.font.italic = True
                    p.font.color.rgb = RGBColor(0,0,0)
                    y = prs.slide_height - Inches(config.FOOTER_OFFSET) - Inches(0.4)
                    tx = slide.shapes.add_textbox(Inches(0.5), y, Inches(8), Inches(0.3))
                    pf = tx.text_frame.paragraphs[0]
                    pf.text = f"Source: OnePulse, {label} ({n_resp}), Total ({total_segment[2]})"
                    pf.font.name = 'Calibri'
                    pf.font.size = Pt(10)
                    pf.font.color.rgb = RGBColor(0,0,0)
                    slide_count += 1
            continue
        total_segment = next((s for s in segments if s[0] == "Total"), None)
        if total_segment:
            ungrouped_segments = [s for s in segments if s[0] != "Total" and (not audience_defs or s[0] in ungrouped_audiences)]
            for label, vals, n_resp in ungrouped_segments:
                segment_series = [
                    (total_segment[0], total_segment[1]),
                    (label, vals)
                ]
                slide, chart = create_chart_slide(prs, categories, segment_series)
                chart.chart_title.text_frame.text = f"{title} ({label} vs Total)"
                p = chart.chart_title.text_frame.paragraphs[0]
                p.font.name = 'Calibri'
                p.font.size = Pt(12)
                p.font.italic = True
                p.font.color.rgb = RGBColor(0,0,0)
                y = prs.slide_height - Inches(config.FOOTER_OFFSET) - Inches(0.4)
                tx = slide.shapes.add_textbox(Inches(0.5), y, Inches(8), Inches(0.3))
                pf = tx.text_frame.paragraphs[0]
                pf.text = f"Source: OnePulse, {label} ({n_resp}), Total ({total_segment[2]})"
                pf.font.name = 'Calibri'
                pf.font.size = Pt(10)
                pf.font.color.rgb = RGBColor(0,0,0)
                slide_count += 1
    return prs


def add_combined_slides(
    prs: Presentation,
    combined_data: List[Tuple[str, List[str], List[Tuple[str, List[float], int]]]],
    group_audience_names: set = None
) -> Presentation:
    """Add combined slides to the presentation."""
    group_audience_names = group_audience_names or set()
    for title, categories, segments in combined_data:
        # Create series list from all segments
        series_list = []
        footer_parts = ["Source: OnePulse"]
        
        for label, vals, n_resp in segments:
            series_list.append((label, vals))
            footer_parts.append(f"{label} ({n_resp})")
        
        # Add the main combined slide with all segments
        slide, chart = create_chart_slide(prs, categories, series_list)
        
        # Set title
        chart.chart_title.text_frame.text = f"{title} ({', '.join(label for label, _, _ in segments)})"
        p = chart.chart_title.text_frame.paragraphs[0]
        p.font.name = 'Calibri'
        p.font.size = Pt(12)
        p.font.italic = True
        p.font.color.rgb = RGBColor(0,0,0)
        
        # Add footer
        y = prs.slide_height - Inches(config.FOOTER_OFFSET) - Inches(0.4)  # Move up by 0.4 inches
        tx = slide.shapes.add_textbox(Inches(0.5), y, Inches(8), Inches(0.3))
        pf = tx.text_frame.paragraphs[0]
        pf.text = ', '.join(footer_parts)
        pf.font.name = 'Calibri'
        pf.font.size = Pt(10)
        pf.font.color.rgb = RGBColor(0,0,0)
        
        # Only add individual segment slides for all-segments charts (not for individual charts)
        # All-segments charts: title does not end with ")" and does not contain a group indicator
        non_total_segments = [s for s in segments if s[0] != "Total"]
        is_group_chart = " - " in title  # Check if this is a group chart
        is_individual_chart = title.endswith(")")
        
        if len(non_total_segments) > 1 and not is_group_chart and not is_individual_chart:
            total_segment = None
            for label, vals, n_resp in segments:
                if label == "Total":
                    total_segment = (label, vals, n_resp)
                    break
            if total_segment:
                for label, vals, n_resp in segments:
                    if label != "Total" and label not in group_audience_names:
                        segment_series = [
                            (total_segment[0], total_segment[1]),
                            (label, vals)
                        ]
                        slide, chart = create_chart_slide(prs, categories, segment_series)
                        chart.chart_title.text_frame.text = f"{title} ({label} vs Total)"
                        p = chart.chart_title.text_frame.paragraphs[0]
                        p.font.name = 'Calibri'
                        p.font.size = Pt(12)
                        p.font.italic = True
                        p.font.color.rgb = RGBColor(0,0,0)
                        y = prs.slide_height - Inches(config.FOOTER_OFFSET) - Inches(0.4)
                        tx = slide.shapes.add_textbox(Inches(0.5), y, Inches(8), Inches(0.3))
                        pf = tx.text_frame.paragraphs[0]
                        pf.text = f"Source: OnePulse, {label} ({n_resp}), Total ({total_segment[2]})"
                        pf.font.name = 'Calibri'
                        pf.font.size = Pt(10)
                        pf.font.color.rgb = RGBColor(0,0,0)
    return prs

def add_cover_and_methodology_slides(
    prs: Presentation,
    questions_data: List[Tuple[str, str, List[str]]]
) -> Presentation:
    """
    Add cover and methodology slides to the beginning of the presentation.
    
    Args:
        prs: Presentation object
        questions_data: List of (question_id, question_text, response_options) tuples
    
    Returns:
        Updated presentation
    """
    # Load the cover slides template
    cover_prs = Presentation('cover_slides_template.pptx')
    
    # Get the source slides
    source_slides = list(cover_prs.slides)
    
    # Create new slides at the beginning
    for source_slide in reversed(source_slides):  # Reverse to maintain order
        # Get the layout from the source slide
        layout = source_slide.slide_layout
        
        # Create new slide with the same layout
        new_slide = prs.slides.add_slide(layout)
        
        # Copy shapes from source to new slide
        for shape in source_slide.shapes:
            # Get the shape's position and size
            left = shape.left
            top = shape.top
            width = shape.width
            height = shape.height
            
            # Copy the shape based on its type
            if shape.has_text_frame:
                # Create a new text box
                new_shape = new_slide.shapes.add_textbox(left, top, width, height)
                # Copy the text
                new_shape.text_frame.text = shape.text_frame.text
            elif shape.has_chart:
                # Skip charts for now
                continue
            else:
                # For other shapes, just copy the basic properties
                new_shape = new_slide.shapes.add_shape(
                    shape.shape_type,
                    left, top, width, height
                )
    
    return prs

def generate_presentation(
    raw_audience_data: List[Tuple[str, List[str], List[Tuple[str, List[float], int]]]],
    combined_data: List[Tuple[str, List[str], List[Tuple[str, List[float], int]]]],
    output_path: Optional[str] = None,
    group_audience_names: set = None,
    export_type: str = "full",
    audience_defs: dict = None
) -> None:
    """
    Generate the complete PowerPoint presentation using raw audience and combined data.
    Args:
        raw_audience_data: Processed raw audience data (includes categories and values)
        combined_data: Processed combined chart data (includes categories and values)
        output_path: Optional path for the output PowerPoint file. If not provided,
                    uses the default path from config.
        group_audience_names: Set of audience names that are part of a group (to avoid individual slides)
        export_type: Type of export - "full" (all slides) or "condensed" (groups + ungrouped only)
        audience_defs: The audience definitions dict (for group/ungrouped logic)
    """
    # Initialize presentation from template
    prs = Presentation(config.TEMPLATE_PATH)
    
    # Keep only the first two slides (cover and methodology)
    while len(prs.slides) > 2:
        rid = prs.slides._sldIdLst[-1].rId
        prs.part.drop_rel(rid)
        del prs.slides._sldIdLst[-1]

    # Add methodology content to the methodology slide (text box with ID 12)
    methodology_slide = prs.slides[1]  # Second slide
    for shape in methodology_slide.shapes:
        if shape.has_text_frame and shape.shape_id == 12:
            # Create the text frame with proper bullet points
            text_frame = shape.text_frame
            text_frame.clear()  # Clear existing text
            # Add questions and responses
            for title, categories, _ in raw_audience_data:
                # Add question
                p = text_frame.add_paragraph()
                p.text = title
                p.level = 0
                p.font.size = Pt(8)  # Set question text to 8pt
                # Add response options as a single line
                p = text_frame.add_paragraph()
                p.text = f"Response options: {', '.join(f'\"{cat}\"' for cat in categories)}"
                p.level = 1
                p.font.size = Pt(7)  # Set response text to 7pt

    # Validate export_type parameter
    if export_type not in ["full", "condensed"]:
        raise ValueError(f"Invalid export_type: {export_type}. Must be 'full' or 'condensed'")
    
    # Use appropriate function based on export type
    if export_type == "full":
        # Add raw audience slides (individual audience slides)
        prs = add_raw_audience_slides(prs, raw_audience_data)
        # Add combined slides (all segments together + individual vs total)
        prs = add_combined_slides_full_export(prs, combined_data, group_audience_names=group_audience_names)
    else:  # condensed
        # Skip raw audience slides - only add combined slides with groups + ungrouped
        prs = add_combined_slides_condensed_export(prs, combined_data, group_audience_names=group_audience_names, audience_defs=audience_defs, raw_audience_data=raw_audience_data)

    # Save presentation with appropriate filename
    if output_path:
        # If output_path is provided, use it as-is
        output_file = output_path
    else:
        # Generate filename based on export type
        base_name = config.DEFAULT_OUTPUT_PPTX.replace('.pptx', '')
        output_file = f"{base_name}_{export_type}.pptx"
    
    prs.save(output_file)
    print(f"Presentation saved to: {output_file}") 