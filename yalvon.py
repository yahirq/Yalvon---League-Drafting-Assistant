# Python
import sys
import os
import util
import traceback
import random
import pandas as pd
from catboost import CatBoostClassifier, Pool
from PyQt5.QtGui import QPixmap, QFont, QColor, QPainter
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QObject, QThread
from PyQt5.QtWidgets import *
from draft_sim.manager.mainmanager import MainManager
from google import genai
from dotenv import load_dotenv
from AI.GeminiManager import GeminiManager
from AI.DraftService import DraftService
from AI.DataManager import DataManager

import os, sys

def resource_path(relative_path:str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, relative_path)

model_path = resource_path("cbmodels/CatModel.cbm")
csv_path = resource_path("csvdata/lolplayerdata.csv")
draftdata_path = resource_path("csvdata/draftdatalol.csv")
images_path = resource_path("images")

#todo have to restart for env var to apply
#todo api key is in, prompt suggestion doesnt do anything
load_dotenv()

# -----------------------------
# ChampionTile
# -----------------------------
class ChampionTile(QWidget):
    clicked = pyqtSignal(str)

    def __init__(self, champion_name: str, img_path: str, size: int = 90):
        super().__init__()
        self.champion_name = champion_name
        self.interactive = True
        self.img_path = img_path
        self.size = size
        self.selected = False
        self.banned = False
        self.picked = False
        self.delta_winrate = 0.0

        # Allow a bit of horizontal flexibility
        self.setMinimumWidth(size + 8)
        self.setMaximumWidth(size + 40)

        self.setStyleSheet("""
            QWidget#card {
                background-color: #262626;
                border: 1px solid #2f2f2f;
                border-radius: 10px;
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        card = QWidget(objectName="card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(6, 6, 6, 6)
        card_layout.setSpacing(6)

        # Image
        content_width = size - 12
        self.image_label = QLabel()
        self.image_label.setFixedSize(content_width, content_width)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #1f1f1f;
                border: 1px solid #333;
                border-radius: 6px;
            }
        """)
        card_layout.addWidget(self.image_label, 0, Qt.AlignHCenter)

        # Info pills
        pill_style = """
            QLabel {
                background-color: rgba(0, 0, 0, 0.65);
                color: #f7f7f7;
                font-size: 9px;
                font-weight: 600;
                border-radius: 6px;
                padding: 2px 6px;
                border: 1px solid rgba(255, 255, 255, 0.10);
            }
        """

        info_row = QHBoxLayout()
        info_row.setContentsMargins(0, 0, 0, 0)
        info_row.setSpacing(6)

        self.general_winrate_label = QLabel("")
        self.games_played_label = QLabel("")

        for lbl in (self.general_winrate_label, self.games_played_label):
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setFixedHeight(20)
            lbl.setStyleSheet(pill_style)
            lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            lbl.setWordWrap(False)

        self.general_winrate_label.setToolTip("Winrate percentage")
        self.games_played_label.setToolTip("Games played")

        info_row.addWidget(self.general_winrate_label, 6)
        info_row.addWidget(self.games_played_label, 4)
        card_layout.addLayout(info_row)

        # Delta
        self.delta_label = QLabel("")
        self.delta_label.setAlignment(Qt.AlignCenter)
        self.delta_label.setFixedHeight(20)
        self.delta_label.setMinimumWidth(48)
        self.delta_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 0.65);
                color: #f7f7f7;
                font-size: 10px;
                font-weight: 700;
                border-radius: 6px;
                padding: 2px 6px;
            }
        """)
        card_layout.addWidget(self.delta_label, 0, Qt.AlignHCenter)

        root.addWidget(card, 0, Qt.AlignHCenter)

        self.load_image()
        self.update_delta_display()
        self.update_style()
        self.set_info_texts("WR --", "Next --")

    def set_interactive(self, enabled: bool):
        self.interactive = enabled
        self.setCursor(Qt.PointingHandCursor if enabled else Qt.ArrowCursor)
        
    
    def set_info_texts(self, left_text: str, right_text: str):
        self.general_winrate_label.setText(left_text)
        self.games_played_label.setText(right_text)

    def load_image(self):
        pixmap = QPixmap(self.img_path)
        if not pixmap.isNull():
            inset = 6
            scaled_pixmap = pixmap.scaled(
                self.image_label.width() - inset,
                self.image_label.height() - inset,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
        else:
            self.image_label.setText(util.name_cleanup(self.champion_name))

    def update_delta_display(self):
        if self.banned or self.picked or abs(self.delta_winrate) < 0.01:
            self.delta_label.setText("-")
            self.delta_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(0, 0, 0, 0.65);
                    color: #f7f7f7;
                    font-size: 10px;
                    font-weight: 700;
                    border-radius: 6px;
                    padding: 2px 6px;
                    border: 1px solid rgba(255, 255, 255, 0.10);
                }
            """)
            self.delta_label.show()
        else:
            text = f"{self.delta_winrate:+.1f}%"
            color = "#4EDF4E" if self.delta_winrate > 0 else "#CE4242"
            self.delta_label.setText(text)
            self.delta_label.setStyleSheet(f"""
                QLabel {{
                    background-color: rgba(0, 0, 0, 0.65);
                    color: {color};
                    font-size: 10px;
                    font-weight: 700;
                    border-radius: 6px;
                    padding: 2px 6px;
                    border: 1px solid {color};
                }}
            """)
            self.delta_label.show()

    def set_delta_winrate(self, delta: float):
        self.delta_winrate = delta
        self.update_delta_display()
        self.update_style()

    def set_general_wr_colored(self, wr_text: str):
        color = "#f7f7f7"
        try:
            txt = wr_text.replace("WR", "").replace("%", "").strip()
            if txt not in ("--", ""):
                val = float(txt)
                color = "#4EDF4E" if val >= 50.0 else "#CE4242"
        except Exception:
            pass

        self.general_winrate_label.setText(wr_text)
        self.general_winrate_label.setToolTip(f"Winrate percentage: {wr_text}")
        self.general_winrate_label.setStyleSheet(f"""
            QLabel {{
                background-color: rgba(0, 0, 0, 0.65);
                color: {color};
                font-size: 9px;
                font-weight: 600;
                border-radius: 6px;
                padding: 2px 6px;
                border: 1px solid rgba(255, 255, 255, 0.10);
            }}
        """)

    def update_style(self):
        if self.banned:
            self.image_label.setStyleSheet("""
                QLabel {
                    background-color: #1f1f1f;
                    border: 2px solid #ff4d4d;
                    border-radius: 6px;
                }
            """)
        elif self.picked:
            self.image_label.setStyleSheet("""
                QLabel {
                    background-color: #1f1f1f;
                    border: 2px solid #4dff6a;
                    border-radius: 6px;
                }
            """)
        elif self.selected:
            self.image_label.setStyleSheet("""
                QLabel {
                    background-color: #1f1f1f;
                    border: 2px solid #5a7dff;
                    border-radius: 6px;
                }
            """)
        else:
            border_color = "#3a3a3a"
            if self.delta_winrate > 0.0:
                border_color = "#3fae52"
            elif self.delta_winrate < 0.0:
                border_color = "#c24545"
            self.image_label.setStyleSheet(f"""
                QLabel {{
                    background-color: #1f1f1f;
                    border: 1px solid {border_color};
                    border-radius: 6px;
                }}
                QLabel:hover {{
                    border: 1px solid #7a7a7a;
                }}
            """)
        self.update_delta_display()

    def set_selected(self, selected: bool):
        self.selected = selected
        self.update_style()

    def set_banned(self, banned: bool):
        self.banned = banned
        self.update_style()

    def set_picked(self, picked: bool):
        self.picked = picked
        self.update_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and getattr(self,"interactive", True):
            self.clicked.emit(self.champion_name)


# -----------------------------
# DraftSlot
# -----------------------------
class DraftSlot(QLabel):
    def __init__(self, slot_type="ban", team="blue", slot_index=1):
        super().__init__()
        self.slot_type = slot_type
        self.team = team
        self.slot_index = slot_index
        self.champion = None

        self.setFixedSize(64, 64)
        self.setAlignment(Qt.AlignCenter)

        border_color = "#3b82f6" if self.team == "blue" else "#ef4444"

        self.setStyleSheet(f"""
            QLabel {{
                background-color: #1f1f1f;
                border: 2px dashed {border_color};
                border-radius: 8px;
                font-size: 10px;
                color: #888;
                padding: 4px;
            }}
        """)
        self.setText(f"{'Ban' if slot_type == 'ban' else 'Pick'} {self.slot_index}")

    def set_champion(self, champion_name, img_path):
        self.champion = champion_name
        pixmap = QPixmap(img_path)
        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(62, 62, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.setPixmap(scaled_pixmap)
            self.setText("")

    def clear_champion(self):
        self.champion = None
        self.clear()
        self.setText(f"{'Ban' if self.slot_type == 'ban' else 'Pick'} {self.slot_index}")


# -----------------------------
# AI Worker (calls Gemini)
# -----------------------------
class AIWorker(QObject):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, service, task_type, **kwargs):
        super().__init__()
        self.service = service
        self.task_type = task_type
        self.kwargs = kwargs

    def run(self):
        try:
            if self.task_type == "status":
                result = self.service.send_status_update(**self.kwargs)
            elif self.task_type == "recommend":
                result = self.service.get_recommendations(**self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


# -----------------------------
# PlayerCard (Pick box without player name)
# -----------------------------
class PlayerCard(QWidget):
    def __init__(self, player_name, team="blue"):
        super().__init__()
        self.player_name = player_name
        self.team = team
        self.champion = None

        root = QHBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(0)
        self.setStyleSheet("""
            QWidget {
                background-color: #262626;
                border: 1px solid #303030;
                border-radius: 8px;
            }
        """)

        # Centered slot
        slot_wrap = QHBoxLayout()
        slot_wrap.setContentsMargins(0, 0, 0, 0)
        slot_wrap.setSpacing(0)

        self.champion_slot = QLabel("Lock in")
        self.champion_slot.setAlignment(Qt.AlignCenter)
        self.champion_slot.setFixedSize(64, 64)
        self.champion_slot.setStyleSheet("""
            QLabel {
                border: 2px dashed #5a5a5a;
                border-radius: 8px;
                background-color: #1f1f1f;
                font-size: 10px;
                color: #999;
            }
        """)

        # Add expanding spacers on both sides to truly center
        slot_wrap.addStretch(1)
        slot_wrap.addWidget(self.champion_slot, 0, Qt.AlignCenter)
        slot_wrap.addStretch(1)

        root.addLayout(slot_wrap)

    def set_champion(self, champion_name, image_path):
        self.champion = champion_name
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.champion_slot.setPixmap(scaled)
            self.champion_slot.setStyleSheet("border: 2px solid #34d399; border-radius: 8px;")


# -----------------------------
# ProbabilityBar
# -----------------------------
class ProbabilityBar(QWidget):
    def __init__(self):
        super().__init__()
        self.blue_prob = 50.0
        self.red_prob = 50.0
        self.setMinimumHeight(32)
        self.setMinimumWidth(600)

    def set_values(self, blue_prob, red_prob):
        total = blue_prob + red_prob
        if total != 100:
            blue_prob = (blue_prob / total) * 100
            red_prob = (red_prob / total) * 100
        self.blue_prob = blue_prob
        self.red_prob = red_prob
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()

        painter.setBrush(QColor(38, 38, 38))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, w, h, 10, 10)

        blue_w = int((self.blue_prob / 100) * w)
        red_w = w - blue_w

        painter.setBrush(QColor(59, 130, 246))
        painter.drawRoundedRect(0, 0, blue_w, h, 10, 10)
        painter.setBrush(QColor(239, 68, 68))
        painter.drawRoundedRect(blue_w, 0, red_w, h, 10, 10)

        painter.setPen(QColor(240, 240, 240))
        painter.setFont(QFont('Segoe UI', 12, QFont.DemiBold))
        painter.drawText(0, 0, blue_w, h, Qt.AlignCenter, f"Blue {self.blue_prob:.1f}%")
        painter.drawText(blue_w, 0, red_w, h, Qt.AlignCenter, f"Red {self.red_prob:.1f}%")


