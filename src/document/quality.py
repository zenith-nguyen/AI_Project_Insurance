"""Explainable OCR-readability triage for printed and possibly handwritten pages.

This module intentionally does not claim to be a handwriting classifier.  It
uses OCR evidence to decide whether automatic extraction is safe enough to
show as a suggestion or whether the page needs a human/manual route.
"""
from __future__ import annotations

from statistics import fmean
from typing import Iterable

from .schema import OCRToken


def assess_document_readability(tokens: Iterable[OCRToken]) -> dict:
    rows = list(tokens)
    if not rows:
        return {
            "state": "no_text",
            "label": "Không đọc được chữ",
            "human_review_required": True,
            "handwriting_model_active": False,
            "mean_ocr_confidence": 0.0,
            "low_confidence_ratio": 1.0,
            "short_token_ratio": 1.0,
            "token_count": 0,
            "reasons": ["OCR không tìm thấy vùng chữ nào trên trang."],
            "recommended_action": "Kiểm tra ảnh gốc, xoay/cắt lại hoặc chuyển người duyệt nhập tay.",
            "limitations": ["Không thể phân biệt trang trắng, ảnh kém chất lượng và chữ viết tay chỉ từ kết quả rỗng."],
        }

    confidences = [float(row.confidence) for row in rows]
    low_ratio = sum(value < 0.72 for value in confidences) / len(confidences)
    short_ratio = sum(len("".join(char for char in row.text if char.isalnum())) <= 2 for row in rows) / len(rows)
    mean_confidence = fmean(confidences)
    readable_characters = sum(sum(char.isalnum() for char in row.text) for row in rows)

    reasons: list[str] = []
    if mean_confidence < 0.70:
        reasons.append("Độ tin cậy OCR trung bình thấp.")
    if low_ratio >= 0.45:
        reasons.append("Nhiều vùng chữ có độ tin cậy thấp.")
    if short_ratio >= 0.55:
        reasons.append("OCR tạo nhiều mảnh chữ rất ngắn, thường gặp khi chữ khó đọc hoặc bố cục nhiễu.")
    if readable_characters < 8:
        reasons.append("Trang có quá ít ký tự đọc được để trích xuất trường ổn định.")

    if mean_confidence < 0.70 or low_ratio >= 0.45 or readable_characters < 8:
        state = "handwriting_or_low_quality_review"
        label = "Có thể là chữ viết tay hoặc ảnh khó đọc"
        action = "Đối chiếu bản gốc; nhập tay trường quan trọng hoặc chạy model chữ viết tay đã được kiểm định khi có."
        review = True
    elif mean_confidence < 0.82 or low_ratio >= 0.20 or short_ratio >= 0.55:
        state = "mixed_or_uncertain"
        label = "Có phần chữ chưa chắc chắn"
        action = "Xác nhận ngày, số tiền, biển số và các trường có confidence thấp trước khi lưu quyết định."
        review = True
        if not reasons:
            reasons.append("Kết quả OCR chưa đạt ngưỡng tin cậy cho xử lý không cần xác nhận.")
    else:
        state = "printed_likely"
        label = "Chữ in có thể đọc được"
        action = "Dùng kết quả làm gợi ý và vẫn đối chiếu các trường ảnh hưởng quyết định bồi thường."
        review = False
        reasons.append("Độ tin cậy OCR và độ dài văn bản đạt ngưỡng kỹ thuật hiện tại.")

    return {
        "state": state,
        "label": label,
        "human_review_required": review,
        "handwriting_model_active": False,
        "mean_ocr_confidence": round(mean_confidence, 4),
        "low_confidence_ratio": round(low_ratio, 4),
        "short_token_ratio": round(short_ratio, 4),
        "token_count": len(rows),
        "readable_character_count": readable_characters,
        "reasons": reasons,
        "recommended_action": action,
        "limitations": [
            "Đây là bộ định tuyến theo độ đọc được, không phải kết luận chắc chắn tài liệu có chữ viết tay.",
            "PaddleOCR/LayoutLMv3 hiện chưa được validation riêng trên chữ viết tay bảo hiểm Việt Nam.",
        ],
    }
