from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.core.files.uploadedfile import UploadedFile
from pdf2image import convert_from_bytes
from PyPDF2 import PdfReader
from PIL import Image, ImageDraw
import pytesseract
import json
import cv2
import numpy as np

@csrf_exempt
def DocCompare(request):
    if request.method == 'POST':
        pdf_file1: UploadedFile = request.FILES['pdf1']
        pdf_file2: UploadedFile = request.FILES['pdf2']

        reader1 = PdfReader(pdf_file1)
        reader2 = PdfReader(pdf_file2)
        num_pages_pdf1 = len(reader1.pages)
        num_pages_pdf2 = len(reader2.pages)
        print(num_pages_pdf1, num_pages_pdf2)
        if num_pages_pdf1 != num_pages_pdf2:
            message = f"Different documents. Each document has a different number of pages: {num_pages_pdf1} and {num_pages_pdf2}."
            return JsonResponse({'message': message})
        else:
            results = {}
            pdf_file1.seek(0)
            images_pdf1 = convert_from_bytes(pdf_file1.read())
            pdf_file2.seek(0)
            images_pdf2 = convert_from_bytes(pdf_file2.read())
            for i in range(num_pages_pdf1):
                # Convert each image
                img1 = cv2.cvtColor(np.array(images_pdf1[i]), cv2.COLOR_RGB2BGR)
                img2 = cv2.cvtColor(np.array(images_pdf2[i]), cv2.COLOR_RGB2BGR)

                # Subtraction of images
                diff = cv2.absdiff(img1, img2)
                
                # Convert to gris scale
                gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
                
                # Threshold
                _, thresh = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY)

                kernel = np.ones((5, 5), np.uint8)
                dilated = cv2.dilate(thresh, kernel, iterations=2)
                compacted = cv2.erode(dilated, kernel, iterations=1)

                contours, _ = cv2.findContours(compacted, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                for contour in contours:
                    if cv2.contourArea(contour) > 10:
                        # Bounding Box
                        x, y, w, h = cv2.boundingRect(contour)
                        x, y, w, h = x - 10, y - 10, w + 20, h + 20
                        
                        roi1 = img1[y:y+h, x:x+w]
                        roi_pil1 = Image.fromarray(cv2.cvtColor(roi1, cv2.COLOR_BGR2RGB))
                        roi_pil1.save(f'roi_pdf1_page_{i + 1}_contour.png')
                        
                        # OCR Text1
                        text1 = pytesseract.image_to_string(roi_pil1)
                 
                        roi2 = img2[y:y+h, x:x+w]
                        roi_pil2 = Image.fromarray(cv2.cvtColor(roi2, cv2.COLOR_BGR2RGB))
                        roi_pil2.save(f'roi_pdf2_page_{i + 1}_contour.png')
                        
                        # OCR Text2
                        text2 = pytesseract.image_to_string(roi_pil2)
                        

                        # Save results
                        text1 = text1.replace("\n", "").strip() if text1 else "Null"
                        text2 = text2.replace("\n", "").strip() if text2 else "Null"
                        text1 = text1 if text1 else "Null"
                        text2 = text2 if text2 else "Null"
                        if i + 1 not in results:
                            results[i + 1] = []
                        results[i + 1].append(text1)
                        results[i + 1].append(text2)
                        
            return JsonResponse({'message': 'Done.', 'results:' : results})

    return JsonResponse({'error': 'Error comparing documents.'})
