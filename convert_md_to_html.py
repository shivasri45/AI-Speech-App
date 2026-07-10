#!/usr/bin/env python3
"""
Convert MD to HTML - Open in browser and use Print to PDF (Ctrl+P)
"""

import markdown
from pathlib import Path

# Configuration
md_file = Path("SCORING_METRICS_DOCUMENTATION.md")
html_file = Path("SCORING_METRICS_DOCUMENTATION.html")

print(f"📄 Reading {md_file}...")
md_content = md_file.read_text(encoding='utf-8')

# Convert markdown to HTML
print("🔄 Converting Markdown to HTML...")
html_body = markdown.markdown(
    md_content,
    extensions=['tables', 'fenced_code', 'toc']
)

# Complete HTML with beautiful styling
html_complete = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KIET Soft Skills Platform - Scoring Metrics Documentation</title>
    <style>
        @page {{
            size: A4;
            margin: 2cm;
        }}
        
        * {{
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            font-size: 11pt;
            line-height: 1.6;
            color: #333;
            max-width: 210mm;
            margin: 0 auto;
            padding: 20px;
            background-color: #fff;
        }}
        
        h1 {{
            color: #2c3e50;
            font-size: 28pt;
            border-bottom: 3px solid #3498db;
            padding-bottom: 12px;
            margin-top: 30px;
            page-break-after: avoid;
        }}
        
        h2 {{
            color: #34495e;
            font-size: 20pt;
            border-bottom: 2px solid #95a5a6;
            padding-bottom: 10px;
            margin-top: 25px;
            page-break-after: avoid;
        }}
        
        h3 {{
            color: #2980b9;
            font-size: 16pt;
            margin-top: 20px;
            page-break-after: avoid;
        }}
        
        h4 {{
            color: #7f8c8d;
            font-size: 13pt;
            margin-top: 15px;
        }}
        
        code {{
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 10pt;
            color: #c7254e;
        }}
        
        pre {{
            background-color: #f8f8f8;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            overflow-x: auto;
            font-size: 9pt;
            line-height: 1.4;
            page-break-inside: avoid;
        }}
        
        pre code {{
            background-color: transparent;
            padding: 0;
            color: #333;
        }}
        
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
            font-size: 10pt;
            page-break-inside: avoid;
        }}
        
        th {{
            background-color: #3498db;
            color: white;
            font-weight: bold;
            padding: 12px;
            text-align: left;
            border: 1px solid #2980b9;
        }}
        
        td {{
            padding: 10px;
            border: 1px solid #ddd;
        }}
        
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        
        blockquote {{
            border-left: 4px solid #3498db;
            padding-left: 20px;
            margin-left: 0;
            color: #555;
            font-style: italic;
        }}
        
        ul, ol {{
            margin: 15px 0;
            padding-left: 30px;
        }}
        
        li {{
            margin: 8px 0;
        }}
        
        strong {{
            color: #2c3e50;
            font-weight: 600;
        }}
        
        a {{
            color: #3498db;
            text-decoration: none;
        }}
        
        a:hover {{
            text-decoration: underline;
        }}
        
        hr {{
            border: none;
            border-top: 2px solid #ecf0f1;
            margin: 30px 0;
        }}
        
        /* Print styles */
        @media print {{
            body {{
                max-width: 100%;
                padding: 0;
            }}
            
            h1, h2, h3, h4, h5, h6 {{
                page-break-after: avoid;
            }}
            
            table, pre, blockquote, img {{
                page-break-inside: avoid;
            }}
            
            a {{
                color: #000;
            }}
        }}
        
        /* Header for PDF */
        .doc-header {{
            text-align: center;
            border-bottom: 3px solid #3498db;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        
        .doc-header h1 {{
            margin: 0;
            border: none;
            color: #2c3e50;
        }}
        
        .doc-header p {{
            margin: 10px 0 0 0;
            color: #7f8c8d;
            font-size: 12pt;
        }}
    </style>
</head>
<body>
    <div class="doc-header">
        <h1>KIET Soft Skills Platform</h1>
        <p>Scoring Metrics Documentation</p>
        <p style="font-size: 10pt; color: #95a5a6;">Comprehensive AI Scoring Algorithms | July 2026</p>
    </div>
    
    {html_body}
    
    <hr>
    <p style="text-align: center; color: #95a5a6; font-size: 9pt; margin-top: 30px;">
        Generated from SCORING_METRICS_DOCUMENTATION.md<br>
        KIET Development Team • 2026
    </p>
</body>
</html>
"""

# Save HTML
html_file.write_text(html_complete, encoding='utf-8')

print(f"✅ HTML created successfully: {html_file}")
print(f"📊 File size: {html_file.stat().st_size / 1024:.1f} KB")
print()
print("📌 To create PDF:")
print("   1. Open the HTML file in Chrome/Edge browser")
print("   2. Press Ctrl+P (Print)")
print("   3. Select 'Save as PDF'")
print("   4. Click 'Save'")
print()
print(f"🌐 Opening in browser...")

# Try to open in browser
import webbrowser
webbrowser.open(str(html_file.absolute()))
