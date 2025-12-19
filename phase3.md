Phase 3: Enhanced PDF Service (Day 5-6)
Objective
Create a FastAPI service that not only converts images to PDF but also automatically processes them to improve quality before assembly.

Technology Stack Updates
Core Libraries: FastAPI, Pillow, ReportLab

AI/Image Processing: rembg, opencv-python, scikit-image, numpy

Utilities: python-multipart, loguru

Updated requirements.txt for python-worker/
txt
# Core API
fastapi==0.115.0
uvicorn[standard]==0.32.0
python-multipart==0.0.16

# PDF & Image Core
pillow==10.4.0
reportlab==4.1.0

# AI Image Processing
rembg==2.0.56        # For background removal
opencv-python==4.10.0.84  # For contour/corner detection
scikit-image==0.24.0 # For advanced enhancement
numpy==1.26.4

# Utilities
loguru==0.7.2        # For structured logging
Revised Implementation Tasks
Day 5: Core Service with Smart Processing
Create FastAPI service structure

python
# pdf_service/main.py
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
import tempfile
import os
from datetime import datetime

app = FastAPI(title="Smart PDF Generator")

@app.post("/generate-pdf")
async def generate_pdf(files: list[UploadFile] = File(...)):
    # 1. Validate input (min 1, max 10 images, valid types)
    # 2. Create temp directory for processing
    # 3. Process each image through smart pipeline
    # 4. Compile processed images to PDF
    # 5. Return PDF file path for download
    pass
Implement SmartImageProcessor class

python
# pdf_service/processor.py
class SmartImageProcessor:
    def __init__(self):
        self.download_rembg_model()  # First-run setup
    
    def process(self, image_bytes: bytes) -> Image:
        """Main processing pipeline"""
        # 1. Remove background (rembg)
        # 2. Detect document corners (OpenCV)
        # 3. Crop and deskew if corners found
        # 4. Enhance quality (contrast, sharpness, denoise)
        # 5. Convert to consistent format (RGB, standard DPI)
        return processed_image
Add background removal with rembg

python
# In processor.py
from rembg import remove, new_session
import cv2

def remove_background(self, image_bytes):
    # Use rembg's U²-Net model
    output_bytes = remove(image_bytes, session=self.session)
    return Image.open(io.BytesIO(output_bytes))
Day 6: PDF Assembly & API Integration
Implement corner detection and cropping logic

python
def detect_and_crop(self, cv_image):
    """Find document edges and crop to content"""
    # Convert to grayscale
    # Apply edge detection (Canny)
    # Find contours
    # Select largest quadrilateral contour
    # Apply perspective transform if 4 corners found
    # Fallback: intelligent bounding box crop
    return cropped_image
Add image enhancement pipeline

python
def enhance_quality(self, image):
    """Improve image clarity for documents"""
    # 1. Adaptive histogram equalization for contrast
    # 2. Unsharp masking for edge clarity
    # 3. Mild denoising for scanned documents
    # 4. Auto-white-balance correction
    # 5. Standardize to 300 DPI for print-ready PDF
    return enhanced_image
Create PDF generator with metadata

python
# pdf_service/pdf_builder.py
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas

class PDFBuilder:
    def create_pdf(self, images: list, output_path: str):
        """Create PDF from processed images"""
        c = canvas.Canvas(output_path, pagesize=A4)
        
        # Add metadata
        c.setTitle("Generated Document")
        c.setAuthor("WhatsApp PDF Bot")
        c.setSubject(f"Document generated on {datetime.now()}")
        
        # Add each image as a page
        for i, img in enumerate(images):
            # Scale image to fit page while maintaining aspect ratio
            # Center image on page
            # Add page number footer
            c.drawImage(img_path, x, y, width, height)
            c.showPage()
        
        c.save()
Implement intelligent image sorting

python
def sort_images(self, files: list, upload_times: list):
    """Sort by multiple strategies for best results"""
    # Priority 1: Explicit filename numbering (page_01.jpg, page_02.jpg)
    # Priority 2: EXIF/creation date metadata
    # Priority 3: Upload sequence (fallback)
    # Priority 4: Content analysis (for multi-page documents)
    return sorted_files
Add comprehensive error handling

python
@app.post("/generate-pdf")
async def generate_pdf(files: list[UploadFile] = File(...)):
    try:
        # Processing logic
        return FileResponse(pdf_path, 
                          media_type="application/pdf",
                          filename=f"document_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
    except InvalidImageError:
        raise HTTPException(400, "One or more images are corrupted")
    except ProcessingError:
        raise HTTPException(500, "Failed to process images")
    finally:
        # Cleanup temp files
        pass
Updated API Response Format
json
{
  "success": true,
  "pdf_url": "/download/generated_20241210_143022.pdf",
  "processing_summary": {
    "images_processed": 5,
    "backgrounds_removed": 5,
    "documents_cropped": 4,
    "pages_generated": 5,
    "processing_time": "2.3s"
  },
  "quality_notes": [
    "Cropped 4/5 images to document boundaries",
    "Enhanced contrast on all images",
    "Page 3 had low resolution - consider retaking"
  ]
}
Testing Checklist for Phase 3
Background Removal: Test with photos of documents on desks, tables, textured surfaces

Corner Detection: Verify with slightly rotated, skewed document images

Enhancement Pipeline: Compare before/after for low-light, blurry, or low-contrast images

PDF Assembly: Generate PDF with 1, 5, and 10 images, verify page order and quality

Error Handling: Test with corrupted images, unsupported formats, empty requests

Performance: Process 10 images in under 10 seconds on modest hardware (2GB RAM)

Memory Management: Verify temp files are cleaned up, no memory leaks

Integration with Node.js Service
javascript
// In your Node.js message-handler.js
async function generatePDF(images) {
  const formData = new FormData();
  
  images.forEach((imgPath, index) => {
    formData.append('files', 
      fs.createReadStream(imgPath),
      `page_${index + 1}.jpg`);
  });
  
  const response = await fetch('http://localhost:8000/generate-pdf', {
    method: 'POST',
    body: formData
  });
  
  // Download PDF and send via WhatsApp
  const pdfBuffer = await response.buffer();
  // Send to user...
}