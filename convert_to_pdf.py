#!/usr/bin/env python3
"""
Convert SCORING_METRICS_DOCUMENTATION.md to PDF
"""

import markdown
from weasyprint import HTML, CSS
from pathlib import Path

# Read the markdown file
md_file = Path("SCORING_METRICS_DOCUMENTATION.md")
pdf_file = Path("SCORING_METRICS_DOCUMENTATION.pdf")

print(f"📄 Reading {md_file}...")
md_content = md_file.read_text(encoding='utf-8')

# Convert markdown to HTML
print("🔄 Converting Markdown to HTML...")
html_content = markdown.markdown(
    md_content,
    extensions=['tables', 'fenced_code', 'codehilite']
)

# Add CSS styling for better PDF output
css_style = """
<style>
    @page {
        size: A4;
        margin: 2cm;
    }
    
    body {
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 11pt;
        line-height: 1.6;
        color: #333;
    }
    
    h1 {
        color: #2c3e50;
        font-size: 24pt;
        border-bottom: 3px solid #3498db;
        padding-bottom: 10px;
        margin-top: 20px;
    }
    
    h2 {
        color: #34495e;
        font-size: 18pt;
        border-bottom: 2px solid #95a5a6;
        padding-bottom: 8px;
        margin-top: 18px;
        page-break-after: avoid;
    }
    
    h3 {
        color: #2980b9;
        font-size: 14pt;
        margin-top: 15px;
        page-break-after: avoid;
    }
    
    h4 {
        color: #7f8c8d;
        font-size: 12pt;
        margin-top: 12px;
    }
    
    code {
        background-color: #f4f4f4;
        padding: 2px 6px;
        border-radius: 3px;
        font-family: 'Consolas', 'Monaco', monospace;
        font-size: 10pt;
        color: #c7254e;
    }
    
    pre {
        background-color: #f8f8f8;
        border: 1px solid #ddd;
        border-radius: 5px;
        padding: 12px;
        overflow-x: auto;
        font-size: 9pt;
        line-height: 1.4;
    }
    
    pre code {
        background-color: transparent;
        padding: 0;
        color: #333;
    }
    
    table {
        border-collapse: collapse;
        width: 100%;
        margin: 15px 0;
        font-size: 10pt;
    }
    
    th {
        background-color: #3498db;
        color: white;
        font-weight: bold;
        padding: 10px;
        text-align: left;
        border: 1px solid #2980b9;
    }
    
    td {
        padding: 8px;
        border: 1px solid #ddd;
    }
    
    tr:nth-child(even) {
        background-color: #f9f9f9;
    }
    
    blockquote {
        border-left: 4px solid #3498db;
        padding-left: 15px;
        margin-left: 0;
        color: #555;
        font-style: italic;
    }
    
    ul, ol {
        margin: 10px 0;
        padding-left: 25px;
    }
    
    li {
        margin: 5px 0;
    }
    
    strong {
        color: #2c3e50;
        font-weight: 600;
    }
    
    a {
        color: #3498db;
        text-decoration: none;
    }
    
    hr {
        border: none;
        border-top: 2px solid #ecf0f1;
        margin: 20px 0;
    }
    
    /* Page break hints */
    .page-break {
        page-break-after: always;
    }
    
    /* Avoid breaking inside these elements */
    table, pre, blockquote {
        page-break-inside: avoid;
    }
</style>
"""

# Combine HTML with CSS
full_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>KIET Soft Skills Platform - Scoring Metrics Documentation</title>
    {css_style}
</head>
<body>
    {html_content}
</body>
</html>
"""

# Convert to PDF
print("📝 Generating PDF...")
HTML(string=full_html).write_pdf(pdf_file)

print(f"✅ PDF created successfully: {pdf_file}")
print(f"📊 File size: {pdf_file.stat().st_size / 1024:.1f} KB")
