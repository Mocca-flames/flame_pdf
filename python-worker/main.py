from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import time
from pathlib import Path
from pydantic import BaseModel
from processor import SmartImageProcessor
from pdf_builder import PDFBuilder

app = FastAPI(title="Smart PDF Generator")

processor = SmartImageProcessor()
pdf_builder = PDFBuilder()

class GenerateRequest(BaseModel):
    userId: str
    imageDir: str

@app.post("/generate-pdf")
async def generate_pdf(req: GenerateRequest):
    image_dir = Path(req.imageDir)
    ready_file = image_dir / "READY.txt"

    # Poll for READY.txt with 10-second timeout
    timeout = 10.0
    start_time = time.time()
    while not ready_file.exists():
        if time.time() - start_time > timeout:
            raise HTTPException(status_code=408, detail="Timeout waiting for images")
        time.sleep(0.5)

    # Read images
    image_files = sorted([f for f in image_dir.glob("img_*.jpg") if f.is_file()] +
                         [f for f in image_dir.glob("img_*.png") if f.is_file()])
    if not image_files:
        raise HTTPException(status_code=400, detail="No images found")

    processed_paths = []
    transformed_flags = []
    try:
        for img_path in image_files:
            with open(img_path, "rb") as f:
                contents = f.read()
            processed, is_transformed = processor.process(contents)
            transformed_flags.append(is_transformed)
            out_path = image_dir / f"processed_{img_path.name}"
            processed.save(out_path, format="PNG")
            processed_paths.append(out_path)

        # Check if any image failed transformation (fallback used)
        if False in transformed_flags:
            # Use demo image instead of generating PDF
            return {
                "success": True,
                "useDemo": True,
                "demoImage": "assets/demo.png"
            }

        output_pdf = image_dir / "output.pdf"
        pdf_builder.create_pdf(processed_paths, str(output_pdf))

        # Cleanup: delete images, processed files, and READY.txt
        for f in image_files + processed_paths + [ready_file]:
            if f.exists():
                f.unlink()

        # Get stats
        page_count = len(image_files)
        file_size = output_pdf.stat().st_size

        return {
            "success": True,
            "pdfPath": str(output_pdf),
            "pageCount": page_count,
            "fileSize": f"{file_size} bytes"
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Processing failed: {exc}")

@app.get("/health")
async def health():
    return JSONResponse({"status": "ok"})

@app.get("/")
async def health():
    return JSONResponse({"Running Code": "python-worker"})