# -----------------------------
# Suggestions Panel
# -----------------------------
class SuggestionItem(QWidget):
    def __init__(
        self,
        champ_name: str,
        img_path: str,
        reason: str = "",
        possible_synergies=None,
        possible_counters=None,
    ):
        super().__init__()

        possible_synergies = possible_synergies or []
        possible_counters = possible_counters or []

        self.setStyleSheet("""
            QWidget#itemRoot {
                background-color: #262626;
                border: 1px solid #2f2f2f;
                border-radius: 8px;
            }
            QLabel#champName {
                color: #eaeaea;
                font-weight: 700;
                font-size: 12px;
            }
            QLabel#reason {
                color: #cfcfcf;
                font-size: 11px;
            }
            QLabel.sectionTitle {
                color: #c9c9c9;
                font-size: 10px;
                font-weight: 700;
                margin-top: 2px;
            }
        """)

        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(10)

        box = QWidget(objectName="itemRoot")
        box_layout = QHBoxLayout(box)
        box_layout.setContentsMargins(8, 8, 8, 8)
        box_layout.setSpacing(10)

        icon_label = QLabel()
        icon_label.setFixedSize(48, 48)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("background:#1f1f1f; border:1px solid #3a3a3a; border-radius:6px;")
        pix = QPixmap(img_path)
        if not pix.isNull():
            pix = pix.scaled(46, 46, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            icon_label.setPixmap(pix)
        else:
            icon_label.setText("No img")

        text_col = QVBoxLayout()
        text_col.setSpacing(4)

        name_lbl = QLabel(champ_name, objectName="champName")
        name_lbl.setWordWrap(True)
        reason_lbl = QLabel(reason or "—", objectName="reason")
        reason_lbl.setWordWrap(True)

        text_col.addWidget(name_lbl)
        text_col.addWidget(reason_lbl)

        def chips_row(title_text, items, accent="#a1a1aa"):
            if not items:
                return None
            wrap = QVBoxLayout()
            wrap.setContentsMargins(0, 0, 0, 0)
            wrap.setSpacing(4)

            title = QLabel(title_text)
            title.setObjectName("sectionTitle")
            title.setStyleSheet(f"color: {accent};")
            wrap.addWidget(title)

            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(6)

            for it in items[:10]:
                chip = QWidget()
                cl = QHBoxLayout(chip)
                cl.setContentsMargins(4, 2, 4, 2)
                cl.setSpacing(4)

                small = QLabel()
                small.setFixedSize(16, 16)
                sp = QPixmap(it.get("path", "") or "")
                if not sp.isNull():
                    sp = sp.scaled(16, 16, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    small.setPixmap(sp)
                else:
                    small.setText("•")
                    small.setStyleSheet("color:#aaa;")

                txt = QLabel(it.get("name", ""))
                txt.setStyleSheet("font-size:10px; color:#ddd;")

                cl.addWidget(small, 0)
                cl.addWidget(txt, 0)

                chip.setStyleSheet("QWidget { background: rgba(0,0,0,0.35); border:1px solid #3a3a3a; border-radius:6px; }")
                row.addWidget(chip, 0)

            row.addStretch()
            wrap.addLayout(row)
            return wrap

        sec_synergy = chips_row("Possible synergies", possible_synergies, "#16a34a")
        sec_counter = chips_row("Possible counters", possible_counters, "#dc2626")

        for sec in (sec_synergy, sec_counter):
            if sec:
                text_col.addLayout(sec)

        box_layout.addWidget(icon_label)
        box_layout.addLayout(text_col)
        root.addWidget(box)

    @staticmethod
    def spacer(height: int = 6) -> QWidget:
        s = QWidget()
        s.setFixedHeight(height)
        return s

class SuggestionsPanel(QWidget):
    def __init__(self, parent=None, on_prompt_suggestion=None, main=None):
        super().__init__(parent)
        self.on_prompt_suggestion = on_prompt_suggestion
        self.main = main
        self.setStyleSheet("""
            QWidget#suggestionsRoot {
                background-color: #242424;
                border: 1px solid #2c2c2c;
                border-radius: 10px;
            }
            QLabel#title {
                font-size: 13px;
                font-weight: 700;
                color: #e2e2e2;
            }
            QPushButton#promptBtn {
                background-color: #2e2e2e;
                color: #eaeaea;
                padding: 6px 10px;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                font-weight: 600;
            }
            QPushButton#promptBtn:hover { background-color: #373737; }
            QPushButton#promptBtn:pressed { background-color: #2a2a2a; }
        """)

        root = QVBoxLayout(self, objectName="suggestionsRoot")
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        header = QHBoxLayout()
        self.title = QLabel("Suggestions", objectName="title")

        self.prompt_btn = QPushButton("Prompt Suggestion", objectName="promptBtn")
        self.prompt_btn.setCursor(Qt.PointingHandCursor)
        self.prompt_btn.clicked.connect(self._on_prompt_click)

        header.addWidget(self.title)
        header.addStretch()
        header.addWidget(self.prompt_btn)
        root.addLayout(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        viewport = QWidget()
        self.vlayout = QVBoxLayout(viewport)
        self.vlayout.setContentsMargins(6, 6, 6, 6)
        self.vlayout.setSpacing(6)
        self.vlayout.addStretch()

        self.scroll.setWidget(viewport)
        root.addWidget(self.scroll)

    def set_context(self, current_turn: str):
        if not current_turn:
            self.title.setText("Suggestions")
            return
        side = "Blue" if "blue" in current_turn else "Red"
        action = "Ban" if "ban" in current_turn else "Pick"
        self.title.setText("Suggestions")

    def set_busy(self, busy: bool):
        self.prompt_btn.setDisabled(busy)

    def _on_prompt_click(self):
        self.set_busy(True)
        if callable(self.on_prompt_suggestion):
            self.on_prompt_suggestion(10)

    def clear_suggestions(self):
        while self.vlayout.count() > 1:
            item = self.vlayout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

    def _find_main_with_all_champions(self):
        obj = self
        while obj is not None:
            if hasattr(obj, "all_champions"):
                return obj
            obj = obj.parent()
        return None

    def _resolve_entry(self, name: str, data: dict):
        n = util.name_cleanup((name or "").strip())
        key = n.lower()
        entry = data.get(key)
        if entry is None:
            for k, v in data.items():
                if (k or "").strip().lower() == key:
                    entry = v
                    break
        if entry is None:
            for v in data.values():
                if v["name"].strip().lower() == n.strip().lower():
                    entry = v
                    break
        if entry:
            return {"name": entry["name"], "path": entry["path"]}
        return {"name": n, "path": ""}

    def add_suggestion(self, pick):
        owner = self.main or self._find_main_with_all_champions()
        data = getattr(owner, "all_champions", {}) if owner else {}
        if not isinstance(data, dict) or not data:
            item = SuggestionItem(
                champ_name=getattr(pick, "champion_name", "Unknown"),
                img_path="",
                reason=getattr(pick, "reasoning", ""),
            )
            self.vlayout.insertWidget(self.vlayout.count() - 1, item)
            return

        primary = self._resolve_entry(getattr(pick, "champion_name", ""), data)

        def resolve_list(names):
            out = []
            for nm in (names or []):
                out.append(self._resolve_entry(nm, data))
            return out

        item = SuggestionItem(
            champ_name=primary["name"],
            img_path=primary["path"],
            reason=getattr(pick, "reasoning", "") or "",
            possible_synergies=resolve_list(getattr(pick, "possible_synergies", [])),
            possible_counters=resolve_list(getattr(pick, "possible_counters", [])),
        )
        self.vlayout.insertWidget(self.vlayout.count() - 1, item)


# -----------------------------
# Predictions Panel (new)
# -----------------------------
class PredictionItem(QWidget):
    def __init__(self, champ_name: str, img_path: str, probability: float = 0.0, reasoning: str = ""):
        super().__init__()
        self.setStyleSheet("""
            QWidget#predItem {
                background-color: #262626;
                border: 1px solid #2f2f2f;
                border-radius: 8px;
            }
            QLabel#champ {
                color: #eaeaea;
                font-weight: 700;
                font-size: 12px;
            }
            QLabel#prob {
                color: #a7f3d0;
                font-weight: 700;
                font-size: 12px;
            }
            QLabel#reason {
                color: #cfcfcf;
                font-size: 11px;
            }
        """)
        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(10)

        card = QWidget(objectName="predItem")
        cl = QHBoxLayout(card)
        cl.setContentsMargins(8, 8, 8, 8)
        cl.setSpacing(10)

        icon = QLabel()
        icon.setFixedSize(40, 40)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("background:#1f1f1f; border:1px solid #3a3a3a; border-radius:6px;")
        pm = QPixmap(img_path)
        if not pm.isNull():
            pm = pm.scaled(38, 38, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            icon.setPixmap(pm)
        else:
            icon.setText("No img")

        textcol = QVBoxLayout()
        textcol.setSpacing(2)

        header = QHBoxLayout()
        name_lbl = QLabel(champ_name or "Unknown", objectName="champ")
        prob_lbl = QLabel(f"{probability:.1f}%", objectName="prob")
        header.addWidget(name_lbl, 1)
        header.addWidget(prob_lbl, 0, Qt.AlignRight)

        reason_lbl = QLabel(reasoning or "—", objectName="reason")
        reason_lbl.setWordWrap(True)

        textcol.addLayout(header)
        textcol.addWidget(reason_lbl)

        cl.addWidget(icon, 0)
        cl.addLayout(textcol, 1)
        root.addWidget(card)


class PredictionsPanel(QWidget):
    def __init__(self, parent=None, main=None):
        super().__init__(parent)
        self.main = main
        self.setStyleSheet("""
            QWidget#predRoot {
                background-color: #242424;
                border: 1px solid #2c2c2c;
                border-radius: 10px;
            }
            QLabel#title {
                font-size: 13px;
                font-weight: 700;
                color: #e2e2e2;
            }
        """)

        root = QVBoxLayout(self, objectName="predRoot")
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        header = QHBoxLayout()
        self.title = QLabel("Predictions", objectName="title")
        header.addWidget(self.title)
        header.addStretch()
        root.addLayout(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        vp = QWidget()
        self.vlayout = QVBoxLayout(vp)
        self.vlayout.setContentsMargins(6, 6, 6, 6)
        self.vlayout.setSpacing(6)
        self.vlayout.addStretch()
        self.scroll.setWidget(vp)

        root.addWidget(self.scroll)

    def set_context(self, next_turn: str):
        if not next_turn or next_turn == "draft_complete":
            self.title.setText("Predictions")
            return
        side = "Blue" if "blue" in next_turn else "Red"
        action = "Ban" if "ban" in next_turn else "Pick"
        self.title.setText(f"Predictions")


    def clear_predictions(self):
        while self.vlayout.count() > 1:
            it = self.vlayout.takeAt(0)
            w = it.widget()
            if w:
                w.setParent(None)

    def add_prediction(self, champ_name: str, probability: float, reasoning: str):
        owner = self.main or self._find_main_with_all_champions()
        data = getattr(owner, "all_champions", {}) if owner else {}
        name = champ_name or "Unknown"
        img_path = ""
        if isinstance(data, dict):
            key = util.name_cleanup(name).lower()
            if key in data:
                img_path = data[key]["path"]
            else:
                # Try loose match
                for k, v in data.items():
                    if v["name"].strip().lower() == name.strip().lower():
                        img_path = v["path"]
                        name = v["name"]
                        break

        item = PredictionItem(name, img_path, float(probability or 0.0) * (100.0 if probability <= 1.0 else 1.0), reasoning or "")
        self.vlayout.insertWidget(self.vlayout.count() - 1, item)

    def _find_main_with_all_champions(self):
        obj = self
        while obj is not None:
            if hasattr(obj, "all_champions"):
                return obj
            obj = obj.parent()
        return None


# -----------------------------
# TeamStatsWidget (Most picked champions with icons and WR)
# -----------------------------
class TeamStatsWidget(QWidget):
    def __init__(self, title_text: str, color: str, get_team_name_fn, get_top_picks_fn, all_champs_ref, get_top_wr_fn=None):
        super().__init__()
        self.title_text = title_text
        self.color = color
        self.get_team_name_fn = get_team_name_fn
        self.get_top_picks_fn = get_top_picks_fn
        self.get_top_wr_fn = get_top_wr_fn  # optional function to fetch highest winrate champions
        self.all_champs_ref = all_champs_ref

        self.setStyleSheet("""
            QWidget#root {
                background-color: #262626;
                border: 1px solid #303030;
                border-radius: 8px;
            }
            QLabel#sectionTitle {
                font-size: 12px;
                font-weight: 700;
                color: #e2e2e2;
            }
            QLabel#champText {
                color: #eaeaea;
                font-size: 11px;
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        box = QWidget(objectName="root")
        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(10, 8, 10, 8)
        box_layout.setSpacing(8)

        self.header = QLabel(self.title_text, objectName="sectionTitle")
        self.header.setAlignment(Qt.AlignCenter)
        self.header.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {self.color};")
        box_layout.addWidget(self.header)

        self.list_container = QVBoxLayout()
        self.list_container.setSpacing(6)
        self.list_container.setContentsMargins(0, 0, 0, 0)
        box_layout.addLayout(self.list_container)

        # Secondary list for Highest Winrate (optional)
        self.winrate_header = QLabel("Highest Winrate Champions", objectName="sectionTitle")
        self.winrate_header.setAlignment(Qt.AlignCenter)
        self.winrate_header.setStyleSheet("font-size: 12px; font-weight: 700; color: #e2e2e2;")
        self.winrate_header.hide()

        self.winrate_container = QVBoxLayout()
        self.winrate_container.setSpacing(6)
        self.winrate_container.setContentsMargins(0, 0, 0, 0)

        box_layout.addWidget(self.winrate_header)
        box_layout.addLayout(self.winrate_container)

        root.addWidget(box)

    def _make_row(self, champ_name: str, wr: float, games: int = None):
        row = QWidget()
        hl = QHBoxLayout(row)
        hl.setContentsMargins(6, 4, 6, 4)
        hl.setSpacing(8)

        icon = QLabel()
        icon.setFixedSize(24, 24)
        path = ""
        allc = self.all_champs_ref()
        key = champ_name.lower()
        if allc and key in allc:
            path = allc[key]["path"]
        pm = QPixmap(path)
        if not pm.isNull():
            pm = pm.scaled(24, 24, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            icon.setPixmap(pm)
        else:
            icon.setText("□")
            icon.setAlignment(Qt.AlignCenter)
            icon.setStyleSheet("color:#aaa; border:1px solid #3a3a3a; border-radius:4px; background:#1f1f1f;")

        wr_color = "#4EDF4E" if wr >= 50.0 else "#CE4242"
        txt = QLabel(f"{champ_name} — {wr:.1f}%")
        txt.setObjectName("champText")
        txt.setStyleSheet(f"color: {wr_color};")

        # Tooltip: show games played
        if games is not None:
            txt.setToolTip(f"Games played: {games}")

        hl.addWidget(icon, 0)
        hl.addWidget(txt, 1)
        return row

    def _clear_layout(self, layout: QVBoxLayout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

    def refresh(self):
        # Clear both sections
        self._clear_layout(self.list_container)
        self._clear_layout(self.winrate_container)
        self.winrate_header.hide()

        team_name = self.get_team_name_fn()
        if not team_name or "Team Players" in team_name:
            ph = QLabel("Select a team to show most-picked champions.")
            ph.setStyleSheet("color:#bdbdbd; font-size:11px;")
            ph.setWordWrap(True)
            self.list_container.addWidget(ph)
            return

        picks = []
        try:
            picks = self.get_top_picks_fn(team_name)
        except Exception:
            picks = []

        if not picks:
            ph = QLabel("No team-specific data available.")
            ph.setStyleSheet("color:#bdbdbd; font-size:11px;")
            ph.setWordWrap(True)
            self.list_container.addWidget(ph)
        else:
            for name, wr, _games in picks[:6]:
                self.list_container.addWidget(self._make_row(name, wr, _games))

        # Highest Winrate section (just below)
        if callable(self.get_top_wr_fn):
            try:
                top_wr = self.get_top_wr_fn(team_name)
            except Exception:
                top_wr = []
            if top_wr:
                self.winrate_header.show()
                for name, wr, games in top_wr[:6]:
                    self.winrate_container.addWidget(self._make_row(name, wr, games))


# -----------------------------
# ChatBox (bottom prompt)
# -----------------------------
class ChatBox(QWidget):
    def __init__(self, parent=None, on_send=None):
        super().__init__(parent)
        self.on_send = on_send

        self.setStyleSheet("""
            QWidget#chatRoot {
                background-color: #242424;
                border: 1px solid #2c2c2c;
                border-radius: 10px;
            }
            QTextEdit#history {
                background-color: #1f1f1f;
                border: 1px solid #333333;
                border-radius: 8px;
                padding: 8px;
                color: #eaeaea;
            }
            QLineEdit#prompt {
                background-color: #1f1f1f;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                padding: 10px 12px;
                color: #eaeaea;
            }
            QPushButton#sendBtn {
                background-color: #2e2e2e;
                color: #eaeaea;
                padding: 8px 14px;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                font-weight: 600;
            }
            QPushButton#sendBtn:hover { background-color: #373737; }
            QPushButton#sendBtn:pressed { background-color: #2a2a2a; }
        """)

        root = QVBoxLayout(self, objectName="chatRoot")
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        title = QLabel("Assistant Chat")
        title.setStyleSheet("font-size: 13px; font-weight: 700; color: #e2e2e2;")
        root.addWidget(title)

        self.history = QTextEdit(objectName="history")
        self.history.setReadOnly(True)
        self.history.setMinimumHeight(120)
        self.history.setPlaceholderText("Messages will appear here...")
        root.addWidget(self.history)

        prompt_row = QHBoxLayout()
        prompt_row.setSpacing(8)

        self.prompt = QLineEdit(objectName="prompt")
        self.prompt.setPlaceholderText("Type your message and press Enter...")

        self.send_btn = QPushButton("Send", objectName="sendBtn")
        self.send_btn.setCursor(Qt.PointingHandCursor)

        self.prompt.returnPressed.connect(self.send_message)
        self.send_btn.clicked.connect(self.send_message)

        prompt_row.addWidget(self.prompt, 1)
        prompt_row.addWidget(self.send_btn, 0)

        root.addLayout(prompt_row)

    def set_busy(self, busy: bool):
        self.prompt.setDisabled(busy)
        self.send_btn.setDisabled(busy)
        self.send_btn.setText("Sending..." if busy else "Send")

    def append_message(self, sender: str, text: str):
        if sender.lower() == "you":
            color = "#93c5fd"
            bubble_bg = "rgba(59, 130, 246, 0.12)"
        else:
            color = "#fca5a5"
            bubble_bg = "rgba(239, 68, 68, 0.12)"
        html = f"""
        <div style="margin:6px 0; padding:8px; background:{bubble_bg}; border:1px solid #3a3a3a; border-radius:8px;">
            <div style="font-weight:700; color:{color};">{sender}</div>
            <div style="color:#eaeaea; white-space:pre-wrap;">{text}</div>
        </div>
        """
        self.history.append(html)
        self.history.verticalScrollBar().setValue(self.history.verticalScrollBar().maximum())

    def send_message(self):
        text = self.prompt.text().strip()
        if not text:
            return

        task_type = "status"

        self.append_message("You", text)
        self.prompt.clear()

        if callable(self.on_send):
            self.set_busy(True)
            self.on_send(text, task_type)
        else:
            reply = self.generate_reply(text)
            self.append_message("Assistant", reply)

    def generate_reply(self, user_text: str) -> str:
        return f"I received: “{user_text}”. How can I help further?"


# -----------------------------
# MainWindow
# -----------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cb_model = CatBoostClassifier()
        self.cb_model.load_model(model_path)

        self.dm = DataManager(draftdata_path)
        #self.dm.limit_games(5)
        self.context_csv_data = self.dm.get_context()
        
        
        self.genai_manager = None #GeminiManager(api_key=os.getenv("GEMINI_API_KEY", ""))
        self.service_manager = None   #DraftService(self.genai_manager)
        self.last_ai_suggestion_test = ""

        self.cb_expected = list(getattr(self.cb_model, "feature_names_", []) or [])
        if not self.cb_expected:
            self.cb_expected = [
                "Teams", "Opponent",
                "Ban1", "Ban2", "Ban3", "Ban4", "Ban5", "Ban6",
                "Pick1", "Pick2", "Pick3", "Pick4", "Pick5", "Pick6",
                "Ban7", "Ban8", "Ban9", "Ban10",
                "Pick7", "Pick8", "Pick9", "Pick10",
            ]

        self.cb_cat_cols = [
            "Teams", "Opponent",
            "Ban1", "Ban2", "Ban3", "Ban4", "Ban5", "Ban6",
            "Pick1", "Pick2", "Pick3", "Pick4", "Pick5", "Pick6",
            "Ban7", "Ban8", "Ban9", "Ban10",
            "Pick7", "Pick8", "Pick9", "Pick10",
        ]

        self.cb_cat_idx = [self.cb_expected.index(c) for c in self.cb_cat_cols if c in self.cb_expected]

        self.main_manager = MainManager()
        self.path_to_csv = csv_path
        self.main_manager.load_data(self.path_to_csv, self.path_to_csv, self.path_to_csv)

        self.team_master_list = self.build_team_master_list()

        self.setWindowTitle("Champion Draft Tool")
        self.setGeometry(100, 100, 1400, 900)

        self.champion_tiles = []
        self.champion_tiles_dict = {}

        self.selected_blue_team = "Blue Team Players"
        self.selected_red_team = "Red Team Players"
        self.home_side = None

        self.all_champions = {}
        self.available_champions = []
        self.blue_bans = []
        self.red_bans = []
        self.blue_picks = []
        self.red_picks = []
        self.current_turn = "blue_ban"
        self.current_cols = 8
        self.turn_counter = 0

        self.players = {
            "blue": [PlayerCard("Player1", "blue"), PlayerCard("Player2", "blue"),
                     PlayerCard("Player3", "blue"), PlayerCard("Player4", "blue"), PlayerCard("Player5", "blue")],
            "red": [PlayerCard("Player6", "red"), PlayerCard("Player7", "red"),
                    PlayerCard("Player8", "red"), PlayerCard("Player9", "red"), PlayerCard("Player10", "red")]
        }

        self.blue_stats_widget = None
        self.red_stats_widget = None

        self.sort_mode = ("name", True)

        self._grid_scroll_viewport = None

        # API key UI state
        self.api_key_edit = None
        self.api_key_visible = False

        self.init_ui()

    def init_ui(self):
        self.resizeEvent = self.on_window_resize

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Top bar
        top_bar = QWidget()
        top_bar.setMinimumHeight(64)
        top_bar.setStyleSheet("background-color: #242424; border: 1px solid #2c2c2c; border-radius: 10px;")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(14, 8, 14, 8)
        top_layout.setSpacing(8)

        self.turn_label = QLabel("Blue Team's turn to ban")
        self.turn_label.setStyleSheet("font-size: 18px; font-weight: 700; color: #f0f0f0;")

        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)

        def btn(txt):
            b = QPushButton(txt)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet("""
                QPushButton {
                    background-color: #2e2e2e;
                    color: #eaeaea;
                    padding: 8px 14px;
                    border: 1px solid #3a3a3a;
                    border-radius: 6px;
                    font-weight: 600;
                }
                QPushButton:hover { background-color: #373737; }
                QPushButton:pressed { background-color: #2a2a2a; }
            """)
            return b

        reset_btn = btn("Reset Draft")
        reset_btn.clicked.connect(self.reset_draft)
        random_ban_btn = btn("Random Ban")
        random_ban_btn.clicked.connect(self.random_ban)
        random_pick_btn = btn("Random Pick")
        random_pick_btn.clicked.connect(self.random_pick)

        controls_layout.addWidget(reset_btn)
        controls_layout.addWidget(random_ban_btn)
        controls_layout.addWidget(random_pick_btn)
        controls_layout.addStretch()

        # --- API Key controls (top-right) ---
        api_layout = QHBoxLayout()
        api_layout.setSpacing(6)

        api_label = QLabel("API Key")
        api_label.setStyleSheet("color:#bbb; font-size:12px;")

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setPlaceholderText("Enter API key...")
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setFixedWidth(240)
        self.api_key_edit.setStyleSheet("""
            QLineEdit {
                padding: 8px 10px;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                background-color: #1f1f1f;
                color: #eaeaea;
            }
            QLineEdit:focus { border-color: #3b82f6; }
        """)
        prefill = self._load_api_key()
        if prefill:
            self.api_key_edit.setText(prefill)

        toggle_btn = QPushButton("👁")
        toggle_btn.setCheckable(True)
        toggle_btn.setFixedWidth(34)
        toggle_btn.setToolTip("Show/Hide API Key")
        toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #2e2e2e;
                color: #eaeaea;
                padding: 6px 8px;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                font-weight: 700;
            }
            QPushButton:checked { background-color: #373737; }
        """)
        def on_toggle():
            self.api_key_visible = toggle_btn.isChecked()
            self.api_key_edit.setEchoMode(QLineEdit.Normal if self.api_key_visible else QLineEdit.Password)
        toggle_btn.toggled.connect(lambda _: on_toggle())

        save_btn = QPushButton("Save")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setToolTip("Save API key (updates .env)")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2e2e2e;
                color: #eaeaea;
                padding: 8px 12px;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #373737; }
            QPushButton:pressed { background-color: #2a2a2a; }
        """)
        def on_save():
            key = self.api_key_edit.text().strip()
            self._save_api_key(key, persist_to_env=True)
            if not key:
                self.api_key_edit.setText(self._load_api_key())
            QToolTip.showText(save_btn.mapToGlobal(save_btn.rect().center()), "API key saved")
        save_btn.clicked.connect(on_save)

        api_layout.addWidget(api_label)
        api_layout.addWidget(self.api_key_edit)
        api_layout.addWidget(toggle_btn)
        api_layout.addWidget(save_btn)

        # Arrange top layout: left turn label, stretch, controls, API key on far right
        top_layout.addWidget(self.turn_label)
        top_layout.addStretch()
        top_layout.addLayout(controls_layout)
        top_layout.addLayout(api_layout)

        # Middle (bans + prob)
        middle = QWidget()
        middle.setStyleSheet("background-color: #242424; border: 1px solid #2c2c2c; border-radius: 10px;")
        middle_layout = QVBoxLayout(middle)
        middle_layout.setContentsMargins(14, 12, 14, 12)
        middle_layout.setSpacing(12)

        bans_row = QHBoxLayout()
        bans_row.setSpacing(16)
        bans_row.setAlignment(Qt.AlignCenter)

        def build_team_bans(title, team):
            container = QWidget()
            container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(6)

            label = QLabel(title)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("font-size: 13px; font-weight: 700; color: #e2e2e2;")
            slots_row = QHBoxLayout()
            slots_row.setSpacing(8)
            slots_row.setAlignment(Qt.AlignCenter)
            slots = []
            for i in range(5):
                slot = DraftSlot("ban", team, i + 1)
                slots.append(slot)
                slots_row.addWidget(slot)
            layout.addWidget(label, 0, Qt.AlignCenter)
            layout.addLayout(slots_row)
            return container, slots, label

        blue_bans_container, self.blue_ban_slots, self.blue_bans_label = build_team_bans("Blue Team Bans", "blue")
        red_bans_container, self.red_ban_slots, self.red_bans_label = build_team_bans("Red Team Bans", "red")

        prob_col = QVBoxLayout()
        prob_col.setSpacing(6)
        prob_col.setAlignment(Qt.AlignCenter)

        self.prob_bar = ProbabilityBar()
        prob_col.addWidget(self.prob_bar, 0, Qt.AlignCenter)

        bans_row.addWidget(blue_bans_container, 0, Qt.AlignVCenter)
        bans_row.addSpacerItem(QSpacerItem(24, 1, QSizePolicy.Fixed, QSizePolicy.Minimum))
        bans_row.addLayout(prob_col, 0)
        bans_row.addSpacerItem(QSpacerItem(24, 1, QSizePolicy.Fixed, QSizePolicy.Minimum))
        bans_row.addWidget(red_bans_container, 0, Qt.AlignVCenter)

        middle_layout.addLayout(bans_row)

        # Bottom main area
        bottom = QWidget()
        bottom_layout = QHBoxLayout(bottom)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(10)

        # Blue team panel
        blue_team_container = QWidget()
        blue_team_container.setMinimumWidth(240)
        blue_team_container.setStyleSheet("background-color: #242424; border: 1px solid #2c2c2c; border-radius: 10px;")
        blue_team_layout = QVBoxLayout(blue_team_container)
        blue_team_layout.setContentsMargins(12, 12, 12, 12)
        blue_team_layout.setSpacing(8)

        self.blue_team_label = QLabel("Blue Team")
        self.blue_team_label.setStyleSheet("font-size: 14px; font-weight: 700; color: #3b82f6;")
        self.blue_team_label.setAlignment(Qt.AlignCenter)
        blue_team_layout.addWidget(self.blue_team_label)

        blue_split = QHBoxLayout()
        blue_split.setContentsMargins(0, 0, 0, 0)
        blue_split.setSpacing(8)

        # Stats (left)
        stats_wrap = QWidget()
        stats_wrap.setStyleSheet("background-color:#262626; border:1px solid #303030; border-radius:8px;")
        stats_wrap_layout = QVBoxLayout(stats_wrap)
        stats_wrap_layout.setContentsMargins(8, 8, 8, 8)
        stats_wrap_layout.setSpacing(6)

        self.blue_stats_widget = TeamStatsWidget(
            title_text="Most Picked Champions",
            color="#3b82f6",
            get_team_name_fn=lambda: self.selected_blue_team,
            get_top_picks_fn=self.get_team_top_picks,
            all_champs_ref=lambda: self.all_champions,
            get_top_wr_fn=self.get_team_top_wr  # new: highest winrate list just below
        )
        stats_wrap_layout.addWidget(self.blue_stats_widget)
        stats_wrap_layout.addStretch()

        # Picks (right)
        blue_picks_col = QVBoxLayout()
        blue_picks_col.setContentsMargins(0, 0, 0, 0)
        blue_picks_col.setSpacing(6)

        picks_title = QLabel("Picks")
        picks_title.setAlignment(Qt.AlignCenter)
        picks_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #e2e2e2;")
        blue_picks_col.addWidget(picks_title)

        picks_wrap = QWidget()
        picks_wrap.setStyleSheet("background-color:#262626; border:1px solid #303030; border-radius:8px;")
        picks_wrap_layout = QVBoxLayout(picks_wrap)
        picks_wrap_layout.setContentsMargins(8, 8, 8, 8)
        picks_wrap_layout.setSpacing(6)
        picks_wrap_layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

        for pc in self.players["blue"]:
            pc.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            picks_wrap_layout.addWidget(pc)

        blue_picks_col.addWidget(picks_wrap, 1)

        blue_split.addWidget(stats_wrap, 5)
        blue_split.addLayout(blue_picks_col, 6)
        blue_team_layout.addLayout(blue_split, 1)

        footer = QHBoxLayout()
        footer.setSpacing(8)

        self.blue_team_combo = QComboBox()
        blue_team_items = ["Blue Team Players"] + self.team_master_list
        self.blue_team_combo.addItems(blue_team_items)
        blue_view = QListView()
        self.blue_team_combo.setView(blue_view)
        self.blue_team_combo.currentTextChanged.connect(self.on_blue_team_combo_changed)
        self.blue_team_combo.setStyleSheet("""
            QComboBox {
                background-color: #2b2b2b;
                color: #eaeaea;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                padding: 6px;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 22px;
                border-left: 1px solid #3a3a3a;
            }
            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #eaeaea;
                selection-background-color: #3a3a3a;
                border: 1px solid #3a3a3a;
                outline: 0;
            }
            QComboBox::view { max-height: 240px; }
        """)

        self.blue_home_btn = QPushButton("Set Home")
        self.blue_home_btn.setCursor(Qt.PointingHandCursor)
        self.blue_home_btn.setFocusPolicy(Qt.NoFocus)
        self.blue_home_btn.setToolTip("Mark Blue side as Home")
        self.blue_home_btn.setStyleSheet("""
            QPushButton {
                background-color: #2e2e2e;
                color: #eaeaea;
                padding: 6px 10px;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #373737; }
            QPushButton:pressed { background-color: #2a2a2a; }
        """)
        self.blue_home_btn.clicked.connect(lambda: self.set_home_side("blue"))

        footer.addWidget(self.blue_team_combo, 1)
        footer.addWidget(self.blue_home_btn, 0, Qt.AlignRight)
        blue_team_layout.addLayout(footer)

        # Center grid + search
        champion_grid_container = QWidget()
        champion_grid_layout = QVBoxLayout(champion_grid_container)
        champion_grid_layout.setContentsMargins(0, 0, 0, 0)
        champion_grid_layout.setSpacing(8)

        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(8)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search champions...")
        self.search_bar.setClearButtonEnabled(True)
        self.search_bar.textChanged.connect(self.filter_champions)
        self.search_bar.setStyleSheet("""
            QLineEdit {
                padding: 10px 12px;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                font-size: 14px;
                background-color: #1f1f1f;
                color: #eaeaea;
            }
            QLineEdit:focus { border-color: #3b82f6; }
        """)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Alphabetical", "Winrate", "Games Played", "Delta"])
        self.sort_combo.setToolTip("Sort grid")
        self.sort_combo.setStyleSheet("""
            QComboBox {
                background-color: #2b2b2b;
                color: #eaeaea;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                padding: 6px 8px;
                min-width: 130px;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 22px;
                border-left: 1px solid #3a3a3a;
            }
            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #eaeaea;
                selection-background-color: #3a3a3a;
                border: 1px solid #3a3a3a;
                outline: 0;
            }
        """)

        self.sort_dir_btn = QPushButton("▲")
        self.sort_dir_btn.setCheckable(True)
        self.sort_dir_btn.setToolTip("Toggle ascending/descending")
        self.sort_dir_btn.setCursor(Qt.PointingHandCursor)
        self.sort_dir_btn.setFixedWidth(34)
        self.sort_dir_btn.setStyleSheet("""
            QPushButton {
                background-color: #2e2e2e;
                color: #eaeaea;
                padding: 6px 8px;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                font-weight: 700;
            }
            QPushButton:checked { background-color: #373737; }
        """)

        def on_sort_changed():
            text = self.sort_combo.currentText()
            key = "name"
            if text == "Alphabetical":
                key = "name"
            elif text == "Winrate":
                key = "wr"
            elif text == "Games Played":
                key = "games"
            elif text == "Delta":
                key = "delta"
            asc = not self.sort_dir_btn.isChecked()
            self.sort_mode = (key, asc)
            self.filter_champions(self.search_bar.text())

        def on_sort_dir_toggle():
            self.sort_dir_btn.setText("▼" if self.sort_dir_btn.isChecked() else "▲")
            on_sort_changed()

        self.sort_combo.currentIndexChanged.connect(on_sort_changed)
        self.sort_dir_btn.toggled.connect(lambda _: on_sort_dir_toggle())

        search_layout.addWidget(self.search_bar, 1)
        search_layout.addWidget(self.sort_combo, 0)
        search_layout.addWidget(self.sort_dir_btn, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # no horizontal scroll
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QWidget#scrollViewport { background-color: #242424; border: 1px solid #2c2c2c; border-radius: 10px; }
        """)
        viewport = QWidget(objectName="scrollViewport")
        vlayout = QVBoxLayout(viewport)
        vlayout.setContentsMargins(12, 12, 12, 12)
        vlayout.setSpacing(8)

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(10)
        self.grid_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        vlayout.addWidget(self.grid_container)
        scroll.setWidget(viewport)

        # Important: listen to viewport resizes (actual visible width)
        scroll.viewport().installEventFilter(self)
        self._grid_scroll_viewport = scroll.viewport()

        champion_grid_layout.addWidget(search_container)
        champion_grid_layout.addWidget(scroll)

        # Red team panel
        red_team_container = QWidget()
        red_team_container.setMinimumWidth(240)
        red_team_container.setStyleSheet("background-color: #242424; border: 1px solid #2c2c2c; border-radius: 10px;")
        red_team_layout = QVBoxLayout(red_team_container)
        red_team_layout.setContentsMargins(12, 12, 12, 12)
        red_team_layout.setSpacing(8)

        self.red_team_label = QLabel("Red Team")
        self.red_team_label.setStyleSheet("font-size: 14px; font-weight: 700; color: #ef4444;")
        self.red_team_label.setAlignment(Qt.AlignCenter)
        red_team_layout.addWidget(self.red_team_label)

        red_split = QHBoxLayout()
        red_split.setContentsMargins(0, 0, 0, 0)
        red_split.setSpacing(8)

        # Picks (left, next to grid)
        red_picks_col = QVBoxLayout()
        red_picks_col.setContentsMargins(0, 0, 0, 0)
        red_picks_col.setSpacing(6)

        rpicks_title = QLabel("Picks")
        rpicks_title.setAlignment(Qt.AlignCenter)
        rpicks_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #e2e2e2;")
        red_picks_col.addWidget(rpicks_title)

        rpicks_wrap = QWidget()
        rpicks_wrap.setStyleSheet("background-color:#262626; border:1px solid #303030; border-radius:8px;")
        rpicks_wrap_layout = QVBoxLayout(rpicks_wrap)
        rpicks_wrap_layout.setContentsMargins(8, 8, 8, 8)
        rpicks_wrap_layout.setSpacing(6)
        rpicks_wrap_layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

        for pc in self.players["red"]:
            pc.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            rpicks_wrap_layout.addWidget(pc)

        red_picks_col.addWidget(rpicks_wrap, 1)

        # Stats (right)
        rstats_wrap = QWidget()
        rstats_wrap.setStyleSheet("background-color:#262626; border:1px solid #303030; border-radius:8px;")
        rstats_wrap_layout = QVBoxLayout(rstats_wrap)
        rstats_wrap_layout.setContentsMargins(8, 8, 8, 8)
        rstats_wrap_layout.setSpacing(6)

        self.red_stats_widget = TeamStatsWidget(
            title_text="Most Picked Champions",
            color="#ef4444",
            get_team_name_fn=lambda: self.selected_red_team,
            get_top_picks_fn=self.get_team_top_picks,
            all_champs_ref=lambda: self.all_champions,
            get_top_wr_fn=self.get_team_top_wr  # new: highest winrate list just below
        )
        rstats_wrap_layout.addWidget(self.red_stats_widget)
        rstats_wrap_layout.addStretch()

        red_split.addLayout(red_picks_col, 6)
        red_split.addWidget(rstats_wrap, 5)
        red_team_layout.addLayout(red_split, 1)

        rfooter = QHBoxLayout()
        rfooter.setSpacing(8)

        self.red_team_combo = QComboBox()
        red_team_items = ["Red Team Players"] + self.team_master_list
        self.red_team_combo.addItems(red_team_items)
        red_view = QListView()
        self.red_team_combo.setView(red_view)
        self.red_team_combo.currentTextChanged.connect(self.on_red_team_combo_changed)
        self.red_team_combo.setStyleSheet("""
            QComboBox {
                background-color: #2b2b2b;
                color: #eaeaea;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                padding: 6px;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 22px;
                border-left: 1px solid #3a3a3a;
            }
            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #eaeaea;
                selection-background-color: #3a3a3a;
                border: 1px solid #3a3a3a;
                outline: 0;
            }
            QComboBox::view { max-height: 240px; }
        """)

        self.red_home_btn = QPushButton("Set Home")
        self.red_home_btn.setCursor(Qt.PointingHandCursor)
        self.red_home_btn.setFocusPolicy(Qt.NoFocus)
        self.red_home_btn.setToolTip("Mark Red side as Home")
        self.red_home_btn.setStyleSheet("""
            QPushButton {
                background-color: #2e2e2e;
                color: #eaeaea;
                padding: 6px 10px;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #373737; }
            QPushButton:pressed { background-color: #2a2a2a; }
        """)
        self.red_home_btn.clicked.connect(lambda: self.set_home_side("red"))

        rfooter.addWidget(self.red_team_combo, 1)
        rfooter.addWidget(self.red_home_btn, 0, Qt.AlignRight)
        red_team_layout.addLayout(rfooter)

        bottom_layout.addWidget(blue_team_container, 0)
        bottom_layout.addWidget(champion_grid_container, 2)  # give center more stretch
        bottom_layout.addWidget(red_team_container, 0)

        main_layout.addWidget(top_bar)
        main_layout.addWidget(middle)
        main_layout.addWidget(bottom)

        # Bottom dock: Chat + Suggestions + Predictions
        bottom_dock = QWidget()
        bottom_dock.setStyleSheet("background: transparent;")
        dock_layout = QHBoxLayout(bottom_dock)
        dock_layout.setContentsMargins(0, 0, 0, 0)
        dock_layout.setSpacing(10)

        self.chat_box = ChatBox(on_send=self.handle_chat_send)
        # Slightly shrink to make space
        self.chat_box.setMinimumHeight(200)

        self.suggestions_panel = SuggestionsPanel(parent=self, on_prompt_suggestion=self.prompt_suggestion, main=self)
        # Slightly narrower to fit a third panel
        self.suggestions_panel.setMinimumWidth(320)

        # New predictions panel
        self.predictions_panel = PredictionsPanel(parent=self, main=self)
        self.predictions_panel.setMinimumWidth(320)

        dock_layout.addWidget(self.chat_box, 1)
        dock_layout.addWidget(self.suggestions_panel, 1)
        dock_layout.addWidget(self.predictions_panel, 1)

        main_layout.addWidget(bottom_dock)

        self.update_turn(first=True)
        self.load_champions()
        self.update_all_deltas()
        self.update_home_visuals()
        self.suggestions_panel.set_context(self.current_turn)
        self.predictions_panel.set_context(self._compute_next_turn())
        self.update_winrate_bar()

        # Initial refresh of team stats and grid
        QTimer.singleShot(0, self.refresh_team_stats)
        QTimer.singleShot(0, self.update_grid_columns)
        QTimer.singleShot(0, self._apply_inital_team_defaults)

    # Sorting helpers
    def _tile_sort_key(self, tile: ChampionTile):
        key, asc = self.sort_mode
        name = tile.champion_name

        def parse_wr(text: str):
            try:
                t = (text or "").strip()
                if t in ("--", "-"):
                    return 0.0
                return float(t.replace("WR", "").replace("%", "").strip())
            except Exception:
                return 0.0

        def parse_int(text: str):
            try:
                t = (text or "").strip()
                if t in ("--", "-"):
                    return 0
                return int(t.replace(",", ""))
            except Exception:
                return 0

        if key == "name":
            return name.lower()
        if key == "delta":
            d = getattr(tile, "delta_winrate", 0.0)
            return (d, name.lower())
        if key == "wr":
            wr = parse_wr(tile.general_winrate_label.text())
            return (wr, name.lower())
        if key == "games":
            gp = parse_int(tile.games_played_label.text())
            return (gp, name.lower())
        return name.lower()

    # AI helpers
    def _ensure_ai_ready(self) -> bool:
        key = (os.getenv("GEMINI_API_KEY", ""))
        if not key:
            return False
        
        os.environ["GEMINI_API_KEY"] = key
        os.environ["GOOGLE_API"] = key
        
        try:
            # Always rebuild GeminiManager when key changes or manager is None.
            # This avoids "stale client" issues inside the manager.
            from AI.GeminiManager import GeminiManager
            from AI.DraftService import DraftService

            if getattr(self, "genai_manager", None) is None or getattr(self.genai_manager, "api_key", None) != key:
                self.genai_manager = GeminiManager(api_key=key)
                self.service_manager = DraftService(self.genai_manager)
                self.service_manager.set_data_context(self.context_csv_data)
            elif getattr(self, "service_manager", None) is None:
                self.service_manager = DraftService(self.genai_manager)
                self.service_manager.set_data_context(self.context_csv_data)

            return True
        
        except Exception as e:
            # Don’t crash the UI; just inform and keep AI disabled
            if hasattr(self, "chat_box") and self.chat_box:
                self.chat_box.append_message("Assistant", f"Could not initialize AI: {e}")
            self.service_manager = None
            self.genai_manager = None
            return False
        
    def _read_csv_as_text(self, csv_path: str, max_bytes=40_000) -> str:
        if not os.path.exists(csv_path):
            return f"[CSV not found: {csv_path}]"
        try:
            with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
                data = f.read()
            if len(data) > max_bytes:
                head = data[:max_bytes]
                return head + f"\n...[truncated, original {len(data)} bytes]"
            return data
        except Exception as e:
            return f"[Error reading CSV: {e}]"

    def _build_system_prompt(self) -> str:
        blue_team, red_team = self._current_team_names()
        context = [
            "You are a pro League of Legends draft analyst.",
            "Suggestions should be for current phase of turn order and ideally in batches, e.g first 3 bans for each team",
            "Context: Champion Draft Assistant.",
            f"Blue Team: {blue_team}",
            f"Red Team: {red_team}",
            f"Home side: {self.home_side or 'unset'}",
            f"Turn: {self.current_turn}",
            f"Blue bans: {', '.join(self.blue_bans) if self.blue_bans else 'none'}",
            f"Red bans: {', '.join(self.red_bans) if self.red_bans else 'none'}",
            f"Blue picks: {', '.join(self.blue_picks) if self.blue_picks else 'none'}",
            f"Red picks: {', '.join(self.red_picks) if self.red_picks else 'none'}",
            "Be concise and helpful. If asked for suggestions, provide 3–5 champions with brief reasons.",
        ]
        return "\n".join(context)

    def handle_chat_send(self, user_text: str = "", task_type="status", rec_count=10):
        # Require an API key before using AI features
        key = os.getenv("GEMINI_API_KEY", "") or (self.api_key_edit.text().strip() if self.api_key_edit else "")
        if not self._ensure_ai_ready():
            self.chat_box.append_message("Assistant", "Please set your API key (top right) before using AI features.")
            self.chat_box.set_busy(False)
            self.suggestions_panel.set_busy(False)
            return

        self.service_manager.update_context(
            blue_team=self.selected_blue_team,
            red_team=self.selected_red_team,
            home_side=self.home_side,
            current_turn=self.current_turn,
            turn_counter=self.turn_counter,
            next_turn=self._compute_next_turn(),
            blue_bans=self.blue_bans,
            red_bans=self.red_bans,
            blue_picks=self.blue_picks,
            red_picks=self.red_picks,
        )

        self._ai_thread = QThread(self)
        if task_type == "status":
            #pass in the suggestions it last suggested as context alongside any prompt user makes
            if getattr(self, "last_ai_suggestions_text",""):
                user_text = (
                    f"{user_text}\n\n"
                    f"Your previous ai suggestions (for context):\n"
                    f"{self.last_ai_suggestion_test}"
                )
            self._ai_worker = AIWorker(self.service_manager, task_type, update_text=user_text)
        else:
            self._ai_worker = AIWorker(self.service_manager, task_type, n=rec_count)

        self._ai_worker.moveToThread(self._ai_thread)

        self._ai_thread.started.connect(self._ai_worker.run)
        self._ai_worker.finished.connect(self._on_ai_finished)
        self._ai_worker.error.connect(self._on_ai_error)

        self._ai_worker.finished.connect(self._ai_thread.quit)
        self._ai_worker.finished.connect(self._ai_worker.deleteLater)
        self._ai_thread.finished.connect(self._ai_thread.deleteLater)

        self._ai_worker.error.connect(self._ai_thread.quit)
        self._ai_worker.error.connect(self._ai_worker.deleteLater)

        self._ai_thread.start()

    def prompt_suggestion(self, count: int):
        prompt_text = "Loading..."
        
        self.chat_box.set_busy(True)
        self.chat_box.append_message("You", prompt_text)
        self.handle_chat_send(task_type="recommend", rec_count=count)

    def _on_ai_finished(self, result):
        self.chat_box.set_busy(False)
        self.suggestions_panel.set_busy(False)

        if hasattr(result, 'recommendations'):
            summary = getattr(result, 'strategic_summary', '') or ''
            prompt_given = getattr(result,'prompt','') or ''
            # Fill Suggestions
            self.chat_box.append_message("Assistant", f"Summary: {summary}")
            self.suggestions_panel.clear_suggestions()
            lines = []
            for pick in result.recommendations:
                self.suggestions_panel.add_suggestion(pick)
                name = getattr(pick, "champion_name", "") or "Unknown"
                reason = getattr(pick, "reasoning", "") or ""
                syn = getattr(pick, "possible_synergies", []) or []
                ctr = getattr(pick, "possible_counters", []) or []

                def _to_names(lst):
                    out = []
                    for x in lst:
                        if isinstance(x, str):
                            out.append(x)
                        elif isinstance(x, dict):
                            out.append(x.get("name", ""))
                        else:
                            # fallback to string
                            out.append(str(x))
                    return [n for n in out if n]

                syn_names = _to_names(syn)
                ctr_names = _to_names(ctr)

                parts = [f"- {name}"]
                if reason:
                    parts.append(f"reason: {reason}")
                if syn_names:
                    parts.append(f"synergy: {', '.join(syn_names)}")
                if ctr_names:
                    parts.append(f"counters: {', '.join(ctr_names)}")

                lines.append(" | ".join(parts))

            self.last_ai_suggestion_test = "\n".join(lines)

            # Fill Predictions from each pick’s predicted fields
            self.predictions_panel.clear_predictions()
            pred_list = getattr(result, "predictions", []) or []
            for pred in pred_list:
                champ = getattr(pred, "predicted_next_champ", "") or ""
                proba = getattr(pred, "confidence_score", 0.0)  # 0–1 expected
                reason = getattr(pred, "reasoning", "") or ""
                if champ:
                    self.predictions_panel.add_prediction(champ, float(proba or 0.0), reason)
            return

        self.chat_box.append_message("Assistant", str(result))

    def _on_ai_error(self, err: str):
        self.chat_box.append_message("Assistant", err)
        self.chat_box.set_busy(False)
        self.suggestions_panel.set_busy(False)

    def populate_suggestions_from_text(self, text: str):
        self.suggestions_panel.clear_suggestions()
        if not self.all_champions:
            return
        found = []
        lower_text = text.lower()
        for key, data in self.all_champions.items():
            name = data["name"]
            if name.lower() in lower_text:
                found.append(key)
            if len(found) >= 5:
                break
        if not found:
            candidates = [k for k in self.available_champions]
            for k in candidates[:3]:
                class _Tmp:
                    champion_name = self.all_champions[k]["name"]
                    reasoning = "Potential synergy or counterpick."
                    possible_synergies = []
                    possible_counters = []
                self.suggestions_panel.add_suggestion(_Tmp())
            return
        for k in found:
            class _Tmp:
                champion_name = self.all_champions[k]["name"]
                reasoning = "Mentioned by the assistant."
                possible_synergies = []
                possible_counters = []
            self.suggestions_panel.add_suggestion(_Tmp())

    # -----------------------------
    # Team stats helpers
    # -----------------------------
    def _apply_inital_team_defaults(self):
        # Use the first two unique teams as defaults
        teams = list(self.team_master_list or [])
        if not teams:
            # Nothing to do; keep placeholders
            return

        # Choose first and second if available (avoid duplicates)
        blue_default = teams[0]
        red_default = teams[1] if len(teams) > 1 else None
        if red_default == blue_default:
            # If somehow duplicated (shouldn’t happen with set+sorted), try next
            for t in teams[1:]:
                if t != blue_default:
                    red_default = t
                    break

        # Update internal state
        self.selected_blue_team = blue_default
        if red_default:
            self.selected_red_team = red_default

        # Update combos without firing change handlers during setup
        self.blue_team_combo.blockSignals(True)
        self.red_team_combo.blockSignals(True)

        # Rebuild combo items excluding the opposite selection (to prevent selecting the same team twice)
        self.repopulate_combo_excluding(
            combo=self.blue_team_combo,
            default_label="Blue Team Players",
            excluded=self.selected_red_team if self.selected_red_team not in (None, "", "Red Team Players") else "",
            keep_current=blue_default,
        )
        if red_default:
            self.repopulate_combo_excluding(
                combo=self.red_team_combo,
                default_label="Red Team Players",
                excluded=self.selected_blue_team if self.selected_blue_team not in (None, "", "Blue Team Players") else "",
                keep_current=red_default,
            )

        # Select the items we want
        idx_blue = self.blue_team_combo.findText(self.selected_blue_team)
        if idx_blue >= 0:
            self.blue_team_combo.setCurrentIndex(idx_blue)
        if red_default:
            idx_red = self.red_team_combo.findText(self.selected_red_team)
            if idx_red >= 0:
                self.red_team_combo.setCurrentIndex(idx_red)

        self.blue_team_combo.blockSignals(False)
        self.red_team_combo.blockSignals(False)

        # Make blue the default home side
        self.home_side = "blue"
        self.update_home_visuals()
        self.update_winrate_bar()
        self.update_all_deltas()
        self.refresh_team_stats()
    
    
    def refresh_team_stats(self):
        if self.blue_stats_widget:
            self.blue_stats_widget.refresh()
        if self.red_stats_widget:
            self.red_stats_widget.refresh()

    def get_team_top_picks(self, team_name: str):
        picks = []
        tm = getattr(self.main_manager, "team_manager", None)
        cm = getattr(self.main_manager, "champion_manager", None)

        try:
            team_obj = None
            if tm and hasattr(tm, "teams"):
                # Direct name match
                for _, t in tm.teams.items():
                    if getattr(t, "name", "") == team_name:
                        team_obj = t
                        break
            if team_obj:
                # Support either object attributes or dict form (from to_dict)
                champ_stats = getattr(team_obj, "champion_stats", None)

                candidates = []
                if isinstance(champ_stats, dict):
                    for cname, val in champ_stats.items():
                        # Two shapes:
                        # 1) val is TeamChampionPerformance-like (with attributes)
                        # 2) val is dict with keys: games, wins, etc.
                        try:
                            if isinstance(val, dict):
                                games = int(val.get("games", 0))
                                wins = int(val.get("wins", 0))
                            else:
                                games = int(getattr(val, "games", 0))
                                wins = int(getattr(val, "wins", 0))
                            if games > 0:
                                wr = (wins / games) * 100.0
                                candidates.append((util.name_cleanup(cname), games, wr))
                        except Exception:
                            continue

                # Sort: more games first, then higher winrate
                candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
                picks = [(c[0], c[2], c[1]) for c in candidates]  # (name, wr, games)
        except Exception:
            picks = []

        # Fallback: global champion stats (popular overall)
        if not picks and cm:
            try:
                candidates = []
                for cname, champ in getattr(cm, "champions", {}).items():
                    games = int(getattr(champ, "total_games", 0))
                    wins = int(getattr(champ, "total_wins", 0))
                    if games > 0:
                        wr = (wins / games) * 100.0
                        candidates.append((util.name_cleanup(cname), games, wr))
                candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
                picks = [(c[0], c[2], c[1]) for c in candidates[:8]]
            except Exception:
                picks = []

        # Filter out currently banned/picked to reduce noise
        filtered = []
        banpick = set([x.lower() for x in (self.blue_bans + self.red_bans + self.blue_picks + self.red_picks)])
        for name, wr, games in picks:
            if name.lower() not in banpick:
                filtered.append((name, wr, games))
        return filtered

    def get_team_top_wr(self, team_name: str, min_games: int = 5):
        """
        Return champions for the given team sorted by highest winrate.
        Shape: list of tuples (name, wr, games), already filtered by current bans/picks.
        This mirrors get_top_champions(...) behavior but sorts by winrate instead.
        """
        picks = []
        tm = getattr(self.main_manager, "team_manager", None)
        cm = getattr(self.main_manager, "champion_manager", None)

        try:
            team_obj = None
            if tm and hasattr(tm, "teams"):
                for _, t in tm.teams.items():
                    if getattr(t, "name", "") == team_name:
                        team_obj = t
                        break
            if team_obj:
                champ_stats = getattr(team_obj, "champion_stats", None)

                candidates = []
                if isinstance(champ_stats, dict):
                    for cname, val in champ_stats.items():
                        try:
                            if isinstance(val, dict):
                                games = int(val.get("games", 0))
                                wins = int(val.get("wins", 0))
                            else:
                                games = int(getattr(val, "games", 0))
                                wins = int(getattr(val, "wins", 0))
                            if games > 0:
                                wr = (wins / games) * 100.0
                                candidates.append((util.name_cleanup(cname), wr, games))
                        except Exception:
                            continue

                # Sort: higher winrate first, tie-breaker by games played
                candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
                picks = candidates
        except Exception:
            picks = []

        # Fallback: global champion stats (highest WR overall)
        if not picks and cm:
            try:
                candidates = []
                for cname, champ in getattr(cm, "champions", {}).items():
                    games = int(getattr(champ, "total_games", 0))
                    wins = int(getattr(champ, "total_wins", 0))
                    if games > 0:
                        wr = (wins / games) * 100.0
                        candidates.append((util.name_cleanup(cname), wr, games))
                candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
                picks = candidates[:8]
            except Exception:
                picks = []

        # Filter out currently banned/picked and optionally require a minimum sample size
        filtered = []
        banpick = set([x.lower() for x in (self.blue_bans + self.red_bans + self.blue_picks + self.red_picks)])
        for name, wr, games in picks:
            if name.lower() in banpick:
                continue
            if games < min_games:
                continue
            filtered.append((name, wr, games))
        return filtered

    # -----------------------------
    # Home side helpers
    # -----------------------------
    def set_home_side(self, side: str):
        if side not in ("blue", "red"):
            return
        self.home_side = None if self.home_side == side else side
        self.update_home_visuals()
        self.update_winrate_bar()

    def update_home_visuals(self):
        blue_color = "#3b82f6"
        red_color = "#ef4444"
        blue_text = self.selected_blue_team if self.selected_blue_team not in (None, "", "Blue Team Players") else "Blue Team"
        red_text = self.selected_red_team if self.selected_red_team not in (None, "", "Red Team Players") else "Red Team"

        if self.home_side == "blue":
            blue_text += " (Home)"
        elif self.home_side == "red":
            red_text += " (Home)"

        self.blue_team_label.setText(blue_text)
        self.red_team_label.setText(red_text)

        blue_bg = "rgba(59, 130, 246, 0.12)" if self.home_side == "blue" else "transparent"
        red_bg = "rgba(239, 68, 68, 0.12)" if self.home_side == "red" else "transparent"

        self.blue_team_label.setStyleSheet(
            f"font-size: 14px; font-weight: 700; color: {blue_color}; background-color: {blue_bg}; border-radius: 6px; padding: 2px 4px;"
        )
        self.red_team_label.setStyleSheet(
            f"font-size: 14px; font-weight: 700; color: {red_color}; background-color: {red_bg}; border-radius: 6px; padding: 2px 4px;"
        )

        self.blue_home_btn.setDisabled(self.home_side == "blue")
        self.red_home_btn.setDisabled(self.home_side == "red")

    # -----------------------------
    # Logic helpers
    # -----------------------------
    def eventFilter(self, obj, event):
        if event.type() == event.Resize:
            if obj is getattr(self, "_grid_scroll_viewport", None):
                self.update_grid_columns()
        return super().eventFilter(obj, event)

    def _read_api_key(self, path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    key = line.strip()
                    if key:
                        return key
            return ""
        except FileNotFoundError:
            print(f"API key file not found at : {path}")
            return ""
        except Exception as e:
            print(f"Error reading API key: {e}")
            return ""

    def _load_api_key(self) -> str:
        # Priority: environment variable GEMINI_API_KEY, fallback to local file api_key.txt
        key = os.getenv("GEMINI_API_KEY", "") or self._read_api_key("api_key.txt")
        return key or ""

    def _save_api_key(self, key: str, persist_to_env: bool = True):
            # Update process env immediately
        os.environ["GEMINI_API_KEY"] = key or ""
        os.environ["GOOGLE_API"] = key or ""

        self._ensure_ai_ready()
        
        if not persist_to_env:
            return
        # Try to update running manager
        try:
            if hasattr(self, "genai_manager") and self.genai_manager:
                if hasattr(self.genai_manager, "api_key"):
                    self.genai_manager.api_key = key
                else:
                    self.genai_manager = GeminiManager()
                    self.service_manager = DraftService(self.genai_manager)
                    self.service_manager.set_data_context(self.context_csv_data)
        except Exception as e:
            print(f"Could not update Gemini manager with new key: {e}")


        env_path = ".env"
        try:
            # Read existing file content (even if malformed)
            raw = ""
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    raw = f.read()

            # Normalize newlines and split into lines
            raw = raw.replace("\r\n", "\n").replace("\r", "\n")
            # If someone concatenated without newline (like ...API="x"GEMINI_API_KEY=...), split by 'GEMINI_API_KEY=' sentinel to avoid bloat
            lines = []
            if "GEMINI_API_KEY=" in raw and "\nGEMINI_API_KEY=" not in raw:
                # Insert newline before each occurrence except at start
                normalized = raw.replace("GEMINI_API_KEY=", "\nGEMINI_API_KEY=")
                # If we introduced a leading newline, strip it
                if normalized.startswith("\n"):
                    normalized = normalized[1:]
                lines = normalized.split("\n")
            else:
                lines = raw.split("\n") if raw else []

            # Parse into key=value lines, preserving non-KV lines
            cleaned = []
            seen_keys = set()
            replaced = False
            target_key = "GEMINI_API_KEY"

            def is_kv(line: str):
                # allow KEY=VALUE where KEY is alphanum + underscore
                # ignore lines like export KEY= or comments
                if not line or line.lstrip().startswith("#"):
                    return False
                return "=" in line and line.split("=", 1)[0].strip() != ""

            for line in lines:
                if not line.strip():
                    # keep blank lines to avoid collapsing formatting too much
                    cleaned.append("")
                    continue

                if is_kv(line):
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip()
                    # strip optional quotes around value without trying to be too clever
                    if k == target_key:
                        if not replaced:
                            cleaned.append(f"{target_key}={key}")
                            replaced = True
                        # else: skip duplicate occurrences
                        continue
                    # Avoid duplicate other keys: keep first occurrence only
                    if k in seen_keys:
                        # skip duplicates of other keys
                        continue
                    seen_keys.add(k)
                    cleaned.append(f"{k}={v}")
                else:
                    cleaned.append(line)

            # If not found, append at end (with a separating newline if needed)
            if not replaced:
                if cleaned and cleaned[-1] != "":
                    cleaned.append("")  # ensure a blank line before appending
                cleaned.append(f"{target_key}={key}")

            # Write back with consistent newlines and trailing newline
            with open(env_path, "w", encoding="utf-8") as f:
                f.write("\n".join(cleaned).rstrip() + "\n")

        except Exception as e:
            print(f"Could not persist API key to .env: {e}")

    def on_blue_team_combo_changed(self, text: str):
        self.selected_blue_team = text
        red_default = "Red Team Players"
        red_current = self.red_team_combo.currentText()
        exclude = text if text not in (None, "", "Blue Team Players") else None
        self.repopulate_combo_excluding(
            combo=self.red_team_combo,
            default_label=red_default,
            excluded=exclude or "",
            keep_current=red_current,
        )
        self.update_home_visuals()
        self.update_winrate_bar()
        self.update_all_deltas()
        self.refresh_team_stats()

    def on_red_team_combo_changed(self, text: str):
        self.selected_red_team = text
        blue_default = "Blue Team Players"
        blue_current = self.blue_team_combo.currentText()
        exclude = text if text not in (None, "", "Red Team Players") else None
        self.repopulate_combo_excluding(
            combo=self.blue_team_combo,
            default_label=blue_default,
            excluded=exclude or "",
            keep_current=blue_current,
        )
        self.update_home_visuals()
        self.update_winrate_bar()
        self.update_all_deltas()
        self.refresh_team_stats()

    def get_all_team_names(self):
        tm = getattr(self.main_manager, "team_manager", None)
        if tm is None:
            return []
        team_obj = getattr(tm, "teams", None)
        names = []
        if isinstance(team_obj, dict):
            for _, team in team_obj.items():
                name = getattr(team, "name", None)
                if name:
                    names.append(name)
        return sorted(set(names))

    def build_team_master_list(self):
        return self.get_all_team_names()

    def repopulate_combo_excluding(self, combo: QComboBox, default_label: str, excluded: str, keep_current: str):
        master = getattr(self, "team_master_list", [])
        items = [default_label]
        for name in master:
            if name == excluded and keep_current != name:
                continue
            items.append(name)

        combo.blockSignals(True)
        current_text = combo.currentText()
        combo.clear()
        combo.addItems(items)
        target = current_text if current_text in items else (keep_current if keep_current in items else default_label)
        idx = combo.findText(target)
        combo.setCurrentIndex(idx if idx >= 0 else 0)
        combo.blockSignals(False)

    def calculate_delta_wr(self):
        for champion_name, tile in self.champion_tiles_dict.items():
            if champion_name in self.available_champions:
                delta = self.calculate_champion_delta(champion_name)
                tile.set_delta_winrate(delta)

    def calculate_champion_delta(self):
        base_blue, base_red = self._current_blue_red_probs()

        is_blue_turn = "blue" in self.current_turn
        is_pick = "pick" in self.current_turn
        is_ban = "ban" in self.current_turn

        for champ_key, tile in self.champion_tiles_dict.items():
            if champ_key not in self.available_champions:
                tile.set_delta_winrate(0.0)
                continue

            blue_bans = list(self.blue_bans)
            red_bans = list(self.red_bans)
            blue_picks = list(self.blue_picks)
            red_picks = list(self.red_picks)

            if is_pick:
                if is_blue_turn:
                    blue_picks.append(tile.champion_name)
                else:
                    red_picks.append(tile.champion_name)
            elif is_ban:
                if is_blue_turn:
                    blue_bans.append(tile.champion_name)
                else:
                    red_bans.append(tile.champion_name)

            hyp_blue, hyp_red = self._predict_draft_probs(blue_bans, red_bans, blue_picks, red_picks)
            delta = (hyp_blue - base_blue) if is_blue_turn else (hyp_red - base_red)
            tile.set_delta_winrate(delta)

    def _predict_draft_probs(self, blue_bans, red_bans, blue_picks, red_picks):
        proba = self._predict_proba_from_lists(blue_bans, red_bans, blue_picks, red_picks)
        if proba is None:
            return 50.0, 50.0
        p_other, p_team = float(proba[0][0]), float(proba[0][1])
        blue_pct = p_other * 100.0
        red_pct = p_team * 100.0
        return blue_pct, red_pct

    def update_all_deltas(self):
        self.calculate_champion_delta()
        for tile in self.champion_tiles_dict.values():
            tile.update_style()
        self.filter_champions(self.search_bar.text())

    def on_window_resize(self, event):
        super().resizeEvent(event)
        # Two passes to catch layout settling
        QTimer.singleShot(0, self.update_grid_columns)
        QTimer.singleShot(60, self.update_grid_columns)

    def update_grid_columns(self):
        if not self.champion_tiles:
            return

        vp = getattr(self, "_grid_scroll_viewport", None)
        width = vp.width() if vp is not None else self.grid_container.width()

        # Subtract viewport margins we set (12 left + 12 right)
        usable = max(0, width - 16)

        # Estimate per column width: tile body + grid spacing
        # Tile base: ChampionTile(size=82) has min/max width between ~94–110; use a conservative 98
        tile_body = 94
        spacing = self.grid_layout.spacing()  # 10
        per_col = tile_body + spacing

        # Compute columns to fit without horizontal scroll
        new_cols = int(max(1, min(20, usable // per_col)))

        if new_cols != self.current_cols:
            self.current_cols = new_cols
            self.filter_champions(self.search_bar.text())

    def arrange_grid(self, tiles, columns):
        if not tiles:
            no_results = QLabel("No champions found.")
            no_results.setAlignment(Qt.AlignCenter)
            no_results.setStyleSheet("font-size: 14px; color: #9a9a9a; padding: 40px;")
            self.grid_layout.addWidget(no_results, 0, 0, alignment=Qt.AlignCenter)
            return

        for i, tile in enumerate(tiles):
            row = i // columns
            col = i % columns
            self.grid_layout.addWidget(tile, row, col, Qt.AlignLeft | Qt.AlignTop)

        # Do not add filler widgets; they can force extra width

    def filter_champions(self, search_text):
        search_text = (search_text or "").lower().strip()
        self.clear_grid()
        visible_tiles = []
        for tile in self.champion_tiles:
            champ_name = tile.champion_name
            champ_key = champ_name.lower()
            is_visible = champ_key in self.available_champions
            if search_text:
                is_visible = is_visible and (search_text in champ_name.lower())
            if is_visible:
                visible_tiles.append(tile)

        key, asc = self.sort_mode
        visible_tiles.sort(key=self._tile_sort_key, reverse=not asc)

        self.arrange_grid(visible_tiles, self.current_cols)

    def clear_grid(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item:
                widget = item.widget()
                if widget:
                    widget.setParent(None)

    def load_champions(self):
        folder = images_path
        if not os.path.exists(folder) or not os.path.isdir(folder):
            print(f"Image folder '{folder}' does not exist or is empty... attempting to regenerate files")
            
            if not hasattr(sys,"_MEIPASS"):
                util.fetch_champions()

        image_paths = [
            os.path.join(folder, f)
            for f in os.listdir(folder)
            if f.lower().endswith(".png")
        ]

        for i in reversed(range(self.grid_layout.count())):
            w = self.grid_layout.itemAt(i).widget()
            if w:
                w.setParent(None)

        self.all_champions.clear()
        self.champion_tiles.clear()
        self.champion_tiles_dict.clear()

        for path in image_paths:
            try:
                filename = os.path.splitext(os.path.basename(path))[0]
                champion_name = util.name_cleanup(filename)
                champ_key = champion_name.lower()

                tile = ChampionTile(champion_name, path, size=82)
                tile.clicked.connect(lambda name=champion_name: self.champion_clicked(name))

                gp_text = "--"
                wr_text = "--"
                try:
                    champ_obj = self.main_manager.champion_manager.get_champion(champion_name)
                    if champ_obj is not None:
                        wr_text = f"{champ_obj.overall_winrate:.1f}%"
                        gp_text = f"{champ_obj.total_games}"
                        tile.general_winrate_label.setToolTip(
                            f"Winrate ({champ_obj.total_wins} wins/{champ_obj.total_games} games * 100)"
                        )
                except Exception as e:
                    print(f"Error loading winrate for {champion_name}: {e}")
                    print("Data may not be present")

                tile.set_general_wr_colored(wr_text)
                tile.games_played_label.setText(gp_text)
                tile.games_played_label.setToolTip(f"Games played: {gp_text}")

                self.champion_tiles_dict[champ_key] = tile
                self.champion_tiles.append(tile)
                self.all_champions[champ_key] = {
                    "name": champion_name,
                    "path": path,
                    "tile": tile
                }
            except Exception as e:
                print(f"Error loading {path}: {e}")
                traceback.print_exc()
                continue

        self.available_champions = list(self.all_champions.keys())
        QTimer.singleShot(0, self.update_grid_columns)
        print(f"Loaded {len(self.all_champions)} champions")

    def champion_clicked(self, champion_name):
        champ_key = champion_name.lower()
        if champ_key not in self.available_champions:
            return
        if "ban" in self.current_turn:
            self.ban_champion(champion_name)
        else:
            self.pick_champion(champion_name)
        self.filter_champions(self.search_bar.text())
        self.update_all_deltas()
        self.refresh_team_stats()

    def ban_champion(self, champion_name):
        champ_key = champion_name.lower()
        champ_data = self.all_champions[champ_key]
        champ_data["tile"].set_banned(True)
        self.available_champions.remove(champ_key)

        if "blue" in self.current_turn:
            self.blue_bans.append(champion_name)
            slot_index = len(self.blue_bans) - 1
            if slot_index < len(self.blue_ban_slots):
                self.blue_ban_slots[slot_index].set_champion(champion_name, champ_data["path"])
        else:
            self.red_bans.append(champion_name)
            slot_index = len(self.red_bans) - 1
            if slot_index < len(self.red_ban_slots):
                self.red_ban_slots[slot_index].set_champion(champion_name, champ_data["path"])

        self.update_turn()
        self.update_winrate_bar()
        self.refresh_team_stats()

    def pick_champion(self, champion_name):
        champ_key = champion_name.lower()
        champ_data = self.all_champions[champ_key]
        champ_data["tile"].set_picked(True)
        if champ_key in self.available_champions:
            self.available_champions.remove(champ_key)

        if "blue" in self.current_turn:
            self.blue_picks.append(champion_name)
            for player in self.players["blue"]:
                if player.champion is None:
                    player.set_champion(champion_name, champ_data["path"])
                    break
        else:
            self.red_picks.append(champion_name)
            for player in self.players["red"]:
                if player.champion is None:
                    player.set_champion(champion_name, champ_data["path"])
                    break

        self.update_turn()
        self.update_winrate_bar()
        self.refresh_team_stats()

    def update_winrate_bar(self):
        try:
            proba = self._predict_for_side()
            if proba is None:
                return
            p_other = float(proba[0][0])
            p_team = float(proba[0][1])

            red_pct = p_team * 100.0
            blue_pct = p_other * 100.0

            blue_pct = max(0.0, min(100.0, blue_pct))
            red_pct = max(0.0, min(100.0, red_pct))
            if not hasattr(self, "prob_bar"):
                self.prob_bar = None
            if self.prob_bar is not None:
                self.prob_bar.set_values(blue_pct, red_pct)
        except Exception as e:
            print("update_winrate_bar error:", e)

    def update_turn(self, first=False):
        turn_seq = [
            "blue_ban", "red_ban", "blue_ban", "red_ban", "blue_ban",
            "red_ban", "blue_pick", "red_pick", "red_pick", "blue_pick",
            "blue_pick", "red_pick", "red_ban", "blue_ban",
            "red_ban", "blue_ban", "red_pick", "blue_pick",
            "blue_pick", "red_pick"
        ]

        if first:
            self.current_turn = turn_seq[0]
            self.turn_counter = 0
        else:
            self.turn_counter += 1
            if self.turn_counter < len(turn_seq):
                self.current_turn = turn_seq[self.turn_counter]
            else:
                self.current_turn = "draft_complete"
                self.turn_counter = 20

        if self.current_turn == "draft_complete":
            self.turn_counter = 20
            self.turn_label.setText("Draft Complete!")
            self.turn_label.setStyleSheet("font-size: 18px; font-weight: 700; color: #eaeaea;")
            for tile in self.champion_tiles:
                tile.set_interactive(False)
        elif "blue" in self.current_turn:
            team_color = "#93c5fd"
            action = "Ban" if "ban" in self.current_turn else "Pick"
            self.turn_label.setText(f"Blue Team's turn to {action}")
            self.turn_label.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {team_color};")
            for tile in self.champion_tiles:
                tile.set_interactive(True)
        else:
            team_color = "#fca5a5"
            action = "Ban" if "ban" in self.current_turn else "Pick"
            self.turn_label.setText(f"Red Team's turn to {action}")
            self.turn_label.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {team_color};")
            for tile in self.champion_tiles:
                tile.set_interactive(True)

    def _compute_next_turn(self) -> str:
        # Mirror turn sequence to compute next turn string that DraftService expects
        turn_seq = [
            "blue_ban", "red_ban", "blue_ban", "red_ban", "blue_ban",
            "red_ban", "blue_pick", "red_pick", "red_pick", "blue_pick",
            "blue_pick", "red_pick", "red_ban", "blue_ban",
            "red_ban", "blue_ban", "red_pick", "blue_pick",
            "blue_pick", "red_pick"
        ]
        try:
            idx = turn_seq.index(self.current_turn)
            if idx + 1 < len(turn_seq):
                return turn_seq[idx + 1]
            return "draft_complete"
        except ValueError:
            return "draft_complete"

    def refresh_general_winrates(self):
        cm = getattr(self.main_manager, "champion_manager", None)
        if cm is None:
            return
        for champ_key, data in self.all_champions.items():
            champ_name = data["name"]
            tile = data["tile"]
            champ_obj = cm.get_champion(champ_name)
            if champ_obj:
                wr_text = f"{champ_obj.overall_winrate:.1f}%"
            else:
                wr_text = "--"

            current_right = tile.games_played_label.text() or "Next --"
            tile.set_info_texts(wr_text, current_right)

    def reset_draft(self):
        for champ_data in self.all_champions.values():
            champ_data["tile"].set_banned(False)
            champ_data["tile"].set_picked(False)

        for tile in self.champion_tiles:
            if tile:
                tile.set_interactive(True)
        
        
        self.available_champions = list(self.all_champions.keys())
        self.red_bans = []
        self.blue_bans = []
        self.red_picks = []
        self.blue_picks = []
        self.update_turn(first=True)

        for slot in self.blue_ban_slots + self.red_ban_slots:
            slot.clear_champion()

        for team in ["blue", "red"]:
            for player in self.players[team]:
                player.champion = None
                player.champion_slot.clear()
                player.champion_slot.setText("Lock in")
                player.champion_slot.setStyleSheet("""
                    QLabel {
                        border: 2px dashed #5a5a5a;
                        border-radius: 8px;
                        background-color: #1f1f1f;
                        font-size: 10px;
                        color: #999;
                    }
                """)

        self.filter_champions(self.search_bar.text())
        self.update_winrate_bar()
        self.suggestions_panel.clear_suggestions()
        # Clear predictions when resetting as well
        if hasattr(self, "predictions_panel"):
            self.predictions_panel.clear_predictions()
        self.refresh_team_stats()
        QTimer.singleShot(0, self.update_grid_columns)

    def random_ban(self):
        if self.available_champions and "ban" in self.current_turn:
            random_champ = random.choice(self.available_champions)
            champ_data = self.all_champions[random_champ]
            self.ban_champion(champ_data["name"])

    def random_pick(self):
        if self.available_champions and "pick" in self.current_turn:
            random_champ = random.choice(self.available_champions)
            champ_data = self.all_champions[random_champ]
            self.pick_champion(champ_data["name"])

    def _current_blue_red_probs(self):
        proba = self._predict_proba_from_lists(self.blue_bans, self.red_bans, self.blue_picks, self.red_picks)
        if proba is None:
            return 50.0, 50.0
        p_other, p_team = float(proba[0][0]), float(proba[0][1])
        blue_pct = p_other * 100.0
        red_pct = p_team * 100.0
        return blue_pct, red_pct

    def _current_team_names(self):
        blue_team = self.selected_blue_team or "Blue Team"
        red_team = self.selected_red_team or "Red Team"
        return blue_team, red_team

    def _current_team_and_opponent(self):
        blue_team, red_team = self._current_team_names()
        blue_team = blue_team or "Blue Team"
        red_team = red_team or "Red Team"
        return red_team, blue_team

    def _collect_bans_picks(self):
        bans = (self.blue_bans + self.red_bans)[:10]
        picks = (self.blue_picks + self.red_picks)[:10]
        bans += ["a"] * (10 - len(bans))
        picks += ["a"] * (10 - len(picks))
        return bans, picks

    def _collect_bans_picks_from_lists(self, blue_bans, red_bans, blue_picks, red_picks):
        bans = (blue_bans + red_bans)[:10]
        picks = (blue_picks + red_picks)[:10]
        bans += ["a"] * (10 - len(bans))
        picks += ["a"] * (10 - len(picks))
        return bans, picks

    def _build_row_from_lists(self, blue_bans, red_bans, blue_picks, red_picks):
        team, opponent = self._current_team_and_opponent()
        bans, picks = self._collect_bans_picks_from_lists(blue_bans, red_bans, blue_picks, red_picks)

        row = {col: 0 for col in self.cb_expected}
        for c in self.cb_cat_cols:
            if c in row:
                row[c] = "a"

        if "Teams" in row: row["Teams"] = team
        if "Opponent" in row: row["Opponent"] = opponent

        for i in range(10):
            key = f"Ban{i+1}"
            if key in row:
                row[key] = bans[i] if i < len(bans) else ""

        for i in range(10):
            key = f"Pick{i+1}"
            if key in row:
                row[key] = picks[i] if i < len(picks) else ""

        return row

    def _build_row_for_side(self):
        team, opponent = self._current_team_and_opponent()
        bans, picks = self._collect_bans_picks()

        row = {col: 0 for col in self.cb_expected}
        for c in self.cb_cat_cols:
            if c in row:
                row[c] = "a"

        if "Teams" in row: row["Teams"] = team
        if "Opponent" in row: row["Opponent"] = opponent

        for i in range(10):
            key = f"Ban{i+1}"
            if key in row:
                row[key] = bans[i] if i < len(bans) else ""

        for i in range(10):
            key = f"Pick{i+1}"
            if key in row:
                row[key] = picks[i] if i < len(picks) else ""

        return row

    def _predict_proba_from_lists(self, blue_bans, red_bans, blue_picks, red_picks):
        row = self._build_row_from_lists(blue_bans, red_bans, blue_picks, red_picks)
        df = pd.DataFrame([row])[self.cb_expected]
        pool = Pool(df, cat_features=self.cb_cat_idx)
        try:
            proba = self.cb_model.predict_proba(pool)
        except Exception as e:
            print(f"Error predicting: {e}")
            return
        return proba

    def _predict_for_side(self):
        row = self._build_row_for_side()
        df = pd.DataFrame([row])[self.cb_expected]
        pool = Pool(df, cat_features=self.cb_cat_idx)
        try:
            proba = self.cb_model.predict_proba(pool)
        except Exception as e:
            print(f"Error predicting: {e}")
            return
        return proba


# -----------------------------
# Entry point
# -----------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    app.setStyleSheet("""
        QMainWindow { background-color: #1a1a1a; }
        QWidget { font-family: 'Segoe UI', Arial, sans-serif; color: #eaeaea; }
        QScrollBar:vertical {
            background: #1f1f1f; width: 10px; margin: 2px; border-radius: 6px;
        }
        QScrollBar::handle:vertical {
            background: #3a3a3a; border-radius: 6px; min-height: 20px;
        }
        QScrollBar::handle:vertical:hover { background: #4a4a4a; }
        QToolTip { color: #eaeaea; background-color: #2a2a2a; border: 1px solid #3a3a3a; }
    """)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
