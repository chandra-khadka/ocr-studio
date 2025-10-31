import io
import logging
import math
from typing import Dict, Tuple, Any, Optional

import cv2
import numpy as np
from PIL import Image, ImageEnhance

from backend.config import logger
from backend.utils.helper.preprocessing import create_temp_file


class DocumentAnalyzer:
    """Analyzes document quality and characteristics to determine optimal preprocessing"""

    def __init__(self):
        self.analysis_cache = {}

    def weighted_std(self, values, weights):
        values = np.asarray(values).flatten()
        weights = np.asarray(weights).flatten()
        average = np.average(values, weights=weights)
        variance = np.average((values - average) ** 2, weights=weights)
        return np.sqrt(variance)

    def analyze_document_quality(self, img_array: np.ndarray) -> Dict[str, Any]:
        """Comprehensive document quality analysis"""
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array.copy()

        analysis = {
            'image_stats': self._get_image_statistics(gray),
            'noise_level': self._assess_noise_level(gray),
            'contrast_quality': self._assess_contrast(gray),
            'brightness_level': self._assess_brightness(gray),
            'skew_angle': self._detect_skew(gray),
            'document_type': self._classify_document_type(gray),
            'blur_level': self._assess_blur(gray),
            'text_density': self._assess_text_density(gray)
        }

        # Generate quality score (0-100)
        analysis['quality_score'] = self._calculate_quality_score(analysis)

        # Generate preprocessing recommendations
        analysis['recommendations'] = self._generate_recommendations(analysis)

        return analysis

    @staticmethod
    def _get_image_statistics(gray: np.ndarray) -> Dict[str, float]:
        """Basic image statistics"""
        return {
            'mean': float(np.mean(gray)),
            'std': float(np.std(gray)),
            'min': float(np.min(gray)),
            'max': float(np.max(gray)),
            'median': float(np.median(gray))
        }

    @staticmethod
    def _assess_noise_level(gray: np.ndarray) -> Dict[str, Any]:
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        kernel = np.array([[-1, -1, -1], [-1, 8, -1], [-1, -1, -1]])
        noise_response = cv2.filter2D(gray, -1, kernel)
        noise_variance = np.var(noise_response)
        kernel_size = 5
        kernel = np.ones((kernel_size, kernel_size), np.float32) / (kernel_size * kernel_size)
        local_mean = cv2.filter2D(gray.astype(np.float32), -1, kernel)
        local_variance = cv2.filter2D((gray.astype(np.float32) - local_mean) ** 2, -1, kernel)
        avg_local_std = np.mean(np.sqrt(local_variance))
        if laplacian_var > 1000 and noise_variance > 50:
            noise_level = 'high'
        elif laplacian_var > 500 and noise_variance > 20:
            noise_level = 'medium'
        else:
            noise_level = 'low'
        return {
            'level': noise_level,
            'laplacian_variance': laplacian_var,
            'noise_variance': noise_variance,
            'local_std': avg_local_std
        }

    def _assess_contrast(self, gray: np.ndarray) -> Dict[str, Any]:
        rms_contrast = np.std(gray)
        max_val = float(np.max(gray))
        min_val = float(np.min(gray))
        michelson_contrast = (max_val - min_val) / (max_val + min_val) if (max_val + min_val) > 0 else 0
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
        values = np.arange(256)
        hist_spread = self.weighted_std(values, hist)
        if rms_contrast > 60 and michelson_contrast > 0.7:
            contrast_level = 'high'
        elif rms_contrast > 30 and michelson_contrast > 0.4:
            contrast_level = 'medium'
        else:
            contrast_level = 'low'

        return {
            'level': contrast_level,
            'rms_contrast': rms_contrast,
            'michelson_contrast': michelson_contrast,
            'histogram_spread': hist_spread
        }

    @staticmethod
    def _assess_brightness(gray: np.ndarray) -> Dict[str, Any]:
        """Assess brightness and lighting conditions"""
        mean_brightness = np.mean(gray)
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        dark_pixels = np.sum(hist[:50]) / gray.size
        bright_pixels = np.sum(hist[200:]) / gray.size
        if mean_brightness < 80:
            brightness_level = 'very_dark' if dark_pixels > 0.3 else 'dark'
        elif mean_brightness > 180:
            brightness_level = 'overexposed' if bright_pixels > 0.3 else 'bright'
        else:
            brightness_level = 'normal'
        return {
            'level': brightness_level,
            'mean_brightness': mean_brightness,
            'dark_pixels_ratio': dark_pixels,
            'bright_pixels_ratio': bright_pixels
        }

    @staticmethod
    def _detect_skew(gray: np.ndarray) -> Dict[str, Any]:
        """Detect document skew angle"""
        # Apply threshold to get binary image
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        angles = []
        try:
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=100, maxLineGap=10)
            if lines is not None:
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    if x2 - x1 != 0:
                        angle = math.atan2(y2 - y1, x2 - x1) * 180.0 / np.pi
                        if -45 <= angle <= 45:
                            angles.append(angle)
        except Exception:
            pass
        try:
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                if cv2.contourArea(contour) > 1000:
                    rect = cv2.minAreaRect(contour)
                    angle = rect[2]
                    if rect[1][0] < rect[1][1]:
                        angle += 90
                    if -45 <= angle <= 45:
                        angles.append(angle)
        except Exception:
            pass
        skew_angle = np.median(angles) if angles else 0
        abs_angle = abs(skew_angle)
        if abs_angle > 5:
            skew_level = 'high'
        elif abs_angle > 1:
            skew_level = 'medium'
        else:
            skew_level = 'low'
        return {
            'angle': skew_angle,
            'level': skew_level,
            'confidence': len(angles) / 10.0 if angles else 0
        }

    @staticmethod
    def _classify_document_type(gray: np.ndarray) -> Dict[str, Any]:
        """Classify document type based on visual characteristics"""
        # Analyze text vs image content
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        morph = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        text_like_contours = 0
        for contour in contours:
            area = cv2.contourArea(contour)
            if 10 < area < 5000:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h if h > 0 else 0
                if 0.1 < aspect_ratio < 10:
                    text_like_contours += 1
        if edge_density > 0.05 and text_like_contours > 50:
            doc_type = 'text_heavy'
        elif edge_density > 0.1:
            doc_type = 'mixed_content'
        else:
            doc_type = 'simple_text'
        return {
            'type': doc_type,
            'edge_density': edge_density,
            'text_regions': text_like_contours
        }

    @staticmethod
    def _assess_blur(gray: np.ndarray) -> Dict[str, Any]:
        """Assess image sharpness/blur"""
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        sobel_var = np.var(sobelx) + np.var(sobely)
        if laplacian_var > 800:
            blur_level = 'sharp'
        elif laplacian_var > 200:
            blur_level = 'moderate'
        else:
            blur_level = 'blurry'
        return {
            'level': blur_level,
            'laplacian_variance': laplacian_var,
            'sobel_variance': sobel_var
        }

    @staticmethod
    def _assess_text_density(gray: np.ndarray) -> Dict[str, Any]:
        """Assess text density and layout"""
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY_INV, 11, 2)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 1))
        connected = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        text_pixels = np.sum(connected > 0)
        total_pixels = connected.size
        text_density = text_pixels / total_pixels
        if text_density > 0.3:
            density_level = 'high'
        elif text_density > 0.1:
            density_level = 'medium'
        else:
            density_level = 'low'
        return {
            'level': density_level,
            'density_ratio': text_density
        }

    @staticmethod
    def _calculate_quality_score(analysis: Dict[str, Any]) -> float:
        score = 50  # Base
        score += {'high': 25, 'medium': 15, 'low': 0}.get(analysis['contrast_quality']['level'], 0)
        score += {'normal': 20, 'bright': 15, 'dark': 10, 'very_dark': 0, 'overexposed': 5}.get(
            analysis['brightness_level']['level'], 0)
        score += {'low': 0, 'medium': -5, 'high': -15}.get(analysis['noise_level']['level'], 0)
        score += {'sharp': 5, 'moderate': 0, 'blurry': -10}.get(analysis['blur_level']['level'], 0)
        score += {'low': 0, 'medium': -2, 'high': -5}.get(analysis['skew_angle']['level'], 0)
        return max(0, min(100, score))

    @staticmethod
    def _generate_recommendations(analysis: Dict[str, Any]) -> Dict[str, Any]:
        recommendations = {
            'deskew': {'enabled': False, 'priority': 0},
            'denoise': {'enabled': False, 'strength': 0, 'priority': 0},
            'contrast': {'enabled': False, 'adjustment': 0, 'priority': 0},
            'brightness': {'enabled': False, 'adjustment': 0, 'priority': 0},
            'sharpen': {'enabled': False, 'strength': 0, 'priority': 0},
            'threshold_method': 'adaptive'
        }
        if analysis['skew_angle']['level'] in ['medium', 'high']:
            recommendations['deskew'] = {'enabled': True,
                                         'priority': 3 if analysis['skew_angle']['level'] == 'high' else 2,
                                         'angle_threshold': 0.5, 'max_angle': 10}
        if analysis['noise_level']['level'] in ['medium', 'high']:
            strength = 3 if analysis['noise_level']['level'] == 'high' else 2
            recommendations['denoise'] = {'enabled': True, 'strength': strength,
                                          'priority': 2 if analysis['noise_level']['level'] == 'high' else 1}
        if analysis['contrast_quality']['level'] == 'low':
            recommendations['contrast'] = {'enabled': True, 'adjustment': 30, 'priority': 2}
        brightness_level = analysis['brightness_level']['level']
        if brightness_level in ['dark', 'very_dark']:
            adjustment = 40 if brightness_level == 'very_dark' else 20
            recommendations['brightness'] = {'enabled': True, 'adjustment': adjustment, 'priority': 2}
        elif brightness_level == 'overexposed':
            recommendations['brightness'] = {'enabled': True, 'adjustment': -20, 'priority': 1}
        if analysis['blur_level']['level'] == 'blurry':
            recommendations['sharpen'] = {'enabled': True, 'strength': 2, 'priority': 1}
        recommendations['threshold_method'] = 'adaptive' if analysis['document_type'][
                                                                'type'] == 'text_heavy' else 'otsu'
        return recommendations


