from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime
from PIL import Image

class PDFBuilder:
    def create_pdf(self, images: list, output_path: str):
        c = canvas.Canvas(output_path, pagesize=A4)
        c.setTitle("Generated Document")
        c.setAuthor("WhatsApp PDF Bot")
        c.setSubject(f"Document generated on {datetime.now()}")

        page_width, page_height = A4

        for idx, img_path in enumerate(images, start=1):
            try:
                img = Image.open(img_path)
                iw, ih = img.size
                # scale to fit within A4 while keeping aspect
                scale = min(page_width / iw, page_height / ih)
                w = iw * scale
                h = ih * scale
                x = (page_width - w) / 2
                y = (page_height - h) / 2
                c.drawImage(str(img_path), x, y, width=w, height=h)
                c.drawString(30, 30, f"Page {idx}")
                c.showPage()
            except Exception as e:
                print(f"Error processing image {img_path}: {e}")
                continue

        c.save()