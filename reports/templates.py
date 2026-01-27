"""
ReportLab PDF Templates for EOS Alert Reports

Provides professional PDF templates with tier-based features:
- Free tier: Basic table format
- Pro tier: Enhanced with charts and statistics
"""

from datetime import datetime
from io import BytesIO
from typing import List, Dict, Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    PageBreak, Image
)
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.lib.enums import TA_CENTER, TA_RIGHT


# Brand colors
BRAND_PRIMARY = colors.HexColor('#00699b')  # Indigo
BRAND_SECONDARY = colors.HexColor('#009b69')  # Purple
STATUS_ACTIVE = colors.HexColor('#10B981')  # Green
STATUS_APPROACHING = colors.HexColor('#F59E0B')  # Orange
STATUS_EOS = colors.HexColor('#EF4444')  # Red


def get_status_color(status: str) -> colors.Color:
    """
    Get color for device status.
    
    Args:
        status: Device status ("active", "approaching", "end_of_support")
    
    Returns:
        ReportLab Color object
    """
    status_map = {
        "active": STATUS_ACTIVE,
        "approaching": STATUS_APPROACHING,
        "end_of_support": STATUS_EOS,
    }
    return status_map.get(status, colors.grey)


def create_header(title: str, user_name: str, tier: str, device_count: int) -> List:
    """
    Create PDF header section.
    
    Args:
        title: Report title
        user_name: User's full name
        tier: User tier ("free" or "pro")
        device_count: Number of tracked devices
    
    Returns:
        List of ReportLab flowables
    """
    styles = getSampleStyleSheet()
    
    # Custom title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=BRAND_PRIMARY,
        spaceAfter=30,
        alignment=TA_CENTER,
    )
    
    # Subtitle style
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.grey,
        alignment=TA_CENTER,
        spaceAfter=10,
    )
    
    elements = []
    
    # Title
    elements.append(Paragraph(title, title_style))
    elements.append(Paragraph(
        f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
        subtitle_style
    ))
    elements.append(Spacer(1, 0.3 * inch))
    
    # User info table
    tier_display = "Free (3 devices max)" if tier == "free" else "Professional (Unlimited)"
    user_data = [
        ["User:", user_name],
        ["Tier:", tier_display],
        ["Total Devices:", str(device_count)],
    ]
    
    user_table = Table(user_data, colWidths=[2 * inch, 4 * inch])
    user_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica', 10),
        ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 10),
        ('TEXTCOLOR', (0, 0), (0, -1), BRAND_PRIMARY),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    elements.append(user_table)
    elements.append(Spacer(1, 0.5 * inch))
    
    return elements


def create_summary_statistics(stats: Dict[str, int]) -> List:
    """
    Create summary statistics section (Pro tier only).
    
    Args:
        stats: Dictionary with device counts by status
    
    Returns:
        List of ReportLab flowables
    """
    styles = getSampleStyleSheet()
    
    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=BRAND_PRIMARY,
        spaceAfter=15,
    )
    
    elements = []
    
    elements.append(Paragraph("Summary Statistics", heading_style))
    
    # Statistics table
    stats_data = [
        ["Total Devices:", str(stats.get('total', 0))],
        ["Active:", str(stats.get('active', 0))],
        ["Approaching EOS:", str(stats.get('approaching', 0))],
        ["End-of-Support:", str(stats.get('end_of_support', 0))],
    ]
    
    stats_table = Table(stats_data, colWidths=[2.5 * inch, 1.5 * inch])
    stats_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica', 11),
        ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 11),
        ('TEXTCOLOR', (1, 0), (1, 0), colors.black),
        ('TEXTCOLOR', (1, 1), (1, 1), STATUS_ACTIVE),
        ('TEXTCOLOR', (1, 2), (1, 2), STATUS_APPROACHING),
        ('TEXTCOLOR', (1, 3), (1, 3), STATUS_EOS),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
    ]))
    
    elements.append(stats_table)
    elements.append(Spacer(1, 0.4 * inch))
    
    return elements