class DynamicPreprocessor:
    """Dynamic preprocessing pipeline that adapts based on document analysis"""

    def __init__(self):
        self.analyzer = DocumentAnalyzer()
        self.logger = logging.getLogger("dynamic_preprocessor")

    def process_document(self, img_array: np.ndarray, force_analysis: bool = False) -> Tuple[
        np.ndarray, Dict[str, Any]]:
        """
        Process document with dynamic preprocessing based on automatic analysis

        Args:
            img_array: Input image as numpy array
            force_analysis: Force re-analysis even if cached

        Returns:
            Tuple of (processed_image, analysis_report)
        """
        # Analyze document quality
        self.logger.info("Analyzing document quality and characteristics...")
        analysis = self.analyzer.analyze_document_quality(img_array)
        self.logger.info(f"Document Quality Score: {analysis['quality_score']:.1f}/100")
        self.logger.info(f"Document Type: {analysis['document_type']['type']}")
        self.logger.info(f"Brightness: {analysis['brightness_level']['level']}")
        self.logger.info(f"Contrast: {analysis['contrast_quality']['level']}")
        self.logger.info(f"Noise Level: {analysis['noise_level']['level']}")
        self.logger.info(f"Skew Angle: {analysis['skew_angle']['angle']:.2f}°")
        processed_img = self._apply_adaptive_preprocessing(img_array, analysis['recommendations'])
        return processed_img, analysis

    def _apply_adaptive_preprocessing(self, img_array: np.ndarray, recommendations: Dict[str, Any]) -> np.ndarray:
        """Apply preprocessing steps based on recommendations with priority ordering"""

        # Convert to working format
        if len(img_array.shape) == 3:
            working_img = img_array.copy()
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array.copy()
            working_img = cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB)

        steps = []
        for step_name, config in recommendations.items():
            if isinstance(config, dict) and config.get('enabled', False):
                steps.append((config.get('priority', 0), step_name, config))
        steps.sort(key=lambda x: x[0], reverse=True)

        current_img = working_img.copy()
        current_gray = gray.copy()

        for priority, step_name, config in steps:
            self.logger.info(f"Applying {step_name} (priority: {priority})")
            if step_name == 'deskew':
                current_img, current_gray = self._apply_deskew(current_img, current_gray, config)
            elif step_name == 'denoise':
                current_img, current_gray = self._apply_denoise(current_img, current_gray, config)
            elif step_name == 'contrast':
                current_img, current_gray = self._apply_contrast(current_img, current_gray, config)
            elif step_name == 'brightness':
                current_img, current_gray = self._apply_brightness(current_img, current_gray, config)
            elif step_name == 'sharpen':
                current_img, current_gray = self._apply_sharpen(current_img, current_gray, config)

        return current_img

    def _apply_deskew(self, img: np.ndarray, gray: np.ndarray, config: Dict[str, Any]) -> Tuple[np.ndarray, np.ndarray]:
        """Apply deskewing with the detected angle"""
        try:
            angle = self.analyzer._detect_skew(gray)['angle']
            if abs(angle) > config.get('angle_threshold', 0.5):
                h, w = img.shape[:2]
                center = (w // 2, h // 2)
                rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
                abs_cos = abs(rotation_matrix[0, 0]);
                abs_sin = abs(rotation_matrix[0, 1])
                new_w = int(h * abs_sin + w * abs_cos)
                new_h = int(h * abs_cos + w * abs_sin)
                rotation_matrix[0, 2] += (new_w / 2) - center[0]
                rotation_matrix[1, 2] += (new_h / 2) - center[1]
                rotated_img = cv2.warpAffine(img, rotation_matrix, (new_w, new_h),
                                             flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                                             borderValue=(255, 255, 255))
                rotated_gray = cv2.warpAffine(gray, rotation_matrix, (new_w, new_h),
                                              flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=255)
                self.logger.info(f"Applied deskew correction: {angle:.2f}°")
                return rotated_img, rotated_gray
        except Exception as e:
            self.logger.error(f"Deskew failed: {e}")
        return img, gray

    def _apply_denoise(self, img: np.ndarray, gray: np.ndarray, config: Dict[str, Any]) -> Tuple[
        np.ndarray, np.ndarray]:
        try:
            strength = config.get('strength', 2)
            if len(img.shape) == 3:
                denoised_img = cv2.fastNlMeansDenoisingColored(img, None, strength, strength, 7, 21)
            else:
                denoised_img = cv2.fastNlMeansDenoising(img, None, strength, 7, 21)
            denoised_gray = cv2.fastNlMeansDenoising(gray, None, strength, 7, 21)
            self.logger.info(f"Applied denoising with strength: {strength}")
            return denoised_img, denoised_gray
        except Exception as e:
            self.logger.error(f"Denoising failed: {e}")
        return img, gray

    def _apply_contrast(self, img: np.ndarray, gray: np.ndarray, config: Dict[str, Any]) -> Tuple[
        np.ndarray, np.ndarray]:
        """Apply contrast adjustment"""
        try:
            adjustment = config.get('adjustment', 0)
            factor = 1 + (adjustment / 100.0)
            pil_img = Image.fromarray(img)
            enhancer = ImageEnhance.Contrast(pil_img)
            enhanced_img = enhancer.enhance(factor)
            result_img = np.array(enhanced_img)
            result_gray = cv2.cvtColor(result_img, cv2.COLOR_RGB2GRAY) if len(result_img.shape) == 3 else result_img
            self.logger.info(f"Applied contrast adjustment: {adjustment}%")
            return result_img, result_gray
        except Exception as e:
            self.logger.error(f"Contrast adjustment failed: {e}")
        return img, gray

    def _apply_brightness(self, img: np.ndarray, gray: np.ndarray, config: Dict[str, Any]) -> Tuple[
        np.ndarray, np.ndarray]:
        """Apply brightness adjustment"""
        try:
            adjustment = config.get('adjustment', 0)
            brightened_img = cv2.convertScaleAbs(img, alpha=1.0, beta=adjustment)
            brightened_gray = cv2.convertScaleAbs(gray, alpha=1.0, beta=adjustment)
            self.logger.info(f"Applied brightness adjustment: {adjustment}")
            return brightened_img, brightened_gray
        except Exception as e:
            self.logger.error(f"Brightness adjustment failed: {e}")
        return img, gray

    def _apply_sharpen(self, img: np.ndarray, gray: np.ndarray, config: Dict[str, Any]) -> Tuple[
        np.ndarray, np.ndarray]:
        """Apply sharpening filter"""
        try:
            strength = config.get('strength', 1)
            kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]], dtype=np.float32) * strength
            kernel[1, 1] = kernel[1, 1] - strength + 1
            sharpened_img = cv2.filter2D(img, -1, kernel)
            sharpened_gray = cv2.filter2D(gray, -1, kernel)
            sharpened_img = np.clip(sharpened_img, 0, 255).astype(np.uint8)
            sharpened_gray = np.clip(sharpened_gray, 0, 255).astype(np.uint8)
            self.logger.info(f"Applied sharpening with strength: {strength}")
            return sharpened_img, sharpened_gray
        except Exception as e:
            self.logger.error(f"Sharpening failed: {e}")
        return img, gray


