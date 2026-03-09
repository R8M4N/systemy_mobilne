from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGridLayout, QProgressBar, QFrame
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QFont, QBrush, QPen
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class ChannelWidget(QWidget):
    def __init__(self, channel_id, parent=None):
        super().__init__(parent)
        self.channel_id = channel_id
        self.is_busy = False
        self.remaining = 0
        self.served = 0
        self.setMinimumSize(80, 50)
        self.setMaximumSize(120, 60)
        self._color = QColor("#2d6a4f")

    def update_state(self, is_busy, remaining, duration, served):
        self.is_busy = is_busy
        self.remaining = int(remaining)
        self.served = served
        self._color = QColor("#e63946") if is_busy else QColor("#2d6a4f")
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setBrush(QBrush(self._color))
        painter.setPen(QPen(QColor("#0d1117"), 2))
        painter.drawRoundedRect(2, 2, self.width() - 4, self.height() - 4, 8, 8)

        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        text = f"{self.remaining}s" if self.is_busy else "—"
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)

        # numer kanału w rogu
        painter.setFont(QFont("Segoe UI", 7))
        painter.setPen(QColor("#aaaaaa"))
        painter.drawText(8, 14, f"#{self.channel_id + 1}")
        painter.end()


class ChannelsGridWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout_ = QGridLayout(self)
        self.layout_.setSpacing(6)
        self.channel_widgets = []

    def setup_channels(self, count):
        for w in self.channel_widgets:
            self.layout_.removeWidget(w)
            w.deleteLater()
        self.channel_widgets.clear()

        # ile kolumn - coś sensownego dla różnych ilości kanałów
        cols = max(2, min(6, int(count ** 0.5) + 1))
        for i in range(count):
            cw = ChannelWidget(i)
            self.channel_widgets.append(cw)
            self.layout_.addWidget(cw, i // cols, i % cols)

    def update_channels(self, channels_data):
        for i, (is_busy, remaining, duration, served) in enumerate(channels_data):
            if i < len(self.channel_widgets):
                self.channel_widgets[i].update_state(is_busy, remaining, duration, served)


class QueueWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #30363d;
                border-radius: 5px;
                background: #161b22;
                height: 22px;
                text-align: center;
                color: #e6edf3;
                font-size: 11px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #e94560, stop:1 #0f3460);
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.progress)

    def update_queue(self, current, maximum):
        self.progress.setMaximum(maximum)
        self.progress.setValue(current)
        self.progress.setFormat(f"Kolejka: {current} / {maximum}")


class ChartWidget(FigureCanvas):
    #Liniowy wykres z ciemnym motywem

    def __init__(self, title, color, ylabel, parent=None):
        self.fig = Figure(figsize=(4, 2.2), dpi=100)
        self.fig.patch.set_facecolor('#0d1117')
        super().__init__(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.title = title
        self.color = color
        self.ylabel = ylabel
        self._apply_style()

    def _apply_style(self):
        self.ax.set_facecolor('#161b22')
        self.ax.set_title(self.title, color='#e6edf3', fontsize=11, fontweight='bold', pad=8)
        self.ax.tick_params(colors='#8b949e', labelsize=8)
        self.ax.spines['bottom'].set_color('#30363d')
        self.ax.spines['left'].set_color('#30363d')
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.set_ylabel(self.ylabel, color='#8b949e', fontsize=9)
        self.ax.set_xlabel('Czas [s]', color='#8b949e', fontsize=9)
        self.fig.tight_layout(pad=1.5)

    def update_chart(self, x_data, y_data):
        self.ax.clear()
        self._apply_style()
        if x_data and y_data:
            self.ax.plot(x_data, y_data, color=self.color, linewidth=2, alpha=0.9)
            self.ax.fill_between(x_data, y_data, alpha=0.15, color=self.color)
            self.ax.set_ylim(bottom=0)
        self.fig.tight_layout(pad=1.5)
        self.draw()

    def reset(self):
        self.ax.clear()
        self._apply_style()
        self.draw()


class StatsPanel(QFrame):
    #panel statystyk

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background: #161b22;
                border: 1px solid #30363d;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        self.served_label = self._make_label("Obsłużone: 0")
        self.rejected_label = self._make_label("Odrzucone: 0")
        self.rho_label = self._make_label("ρ: 0.0000")
        self.q_label = self._make_label("Q: 0.0000")
        self.w_label = self._make_label("W: 0.0000 s")

        for lbl in [self.served_label, self.rejected_label,
                    self.rho_label, self.q_label, self.w_label]:
            layout.addWidget(lbl)

    def _make_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #e6edf3; font-size: 12px; border: none; font-family: 'Segoe UI';")
        return lbl

    def update_stats(self, served, rejected, rho, q, w):
        self.served_label.setText(f"Obsłużone: {served}")
        self.rejected_label.setText(f"Odrzucone: {rejected}")
        self.rho_label.setText(f"ρ: {rho:.4f}")
        self.q_label.setText(f"Q: {q:.4f}")
        self.w_label.setText(f"W: {w:.4f} s")


class PieChartWidget(FigureCanvas):
    #Kołowy wykres obsłużone vs odrzucone

    def __init__(self, parent=None):
        self.fig = Figure(figsize=(3, 2.2), dpi=100)
        self.fig.patch.set_facecolor('#0d1117')
        super().__init__(self.fig)
        self.ax = self.fig.add_subplot(111)
        self._setup_empty()

    def _safe_layout(self):
        # tight_layout rzuca ValueError jeśli widget nie ma jeszcze wymiarów
        try:
            self.fig.tight_layout(pad=1.5)
        except ValueError:
            pass

    def _setup_empty(self):
        self.ax.clear()
        self.ax.set_facecolor('#0d1117')
        self.ax.set_title('Obsłużone / Odrzucone', color='#e6edf3', fontsize=11, fontweight='bold', pad=8)
        self.ax.text(0.5, 0.5, 'Brak danych', ha='center', va='center',
                     color='#484f58', fontsize=10, transform=self.ax.transAxes)
        self.ax.axis('off')
        self._safe_layout()
        self.draw()

    def update_pie(self, served, rejected):
        self.ax.clear()
        self.ax.set_facecolor('#0d1117')
        self.ax.set_title('Obsłużone / Odrzucone', color='#e6edf3', fontsize=11, fontweight='bold', pad=8)

        if served + rejected == 0:
            self.ax.text(0.5, 0.5, 'Brak danych', ha='center', va='center',
                         color='#484f58', fontsize=10, transform=self.ax.transAxes)
            self.ax.axis('off')
        else:
            self.ax.pie(
                [served, rejected],
                labels=[f'Obsłużone\n{served}', f'Odrzucone\n{rejected}'],
                colors=['#2d6a4f', '#e94560'],
                explode=(0.03, 0.03),
                startangle=90,
                textprops={'color': '#e6edf3', 'fontsize': 9}
            )
        self._safe_layout()
        self.draw()

    def reset(self):
        self._setup_empty()