def create_vendor_pie_chart(vendor_counts: Dict[str, int]) -> Drawing:
    """
    Create pie chart showing device distribution by vendor.
    
    Args:
        vendor_counts: Dictionary mapping vendor names to device counts
    
    Returns:
        ReportLab Drawing containing pie chart
    """
    drawing = Drawing(400, 200)
    
    pie = Pie()
    pie.x = 150
    pie.y = 50
    pie.width = 100
    pie.height = 100
    
    # Prepare data
    labels = list(vendor_counts.keys())[:8]  # Top 8 vendors
    values = list(vendor_counts.values())[:8]
    
    pie.data = values
    pie.labels = labels
    
    # Colors - use a pleasing palette
    chart_colors = [
        colors.HexColor('#6366F1'), colors.HexColor('#8B5CF6'),
        colors.HexColor('#EC4899'), colors.HexColor('#F59E0B'),
        colors.HexColor('#10B981'), colors.HexColor('#3B82F6'),
        colors.HexColor('#14B8A6'), colors.HexColor('#A855F7'),
    ]
    pie.slices.strokeWidth = 0.5
    for i, color in enumerate(chart_colors):
        pie.slices[i].fillColor = color
    
    drawing.add(pie)
    
    return drawing


def create_status_bar_chart(status_counts: Dict[str, int]) -> Drawing:
    """
    Create bar chart showing device counts by status.
    
    Args:
        status_counts: Dictionary mapping status to device counts
    
    Returns:
        ReportLab Drawing containing bar chart
    """
    drawing = Drawing(400, 200)
    
    chart = VerticalBarChart()
    chart.x = 50
    chart.y = 50
    chart.width = 300
    chart.height = 125
    
    # Prepare data
    statuses = ['Active', 'Approaching', 'End-of-Support']
    values = [
        status_counts.get('active', 0),
        status_counts.get('approaching', 0),
        status_counts.get('end_of_support', 0),
    ]
    
    chart.data = [values]
    chart.categoryAxis.categoryNames = statuses
    chart.categoryAxis.labels.boxAnchor = 'ne'
    chart.categoryAxis.labels.dx = -5
    chart.categoryAxis.labels.angle = 0
    chart.categoryAxis.labels.fontName = 'Helvetica'
    chart.categoryAxis.labels.fontSize = 10
    
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = max(values) + 2 if values else 10
    chart.valueAxis.valueStep = max(1, max(values) // 5) if values else 2
    chart.valueAxis.labels.fontName = 'Helvetica'
    chart.valueAxis.labels.fontSize = 9
    
    # Color bars
    chart.bars[0].fillColor = STATUS_ACTIVE
    chart.bars[1].fillColor = STATUS_APPROACHING
    chart.bars[2].fillColor = STATUS_EOS
    
    drawing.add(chart)
    
    return drawing


def create_device_table(devices: List[Dict[str, Any]]) -> Table:
    """
    Create table listing all tracked devices.
    
    Args:
        devices: List of device dictionaries with vendor, model, eos_date, etc.
    
    Returns:
        ReportLab Table object
    """
    # Table headers
    data = [[
        'Vendor',
        'Model',
        'Type',
        'EOS Date',
        'Days Until',
        'Status',
        'Custom Name'
    ]]
    
    # Add device rows
    
    for device in devices:
        custom_name = device.get('custom_name') or '-'
        
        if len(custom_name) > 20:
            custom_name = custom_name[:17] + '...'
        
        eos_date = device.get('eos_date', '')
        if hasattr(eos_date, 'strftime'):
            eos_date = eos_date.strftime('%b %d, %Y')
        
        days_until = device.get('days_until_eos', 0)
        days_display = f"{days_until}" if days_until >= 0 else f"{abs(days_until)} overdue"
        
        status = device.get('status', 'active')
        status_display = status.replace('_', ' ').title()
        
        data.append([
            device.get('vendor', ''),
            device.get('model', ''),
            device.get('device_type', ''),
            eos_date,
            days_display,
            status_display,
            custom_name,
        ])
        
    # Create table
    table = Table(data, colWidths=[
        1.1 * inch,  # Vendor
        1.2 * inch,  # Model
        0.8 * inch,  # Type
        1.0 * inch,  # EOS Date
        0.8 * inch,  # Days
        0.9 * inch,  # Status
        1.2 * inch,  # Custom Name
    ])
    
    # Base style
    table_style = [
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 10),
        ('FONT', (0, 1), (-1, -1), 'Helvetica', 9),
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
        ('ALIGN', (4, 1), (4, -1), 'CENTER'),  # Days center
        ('ALIGN', (5, 1), (5, -1), 'CENTER'),  # Status center
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]
    
    # Add status colors
    for i, device in enumerate(devices, start=1):
        status = device.get('status', 'active')
        color = get_status_color(status)
        table_style.append(('TEXTCOLOR', (5, i), (5, i), color))
        
        # Color days column based on urgency
        days = device.get('days_until_eos', 0)
        if days < 0:
            table_style.append(('TEXTCOLOR', (4, i), (4, i), STATUS_EOS))
        elif days <= 90:
            table_style.append(('TEXTCOLOR', (4, i), (4, i), STATUS_APPROACHING))
    
    table.setStyle(TableStyle(table_style))
    
    return table