def _derive_auto_preprocessing_options(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Turn analysis into reasonable override options for OCR readiness."""
    opts: Dict[str, Any] = {}
    q = float(analysis.get("quality_score", 50))
    noise = (analysis.get("noise_level", {}) or {}).get("level")
    if noise == "high":
        opts["denoise"] = {"strength": 7}
    elif noise == "medium":
        opts["denoise"] = {"strength": 4}
    elif noise == "low" and q < 45:
        opts["denoise"] = {"strength": 3}
    contrast = (analysis.get("contrast_quality", {}) or {}).get("level")
    if contrast == "low":
        opts["contrast"] = 30
    elif contrast == "medium" and q < 60:
        opts["contrast"] = 15
    brightness = (analysis.get("brightness_level", {}) or {}).get("level")
    if brightness == "very_dark":
        opts["brightness"] = 40
    elif brightness == "dark":
        opts["brightness"] = 20
    elif brightness == "overexposed":
        opts["brightness"] = -20
    blur = (analysis.get("blur_level", {}) or {}).get("level")
    if blur == "blurry" and q < 65:
        opts["sharpen"] = 1
    doc_type = (analysis.get("document_type", {}) or {}).get("type")
    if doc_type in ("simple_text", "text_heavy") and brightness != "overexposed":
        opts["grayscale"] = True
    return opts


def _merge_preprocessing_options(auto_opts: Dict[str, Any], user_opts: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Shallow merge; one-level deep for dict values. User overrides win."""
    if not user_opts:
        return dict(auto_opts)
    merged = dict(auto_opts)
    for k, v in user_opts.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            m = dict(merged[k])
            m.update(v)
            merged[k] = m
        else:
            merged[k] = v
    return merged


def _apply_user_overrides(processed_img, preprocessing_options, analysis):
    """
    Apply user-specified overrides while maintaining intelligent processing.
    Supported options:
      - grayscale: bool
      - denoise: bool | int | {"strength": int, "template": int, "search": int}
      - contrast: int        (percent)
      - brightness: int      (additive beta)
      - sharpen: int         (1..3)
    """
    if len(processed_img.shape) == 3:
        working_img = processed_img.copy()
    else:
        working_img = cv2.cvtColor(processed_img, cv2.COLOR_GRAY2RGB)

    opts = preprocessing_options or {}

    if opts.get("grayscale", False):
        if len(working_img.shape) == 3:
            working_img = cv2.cvtColor(working_img, cv2.COLOR_RGB2GRAY)
            logger.info("Applied user-requested grayscale conversion")

    denoise_opt = opts.get("denoise", False)
    if denoise_opt:
        try:
            if isinstance(denoise_opt, bool):
                strength, template, search = 3, 7, 21
            elif isinstance(denoise_opt, int):
                strength, template, search = max(1, min(15, denoise_opt)), 7, 21
            elif isinstance(denoise_opt, dict):
                strength = max(1, min(15, int(denoise_opt.get("strength", 3))))
                template = int(denoise_opt.get("template", 7))
                search = int(denoise_opt.get("search", 21))
            else:
                strength, template, search = 3, 7, 21

            if len(working_img.shape) == 3:
                working_img = cv2.fastNlMeansDenoisingColored(working_img, None, strength, strength, template, search)
            else:
                working_img = cv2.fastNlMeansDenoising(working_img, None, strength, template, search)
            logger.info(f"Applied user-requested denoising (h={strength}, template={template}, search={search})")
        except Exception as e:
            logger.error(f"User denoising failed: {e}")

    contrast_value = int(opts.get("contrast", 0) or 0)
    if contrast_value != 0:
        try:
            if len(working_img.shape) == 2:
                pil_img = Image.fromarray(cv2.cvtColor(working_img, cv2.COLOR_GRAY2RGB))
            else:
                pil_img = Image.fromarray(working_img)
            contrast_factor = 1 + (contrast_value / 100.0)
            enhancer = ImageEnhance.Contrast(pil_img)
            enhanced_img = enhancer.enhance(contrast_factor)
            working_img = np.array(enhanced_img)
            logger.info(f"Applied user contrast adjustment: {contrast_value}%")
        except Exception as e:
            logger.error(f"User contrast adjustment failed: {e}")

    brightness_value = int(opts.get("brightness", 0) or 0)
    if brightness_value != 0:
        try:
            working_img = cv2.convertScaleAbs(working_img, alpha=1.0, beta=brightness_value)
            logger.info(f"Applied user brightness adjustment: {brightness_value}")
        except Exception as e:
            logger.error(f"User brightness adjustment failed: {e}")

    sharpen_value = int(opts.get("sharpen", 0) or 0)
    if sharpen_value > 0:
        try:
            kernel = np.array([[-1, -1, -1],
                               [-1, 9, -1],
                               [-1, -1, -1]], dtype=np.float32)
            kernel *= sharpen_value
            kernel[1, 1] = kernel[1, 1] - sharpen_value + 1
            working_img = cv2.filter2D(working_img, -1, kernel)
            working_img = np.clip(working_img, 0, 255).astype(np.uint8)
            logger.info(f"Applied user sharpening with strength: {sharpen_value}")
        except Exception as e:
            logger.error(f"User sharpening failed: {e}")

    return working_img


def dynamic_preprocess_image(image_bytes, preprocessing_options=None):
    """
    Enhanced preprocessing with automatic quality detection and auto-tuned overrides.
    User options (if provided) override auto picks.
    """
    import time

    start_time = time.time()

    image = Image.open(io.BytesIO(image_bytes))
    original_mode = image.mode

    if image.mode == 'RGBA':
        background = Image.new('RGB', image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[3])
        image = background
        logger.info("Converted RGBA to RGB")
    elif image.mode not in ('RGB', 'L'):
        image = image.convert('RGB')
        logger.info(f"Converted {original_mode} to RGB")

    img_array = np.array(image)

    preprocessor = DynamicPreprocessor()
    processed_img, analysis = preprocessor.process_document(img_array)

    auto_opts = _derive_auto_preprocessing_options(analysis)
    final_opts = _merge_preprocessing_options(auto_opts, preprocessing_options)

    if final_opts:
        processed_img = _apply_user_overrides(processed_img, final_opts, analysis)

    if len(processed_img.shape) == 2:
        processed_image = Image.fromarray(cv2.cvtColor(processed_img, cv2.COLOR_GRAY2RGB))
    else:
        processed_image = Image.fromarray(processed_img)

    byte_io = io.BytesIO()
    if processed_image.mode not in ('RGB', 'L'):
        processed_image = processed_image.convert('RGB')
    processed_image.save(byte_io, format='JPEG', quality=92, optimize=True)
    byte_io.seek(0)

    processing_time = (time.time() - start_time) * 1000  # ms
    report = {
        'quality_score': analysis['quality_score'],
        'document_type': analysis['document_type']['type'],
        'brightness_level': analysis['brightness_level']['level'],
        'contrast_level': analysis['contrast_quality']['level'],
        'noise_level': analysis['noise_level']['level'],
        'skew_angle': analysis['skew_angle']['angle'],
        'blur_level': analysis['blur_level']['level'],
        'processing_applied': [k for k, v in analysis['recommendations'].items()
                               if isinstance(v, dict) and v.get('enabled', False)],
        'original_size_kb': len(image_bytes) / 1024,
        'processed_size_kb': len(byte_io.getvalue()) / 1024,
        'processing_time_ms': processing_time,
        'auto_preprocessing_options': auto_opts,
        'final_preprocessing_options': final_opts,
    }

    logger.info("Dynamic preprocessing complete:")
    logger.info(f"  Quality Score: {report['quality_score']:.1f}/100")
    logger.info(f"  Auto opts: {auto_opts}")
    if preprocessing_options:
        logger.info(f"  User opts: {preprocessing_options}")
    logger.info(f"  Final opts: {final_opts}")

    return byte_io.getvalue(), report


def apply_dynamic_preprocessing_to_file(file_bytes, file_ext, preprocessing_options, temp_file_paths):
    """Apply dynamic preprocessing for images; pass-through for non-images."""
    if file_ext.lower() in ['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp', '.webp']:
        logger.info(f"Applying dynamic preprocessing to {file_ext} file")
        processed_bytes, report = dynamic_preprocess_image(file_bytes, preprocessing_options)
        temp_path = create_temp_file(processed_bytes, file_ext, temp_file_paths)
        logger.info(f"Dynamic preprocessing applied with quality score: {report['quality_score']:.1f}/100")
        return temp_path, report
    else:
        logger.info(f"Non-image file ({file_ext}), using original file")
        temp_path = create_temp_file(file_bytes, file_ext, temp_file_paths)
        return temp_path, {"processing_applied": [], "quality_score": None}


DOCUMENT_SCENARIOS = {
    "high_quality_scan": {"description": "Clean, high-resolution scanned documents",
                          "typical_quality_score": 80, "common_issues": ["minimal_skew", "slight_noise"],
                          "processing_priority": ["deskew", "light_denoise"]},
    "mobile_photo": {"description": "Documents photographed with mobile devices",
                     "typical_quality_score": 60,
                     "common_issues": ["perspective_distortion", "lighting_issues", "motion_blur"],
                     "processing_priority": ["deskew", "brightness", "contrast", "denoise"]},
    "old_document": {"description": "Aged or degraded documents",
                     "typical_quality_score": 40, "common_issues": ["yellowing", "stains", "noise", "low_contrast"],
                     "processing_priority": ["contrast", "denoise", "brightness", "threshold_optimization"]},
    "low_light_photo": {"description": "Documents photographed in poor lighting",
                        "typical_quality_score": 35, "common_issues": ["darkness", "noise", "blur"],
                        "processing_priority": ["brightness", "denoise", "contrast", "sharpen"]},
    "newspaper": {"description": "Newspaper or thin paper with show-through",
                  "typical_quality_score": 50, "common_issues": ["bleed_through", "low_contrast"],
                  "processing_priority": ["contrast", "adaptive_threshold", "morphology"]},
    "handwritten": {"description": "Handwritten documents with ink variations",
                    "typical_quality_score": 45,
                    "common_issues": ["ink_variation", "paper_texture", "stroke_thickness"],
                    "processing_priority": ["adaptive_threshold", "morphology", "contrast"]}
}


def assess_document_quality(image_bytes):
    """Standalone quality assessment without processing."""
    image = Image.open(io.BytesIO(image_bytes))
    if image.mode == 'RGBA':
        background = Image.new('RGB', image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[3])
        image = background
    elif image.mode not in ('RGB', 'L'):
        image = image.convert('RGB')
    img_array = np.array(image)
    analyzer = DocumentAnalyzer()
    analysis = analyzer.analyze_document_quality(img_array)
    return {
        'quality_score': analysis['quality_score'],
        'recommendations': analysis['recommendations'],
        'detailed_analysis': {
            'brightness': analysis['brightness_level'],
            'contrast': analysis['contrast_quality'],
            'noise': analysis['noise_level'],
            'skew': analysis['skew_angle'],
            'document_type': analysis['document_type'],
            'blur': analysis['blur_level']
        }
    }
