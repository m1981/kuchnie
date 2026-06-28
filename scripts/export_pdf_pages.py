#!/usr/bin/env python3
"""
Export all pages from a PDF file to PNG images.

Usage:
    python export_pdf_pages.py <input.pdf> [output_dir] [--dpi 150]

Examples:
    python export_pdf_pages.py blaty.pdf
    python export_pdf_pages.py blaty.pdf ./exported_pages
    python export_pdf_pages.py blaty.pdf ./images --dpi 300
"""

import argparse
import os
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Error: PyMuPDF not installed. Run: uv pip install pymupdf")
    sys.exit(1)


def export_pdf_pages(
    pdf_path: str,
    output_dir: str = None,
    dpi: int = 150,
    page_range: str = None
) -> list[str]:
    """
    Export PDF pages as PNG images.
    
    Args:
        pdf_path: Path to input PDF file
        output_dir: Output directory (default: <pdf_name>_pages)
        dpi: Resolution in dots per inch (default: 150)
        page_range: Page range to export (e.g., "1-5", "1,3,5", "all")
    
    Returns:
        List of exported file paths
    """
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    # Create output directory
    if output_dir is None:
        output_dir = pdf_path.parent / f"{pdf_path.stem}_pages"
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Open PDF
    doc = fitz.open(str(pdf_path))
    
    # Parse page range
    if page_range and page_range != "all":
        pages = parse_page_range(page_range, len(doc))
    else:
        pages = list(range(len(doc)))
    
    # Calculate zoom factor from DPI (PDF default is 72 DPI)
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    
    exported_files = []
    
    print(f"Exporting {len(pages)} pages from {pdf_path.name} to {output_dir}/")
    print(f"Resolution: {dpi} DPI")
    
    for page_num in pages:
        page = doc.load_page(page_num)
        
        # Render page as pixmap
        pixmap = page.get_pixmap(matrix=matrix)
        
        # Generate output filename
        output_filename = f"{pdf_path.stem}-page-{page_num + 1:03d}.png"
        output_path = output_dir / output_filename
        
        # Save image
        pixmap.save(str(output_path))
        exported_files.append(str(output_path))
        
        print(f"  Page {page_num + 1}: {output_filename} ({pixmap.width}x{pixmap.height})")
    
    doc.close()
    
    print(f"\nExported {len(exported_files)} pages to {output_dir}")
    return exported_files


def parse_page_range(range_str: str, total_pages: int) -> list[int]:
    """
    Parse page range string into list of page indices.
    
    Supports:
        "1-5"     -> [0, 1, 2, 3, 4]
        "1,3,5"   -> [0, 2, 4]
        "1-3,7-9" -> [0, 1, 2, 6, 7, 8]
    
    Args:
        range_str: Page range string
        total_pages: Total number of pages in PDF
    
    Returns:
        List of zero-based page indices
    """
    pages = set()
    
    for part in range_str.split(","):
        part = part.strip()
        
        if "-" in part:
            start, end = part.split("-", 1)
            start = max(1, int(start))
            end = min(total_pages, int(end))
            pages.update(range(start - 1, end))
        else:
            page_num = int(part)
            if 1 <= page_num <= total_pages:
                pages.add(page_num - 1)
    
    return sorted(pages)


def main():
    parser = argparse.ArgumentParser(
        description="Export PDF pages as PNG images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s blaty.pdf                      # Export all pages
  %(prog)s blaty.pdf ./output             # Export to specific directory
  %(prog)s blaty.pdf --dpi 300            # High resolution export
  %(prog)s blaty.pdf --pages 1-5          # Export first 5 pages only
  %(prog)s blaty.pdf --pages 1,3,5,7      # Export specific pages
        """
    )
    
    parser.add_argument(
        "pdf_file",
        help="Path to input PDF file"
    )
    
    parser.add_argument(
        "output_dir",
        nargs="?",
        default=None,
        help="Output directory (default: <pdf_name>_pages)"
    )
    
    parser.add_argument(
        "--dpi",
        type=int,
        default=150,
        help="Resolution in DPI (default: 150)"
    )
    
    parser.add_argument(
        "--pages",
        default="all",
        help='Page range to export (e.g., "1-5", "1,3,5", "all")'
    )
    
    args = parser.parse_args()
    
    try:
        exported_files = export_pdf_pages(
            pdf_path=args.pdf_file,
            output_dir=args.output_dir,
            dpi=args.dpi,
            page_range=args.pages
        )
        
        print(f"\n✓ Successfully exported {len(exported_files)} pages")
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error exporting PDF pages: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()