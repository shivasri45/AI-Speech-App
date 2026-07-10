#!/usr/bin/env python3
"""
Convert SCORING_METRICS_DOCUMENTATION.md to PDF using markdown-pdf
"""

from markdown_pdf import MarkdownPdf, Section
from pathlib import Path

# Read the markdown file
md_file = Path("SCORING_METRICS_DOCUMENTATION.md")
pdf_file = Path("SCORING_METRICS_DOCUMENTATION.pdf")

print(f"📄 Reading {md_file}...")
md_content = md_file.read_text(encoding='utf-8')

print("📝 Generating PDF...")

# Create PDF
pdf = MarkdownPdf(toc_level=2)
pdf.add_section(Section(md_content, toc=True))
pdf.meta["title"] = "KIET Soft Skills Platform - Scoring Metrics Documentation"
pdf.meta["author"] = "KIET Development Team"
pdf.save(str(pdf_file))

print(f"✅ PDF created successfully: {pdf_file}")
print(f"📊 File size: {pdf_file.stat().st_size / 1024:.1f} KB")
