#!/usr/bin/env python3
"""
Simple MD to PDF converter using PyMuPDF directly
"""

import fitz  # PyMuPDF
import markdown
from pathlib import Path

# Configuration
md_file = Path("SCORING_METRICS_DOCUMENTATION.md")
pdf_file = Path("SCORING_METRICS_DOCUMENTATION.pdf")

print(f"📄 Reading {md_file}...")
md_content = md_file.read_text(encoding='utf-8')

# Convert markdown to HTML
print("🔄 Converting Markdown to HTML...")
html_content = markdown.markdown(
    md_content,
    extensions=['tables', 'fenced_code']
)

# Add CSS styling
html_with_style = f"""
<html>
<head>
<style>
body {{
    font-family: Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    margin: 40px;
}}
h1 {{
    color: #2c3e50;
    font-size: 20pt;
    border-bottom: 2px solid #3498db;
    padding-bottom: 8px;
}}
h2 {{
    color: #34495e;
    font-size: 16pt;
    border-bottom: 1px solid #95a5a6;
    padding-bottom: 6px;
    margin-top: 20px;
}}
h3 {{
    color: #2980b9;
    font-size: 13pt;
    margin-top: 15px;
}}
code {{
    background-color: #f4f4f4;
    padding: 2px 4px;
    border-radius: 3px;
    font-family: Consolas, monospace;
    font-size: 9pt;
}}
pre {{
    background-color: #f8f8f8;
    border: 1px solid #ddd;
    padding: 10px;
    overflow-x: auto;
    font-size: 9pt;
}}
table {{
    border-collapse: collapse;
    width: 100%;
    margin: 15px 0;
}}
th {{
    background-color: #3498db;
    color: white;
    padding: 8px;
    text-align: left;
}}
td {{
    border: 1px solid #ddd;
    padding: 6px;
}}
tr:nth-child(even) {{
    background-color: #f9f9f9;
}}
</style>
</head>
<body>
{html_content}
</body>
</html>
"""

# Create PDF
print("📝 Generating PDF...")
doc = fitz.open()  # Create empty PDF

# Use Story for HTML to PDF conversion
story = fitz.Story(html_with_style)

# Create pages from story
MEDIABOX = fitz.paper_rect("a4")  # A4 page size
MARGINS = fitz.Rect(40, 40, MEDIABOX.width - 40, MEDIABOX.height - 40)

while True:
    page = doc.new_page(width=MEDIABOX.width, height=MEDIABOX.height)
    more_content, _ = story.place(MARGINS)
    story.draw(page)
    
    if not more_content:
        break

# Save PDF
doc.save(str(pdf_file))
doc.close()

print(f"✅ PDF created successfully: {pdf_file}")
print(f"📊 File size: {pdf_file.stat().st_size / 1024:.1f} KB")
print(f"📄 Total pages: {fitz.open(str(pdf_file)).page_count}")
