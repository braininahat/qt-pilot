"""Draw numbered badges on QImage for annotated screenshots."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter


def annotate_image(
    image: QImage,
    ref_info: list[tuple[str, str, str | None, QRectF]],
) -> QImage:
    """Overlay numbered badges on interactive elements.

    Args:
        image: The screenshot QImage (will be copied, not mutated).
        ref_info: List of (ref, display_cls, text, scene_rect) tuples.

    Returns:
        A new QImage with badge overlays.
    """
    annotated = image.copy()
    painter = QPainter(annotated)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    badge_font = QFont("Inter", 8, QFont.Weight.Bold)
    # Fallback if Inter isn't available
    badge_font.setStyleHint(QFont.StyleHint.SansSerif)
    painter.setFont(badge_font)

    badge_color = QColor(124, 99, 225, 220)  # Purple
    text_color = QColor(255, 255, 255)        # White
    outline_color = QColor(255, 255, 255, 180)

    for i, (_ref, _cls, _text, rect) in enumerate(ref_info, 1):
        label = str(i)

        # Badge size adapts to digit count
        badge_w = max(18, 10 + len(label) * 7)
        badge_h = 16

        # Position: top-left corner of element, offset slightly inward
        bx = int(rect.x()) + 2
        by = int(rect.y()) + 2

        # Clamp to image bounds
        bx = max(0, min(bx, annotated.width() - badge_w))
        by = max(0, min(by, annotated.height() - badge_h))

        badge_rect = QRectF(bx, by, badge_w, badge_h)

        # White outline for contrast
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(outline_color)
        painter.drawRoundedRect(badge_rect.adjusted(-1, -1, 1, 1), 4, 4)

        # Purple badge
        painter.setBrush(badge_color)
        painter.drawRoundedRect(badge_rect, 3, 3)

        # White number
        painter.setPen(text_color)
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, label)

    painter.end()
    return annotated
