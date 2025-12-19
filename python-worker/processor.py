import io
import numpy as np
import cv2
from PIL import Image, ImageEnhance
from typing import Optional, Tuple, List

class SmartImageProcessor:
    """Advanced document scanner with multiple detection strategies and robust fallbacks."""
    
    def __init__(self):
        self.debug = True  # Enable detailed logging
        
    def process(self, image_bytes: bytes) -> Tuple[Image.Image, bool]:
        """Main processing: detect document and transform to flat view"""
        try:
            # Load image
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img is None:
                raise ValueError("Failed to decode image")

            print(f"Image loaded: {img.shape}")
            original = img.copy()

            # Try multiple detection strategies
            corners = self._find_document_corners_multi_strategy(img)

            if corners is not None:
                print(f"✓ Corners found: {corners}")
                print(f"Corner shape: {corners.shape}, dtype: {corners.dtype}")

                # Validate corners before transformation
                is_valid = self._validate_corners(corners, img.shape)
                print(f"✓ Corners validation: {is_valid}")

                if is_valid:
                    print("✓ Starting perspective transformation...")
                    # Transform to flat, top-down view
                    transformed = self._transform_perspective(original, corners)
                    print(f"✓ Transformed image shape: {transformed.shape}")

                    # Enhance quality
                    enhanced = self._enhance_quality(transformed)
                    print("✓ Enhancement complete")

                    # Convert to PIL
                    result = Image.fromarray(cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB))
                    print("✓✓✓ SUCCESS: Document scanned and transformed!")
                    return result, True
                else:
                    print("✗ Corner validation failed")
            else:
                print("✗ No corners detected")

            # Fallback: aggressive enhancement of original
            print("→ Using fallback: enhanced original without transformation")
            enhanced = self._enhance_quality_aggressive(original)
            return Image.fromarray(cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB)), False

        except Exception as e:
            print(f"✗✗✗ CRITICAL ERROR in process: {e}")
            import traceback
            traceback.print_exc()
            # Return original on error
            pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            return pil_img, False
    
    def _find_document_corners_multi_strategy(self, img) -> Optional[np.ndarray]:
        """Try multiple strategies to find document corners"""
        
        # Strategy 1: Standard edge detection with multiple thresholds
        corners = self._strategy_edge_detection(img)
        if corners is not None:
            print("→ Found corners using edge detection strategy")
            return corners
        
        # Strategy 2: Adaptive thresholding approach
        corners = self._strategy_adaptive_threshold(img)
        if corners is not None:
            print("→ Found corners using adaptive threshold strategy")
            return corners
        
        # Strategy 3: Color-based segmentation
        corners = self._strategy_color_segmentation(img)
        if corners is not None:
            print("→ Found corners using color segmentation strategy")
            return corners
        
        # Strategy 4: Morphological operations
        corners = self._strategy_morphological(img)
        if corners is not None:
            print("→ Found corners using morphological strategy")
            return corners
        
        print("→ All strategies failed to find document corners")
        return None
    
    def _strategy_edge_detection(self, img) -> Optional[np.ndarray]:
        """Strategy 1: Enhanced edge detection with multiple preprocessing"""
        height, width = img.shape[:2]
        ratio = height / 800.0
        resized = cv2.resize(img, (int(width / ratio), 800))
        
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        
        # Try multiple preprocessing approaches
        preprocessed_images = []
        
        # Approach 1: Bilateral filter (preserves edges while reducing noise)
        bilateral = cv2.bilateralFilter(gray, 9, 75, 75)
        preprocessed_images.append(bilateral)
        
        # Approach 2: Gaussian blur
        gaussian = cv2.GaussianBlur(gray, (5, 5), 0)
        preprocessed_images.append(gaussian)
        
        # Approach 3: Median blur (good for salt-and-pepper noise)
        median = cv2.medianBlur(gray, 5)
        preprocessed_images.append(median)
        
        # Try different edge detection parameters for each preprocessed image
        edge_params = [
            (30, 100),
            (50, 150),
            (75, 200),
            (100, 250),
        ]
        
        for preprocessed in preprocessed_images:
            for low, high in edge_params:
                edged = cv2.Canny(preprocessed, low, high)
                
                # Dilate to close gaps
                kernel = np.ones((3, 3), np.uint8)
                edged = cv2.dilate(edged, kernel, iterations=2)
                edged = cv2.erode(edged, kernel, iterations=1)
                
                corners = self._find_best_contour(edged, resized.shape, ratio)
                if corners is not None:
                    return corners
        
        return None
    
    def _strategy_adaptive_threshold(self, img) -> Optional[np.ndarray]:
        """Strategy 2: Adaptive thresholding for challenging lighting"""
        height, width = img.shape[:2]
        ratio = height / 800.0
        resized = cv2.resize(img, (int(width / ratio), 800))
        
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Try both adaptive threshold methods
        thresh_methods = [
            cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                 cv2.THRESH_BINARY, 11, 2),
            cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_MEAN_C, 
                                 cv2.THRESH_BINARY, 11, 2)
        ]
        
        for thresh in thresh_methods:
            # Morphological operations to clean up
            kernel = np.ones((5, 5), np.uint8)
            morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
            
            # Edge detection on thresholded image
            edged = cv2.Canny(morph, 50, 150)
            
            # Dilate edges
            kernel = np.ones((3, 3), np.uint8)
            edged = cv2.dilate(edged, kernel, iterations=2)
            
            corners = self._find_best_contour(edged, resized.shape, ratio)
            if corners is not None:
                return corners
        
        return None
    
    def _strategy_color_segmentation(self, img) -> Optional[np.ndarray]:
        """Strategy 3: Use color information to find document"""
        height, width = img.shape[:2]
        ratio = height / 800.0
        resized = cv2.resize(img, (int(width / ratio), 800))
        
        # Convert to LAB color space
        lab = cv2.cvtColor(resized, cv2.COLOR_BGR2LAB)
        
        # Try to segment based on brightness (documents are often lighter)
        l_channel = lab[:, :, 0]
        
        # Otsu's thresholding on L channel
        _, thresh = cv2.threshold(l_channel, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Morphological operations
        kernel = np.ones((7, 7), np.uint8)
        morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=3)
        
        # Find edges
        edged = cv2.Canny(morph, 50, 150)
        
        # Dilate
        kernel = np.ones((3, 3), np.uint8)
        edged = cv2.dilate(edged, kernel, iterations=2)
        
        corners = self._find_best_contour(edged, resized.shape, ratio)
        return corners
    
    def _strategy_morphological(self, img) -> Optional[np.ndarray]:
        """Strategy 4: Heavy morphological processing"""
        height, width = img.shape[:2]
        ratio = height / 800.0
        resized = cv2.resize(img, (int(width / ratio), 800))
        
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        
        # CLAHE for better contrast
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Bilateral filter
        filtered = cv2.bilateralFilter(enhanced, 9, 75, 75)
        
        # Morphological gradient (edges)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        gradient = cv2.morphologyEx(filtered, cv2.MORPH_GRADIENT, kernel)
        
        # Threshold
        _, thresh = cv2.threshold(gradient, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Close gaps
        kernel = np.ones((7, 7), np.uint8)
        morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=3)
        
        # Find contours
        corners = self._find_best_contour(morph, resized.shape, ratio)
        return corners
    
    def _find_best_contour(self, edged, img_shape, ratio) -> Optional[np.ndarray]:
        """Find the best 4-sided contour from edge-detected image"""
        try:
            contours, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return None
            
            # Sort by area (largest first)
            contours = sorted(contours, key=cv2.contourArea, reverse=True)[:15]
            
            img_area = img_shape[0] * img_shape[1]
            
            # Look for 4-sided contour
            for contour in contours:
                # Skip if contour is too small
                if len(contour) < 4:
                    continue
                
                try:
                    area = cv2.contourArea(contour)
                except:
                    continue
                
                # Document should be at least 5% of image (lowered threshold)
                if area < img_area * 0.05:
                    continue
                
                # Don't accept if it's almost the entire image (likely false positive)
                if area > img_area * 0.98:
                    continue
                
                # Approximate the contour with different epsilon values
                peri = cv2.arcLength(contour, True)
                
                if peri == 0:
                    continue
                
                for epsilon_factor in [0.02, 0.03, 0.04, 0.05, 0.06]:
                    approx = cv2.approxPolyDP(contour, epsilon_factor * peri, True)
                    
                    if len(approx) == 4:
                        # Reshape and ensure proper format
                        corners = approx.reshape(4, 2).astype(np.float32)
                        
                        # Scale back to original size
                        corners = corners * ratio
                        
                        # Additional validation
                        if self._is_valid_quadrilateral(corners):
                            return corners
            
            return None
            
        except Exception as e:
            print(f"Error in _find_best_contour: {e}")
            return None
    
    def _is_valid_quadrilateral(self, corners) -> bool:
        """Check if the 4 corners form a valid quadrilateral"""
        try:
            if len(corners) != 4:
                print(f"  Validation: wrong number of corners ({len(corners)})")
                return False
            
            # Ensure corners are numpy array
            corners = np.array(corners, dtype=np.float32)
            
            # Calculate angles at each corner
            angles = []
            for i in range(4):
                p1 = corners[i]
                p2 = corners[(i + 1) % 4]
                p3 = corners[(i + 2) % 4]
                
                v1 = p1 - p2
                v2 = p3 - p2
                
                # Calculate angle
                norm1 = np.linalg.norm(v1)
                norm2 = np.linalg.norm(v2)
                
                if norm1 == 0 or norm2 == 0:
                    print(f"  Validation: zero-length edge detected")
                    return False
                
                cos_angle = np.dot(v1, v2) / (norm1 * norm2)
                cos_angle = np.clip(cos_angle, -1.0, 1.0)
                angle = np.arccos(cos_angle)
                angles.append(np.degrees(angle))
            
            # RELAXED: All angles should be between 20 and 160 degrees (very permissive for perspective)
            invalid_angles = [a for a in angles if a <= 20 or a >= 160]
            if invalid_angles:
                print(f"  Validation: invalid angles {angles} (too extreme: {invalid_angles})")
                return False
            
            if self.debug:
                print(f"  Validation: angles OK {[f'{a:.1f}°' for a in angles]}")
            
            return True
            
        except Exception as e:
            print(f"  Error in _is_valid_quadrilateral: {e}")
            return False
    
    def _validate_corners(self, corners, img_shape) -> bool:
        """Validate that corners are reasonable"""
        try:
            if corners is None or len(corners) != 4:
                print(f"  validate_corners: wrong corner count")
                return False
            
            # Ensure corners are numpy array
            corners = np.array(corners, dtype=np.float32).reshape(4, 2)
            
            height, width = img_shape[:2]
            print(f"  Image dimensions: {width}x{height}")
            
            # Check all corners are within image bounds (with margin)
            margin = 50
            for i, corner in enumerate(corners):
                x, y = corner
                if x < -margin or x > width + margin or y < -margin or y > height + margin:
                    print(f"  validate_corners: corner {i} ({x:.1f}, {y:.1f}) out of bounds")
                    return False
            
            print(f"  Corner positions: {corners.astype(int)}")
            
            # Check area is reasonable - need to reshape for contourArea
            corners_for_area = corners.reshape((-1, 1, 2)).astype(np.float32)
            area = abs(cv2.contourArea(corners_for_area))
            img_area = height * width
            area_ratio = area / img_area
            
            print(f"  Document area: {area:.0f} pixels ({area_ratio*100:.1f}% of image)")
            
            if area_ratio < 0.05:
                print(f"  validate_corners: area too small ({area_ratio*100:.1f}% < 5%)")
                return False
            
            if area_ratio > 0.98:
                print(f"  validate_corners: area too large ({area_ratio*100:.1f}% > 98%)")
                return False
            
            print(f"  ✓ All validations passed")
            return True
            
        except Exception as e:
            print(f"  Error in _validate_corners: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _transform_perspective(self, img, corners):
        """Transform the document to a flat, rectangular view"""
        try:
            # Ensure corners are properly formatted
            corners = np.array(corners, dtype=np.float32).reshape(4, 2)
            
            rect = self._order_corners(corners)
            (tl, tr, br, bl) = rect
            
            print(f"  Ordered corners: TL={tl}, TR={tr}, BR={br}, BL={bl}")
            
            # Calculate the width of the document
            widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
            widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
            maxWidth = max(int(widthA), int(widthB))
            
            # Calculate the height of the document
            heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
            heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
            maxHeight = max(int(heightA), int(heightB))
            
            # Ensure minimum dimensions
            maxWidth = max(maxWidth, 100)
            maxHeight = max(maxHeight, 100)
            
            print(f"  Output dimensions: {maxWidth}x{maxHeight}")
            
            # Define destination points
            dst = np.array([
                [0, 0],
                [maxWidth - 1, 0],
                [maxWidth - 1, maxHeight - 1],
                [0, maxHeight - 1]
            ], dtype="float32")
            
            # Calculate perspective transform matrix
            M = cv2.getPerspectiveTransform(rect, dst)
            
            # Apply the transformation
            warped = cv2.warpPerspective(img, M, (maxWidth, maxHeight))
            
            print(f"  ✓ Perspective transform successful")
            return warped
            
        except Exception as e:
            print(f"  ✗ Error in _transform_perspective: {e}")
            import traceback
            traceback.print_exc()
            return img
    
    def _order_corners(self, pts):
        """Order corners in consistent order: TL, TR, BR, BL"""
        # Ensure proper format
        pts = np.array(pts, dtype=np.float32).reshape(4, 2)
        
        rect = np.zeros((4, 2), dtype="float32")
        
        # Top-left has smallest sum (x+y)
        # Bottom-right has largest sum
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]  # top-left
        rect[2] = pts[np.argmax(s)]  # bottom-right
        
        # Top-right has smallest difference (y-x)
        # Bottom-left has largest difference
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]  # top-right
        rect[3] = pts[np.argmax(diff)]  # bottom-left
        
        return rect
    
    def _enhance_quality(self, img):
        """Enhance image quality for better PDF output"""
        try:
            # Convert to LAB color space for better processing
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            # Apply CLAHE to L channel
            clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
            l = clahe.apply(l)
            
            # Merge channels
            lab = cv2.merge([l, a, b])
            enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            
            # Convert to PIL for additional enhancement
            pil_img = Image.fromarray(cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB))
            
            # Increase contrast
            enhancer = ImageEnhance.Contrast(pil_img)
            pil_img = enhancer.enhance(1.5)
            
            # Increase sharpness
            sharpener = ImageEnhance.Sharpness(pil_img)
            pil_img = sharpener.enhance(2.0)
            
            # Slight brightness boost
            brightness = ImageEnhance.Brightness(pil_img)
            pil_img = brightness.enhance(1.1)
            
            # Convert back to OpenCV format
            return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            
        except Exception as e:
            print(f"Error in _enhance_quality: {e}")
            return img
    
    def _enhance_quality_aggressive(self, img):
        """Aggressive enhancement for images without perspective correction"""
        try:
            # Convert to LAB
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            # Apply CLAHE with stronger parameters
            clahe = cv2.createCLAHE(clipLimit=3.5, tileGridSize=(8, 8))
            l = clahe.apply(l)
            
            # Merge and convert back
            lab = cv2.merge([l, a, b])
            enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            
            # Denoise
            enhanced = cv2.fastNlMeansDenoisingColored(enhanced, None, 10, 10, 7, 21)
            
            # Convert to PIL for additional enhancement
            pil_img = Image.fromarray(cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB))
            
            # Strong contrast
            enhancer = ImageEnhance.Contrast(pil_img)
            pil_img = enhancer.enhance(1.8)
            
            # Strong sharpness
            sharpener = ImageEnhance.Sharpness(pil_img)
            pil_img = sharpener.enhance(2.2)
            
            # Brightness adjustment
            brightness = ImageEnhance.Brightness(pil_img)
            pil_img = brightness.enhance(1.15)
            
            # Convert back
            return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            
        except Exception as e:
            print(f"Error in _enhance_quality_aggressive: {e}")
            return img