def create_footer() -> List:
    """
    Create PDF footer.
    
    Returns:
        List of ReportLab flowables
    """
    styles = getSampleStyleSheet()
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER,
    )
    
    elements = []
    elements.append(Spacer(1, 0.5 * inch))
    elements.append(Paragraph(
        f"Generated by EOS Alert Platform | {datetime.now().strftime('%B %d, %Y')}",
        footer_style
    ))
    
    return elements


def generate_basic_pdf(
    user_name: str,
    tier: str,
    devices: List[Dict[str, Any]],
    buffer: BytesIO
) -> None:
    """
    Generate basic PDF report (free tier).
    
    Args:
        user_name: User's full name
        tier: User tier
        devices: List of tracked devices
        buffer: BytesIO buffer to write PDF to
    """
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    
    story = []
    
    # Header
    story.extend(create_header(
        "EOS Alert Report",
        user_name,
        tier,
        len(devices)
    ))
    
    # Section title
    styles = getSampleStyleSheet()
    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=BRAND_PRIMARY,
        spaceAfter=15,
    )
    
    story.append(Paragraph(f"Tracked Devices ({len(devices)})", heading_style))
    story.append(Spacer(1, 0.2 * inch))
    
    # Device table
    if devices:
        story.append(create_device_table(devices))
    else:
        story.append(Paragraph(
            "No devices tracked yet. Add devices to start monitoring EOS dates.",
            styles['Normal']
        ))
    
    # Footer
    story.extend(create_footer())
    
    doc.build(story)


def generate_enhanced_pdf(
    user_name: str,
    tier: str,
    devices: List[Dict[str, Any]],
    buffer: BytesIO
) -> None:
    """
    Generate enhanced PDF report with charts (Pro tier).
    
    Args:
        user_name: User's full name
        tier: User tier
        devices: List of tracked devices
        buffer: BytesIO buffer to write PDF to
    """
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    # Header
    story.extend(create_header(
        "EOS Alert Report - Professional",
        user_name,
        tier,
        len(devices)
    ))
    
    if devices:
        # Calculate statistics
        status_counts = {'active': 0, 'approaching': 0, 'end_of_support': 0}
        vendor_counts = {}
        
        for device in devices:
            status = device.get('status', 'active')
            status_counts[status] = status_counts.get(status, 0) + 1
            
            vendor = device.get('vendor', 'Unknown')
            vendor_counts[vendor] = vendor_counts.get(vendor, 0) + 1
        
        stats = {
            'total': len(devices),
            **status_counts
        }
        
        # Summary statistics
        story.extend(create_summary_statistics(stats))
        
        # Charts section
        heading_style = ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=BRAND_PRIMARY,
            spaceAfter=15,
        )
        
        # Vendor distribution chart
        if len(vendor_counts) > 0:
            story.append(Paragraph("Device Distribution by Vendor", heading_style))
            story.append(Spacer(1, 0.1 * inch))
            story.append(create_vendor_pie_chart(vendor_counts))
            story.append(Spacer(1, 0.4 * inch))
        
        # Status distribution chart
        story.append(Paragraph("Device Status Distribution", heading_style))
        story.append(Spacer(1, 0.1 * inch))
        story.append(create_status_bar_chart(status_counts))
        story.append(Spacer(1, 0.5 * inch))
        
        # Page break before device table
        story.append(PageBreak())
        
        # Device table
        story.append(Paragraph(f"Tracked Devices ({len(devices)})", heading_style))
        story.append(Spacer(1, 0.2 * inch))
        story.append(create_device_table(devices))
    else:
        story.append(Paragraph(
            "No devices tracked yet. Add devices to start monitoring EOS dates.",
            styles['Normal']
        ))
    
    # Footer
    story.extend(create_footer())
    
    doc.build(story)
