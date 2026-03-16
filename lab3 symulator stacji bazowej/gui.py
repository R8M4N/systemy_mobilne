from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QSpinBox, QDoubleSpinBox, QPushButton, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPolygon
from widgets import ChannelsGridWidget, QueueWidget, ChartWidget, StatsPanel
from simulation import SimulationEngine
import os

_LABEL_STYLE = "color: #e6edf3; font-size: 12px;"
_GROUP_STYLE = """
    QGroupBox {
        background: #161b22; border: 1px solid #30363d; border-radius: 10px;
        margin-top: 14px; padding-top: 14px;
        font-size: 13px; font-weight: bold; color: #58a6ff;
    }
    QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
"""
_TABLE_STYLE = """
    QTableWidget {
        background: #0d1117; color: #e6edf3; border: none;
        gridline-color: #21262d; font-size: 11px;
    }
    QHeaderView::section {
        background: #161b22; color: #58a6ff;
        border: 1px solid #21262d; padding: 4px; font-weight: bold;
    }
    QTableWidget::item { padding: 2px 4px; }
"""

def _btn_style(bg, hover):
    return (f"QPushButton {{ background:{bg}; color:#fff; border:none; border-radius:8px;"
            f" padding:10px 20px; font-size:14px; font-weight:bold; font-family:'Segoe UI'; }}"
            f"QPushButton:hover {{ background:{hover}; }}"
            f"QPushButton:disabled {{ background:#21262d; color:#484f58; }}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Symulator Stacji Bazowej - Michał Romańczyk")
        self.setMinimumSize(1300, 800)
        self.resize(1500, 900)
        self.engine = None
        self.timer = QTimer()
        self.timer.timeout.connect(self._simulation_step)
        self.is_running = False
        self._generate_arrow_icons()
        self._build_ui()

    def _generate_arrow_icons(self):
        arrow_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_arrows")
        os.makedirs(arrow_dir, exist_ok=True)
        self._up_icon   = os.path.join(arrow_dir, "up.png").replace("\\", "/")
        self._down_icon = os.path.join(arrow_dir, "down.png").replace("\\", "/")
        if not os.path.exists(self._up_icon):
            for path, pts in [
                (self._up_icon,   [QPoint(2,8), QPoint(8,2), QPoint(14,8)]),
                (self._down_icon, [QPoint(2,2), QPoint(8,8), QPoint(14,2)]),
            ]:
                px = QPixmap(16, 10)
                px.fill(QColor(0, 0, 0, 0))
                p = QPainter(px)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                p.setBrush(QColor("#8b949e")); p.setPen(QColor("#8b949e"))
                p.drawPolygon(QPolygon(pts)); p.end()
                px.save(path)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # --- lewa kolumna ---
        left_col = QVBoxLayout()
        left_col.setSpacing(10)

        params_group = QGroupBox("Parametry")
        params_group.setStyleSheet(_GROUP_STYLE)
        gl = QGridLayout(params_group)
        gl.setSpacing(6)

        # (row, label, cls, min, max, default, decimals)
        spin_defs = [
            (0, "Liczba kanałów:",      QSpinBox,       1,    50,    10, None),
            (1, "Długość kolejki:",     QSpinBox,       1,   100,    10, None),
            (2, "λ (Poisson):",        QDoubleSpinBox, 0.01,100.0, 1.0, 2),
            (3, "N (śr. rozmowy):",    QDoubleSpinBox, 1.0,1000.0,20.0, 1),
            (4, "σ (odch. std.):",     QDoubleSpinBox, 0.1, 100.0, 5.0, 1),
            (5, "Min rozmowy [s]:",    QSpinBox,       1,   999,    10, None),
            (6, "Maks rozmowy [s]:",   QSpinBox,       1,   999,    30, None),
            (7, "Czas symulacji [s]:", QSpinBox,       1,  9999,    60, None),
            (8, "Prędkość [ms/krok]:", QSpinBox,       50, 2000,   300, None),
        ]
        attr_names = ["spin_channels","spin_queue","spin_lambda","spin_n","spin_sigma",
                      "spin_min","spin_max","spin_sim_time","spin_speed"]
        for (row, lbl, cls, mn, mx, df, dec), attr in zip(spin_defs, attr_names):
            setattr(self, attr, self._add_spin(gl, row, lbl, cls, mn, mx, df, dec))

        left_col.addWidget(params_group)

        btn_layout = QHBoxLayout()
        self.btn_start   = self._make_btn("START",   "#2d6a4f","#40916c", self._toggle_simulation)
        self.btn_restart = self._make_btn("RESTART", "#e94560","#ff6b6b", self._restart_simulation, enabled=False)
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_restart)
        left_col.addLayout(btn_layout)

        self.time_label = QLabel("Czas: 0 / 0 s")
        self.time_label.setStyleSheet("color:#e6edf3; font-size:14px; font-weight:bold; font-family:'Segoe UI';")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_col.addWidget(self.time_label)

        results_group = QGroupBox("Wyniki symulacji")
        results_group.setStyleSheet(_GROUP_STYLE)
        rl = QVBoxLayout(results_group)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Czas", "ρ", "Q", "W"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet(_TABLE_STYLE)
        self.table.verticalHeader().setVisible(False)
        rl.addWidget(self.table)
        left_col.addWidget(results_group, 1)
        main_layout.addLayout(left_col, 2)

        # --- środkowa kolumna ---
        mid_col = QVBoxLayout()
        mid_col.setSpacing(10)
        channels_group = self._make_group("Kanały")
        self.channels_grid = ChannelsGridWidget()
        channels_group.layout().addWidget(self.channels_grid)
        mid_col.addWidget(channels_group, 3)

        queue_group = self._make_group("Kolejka")
        self.queue_widget = QueueWidget()
        queue_group.layout().addWidget(self.queue_widget)
        mid_col.addWidget(queue_group)

        self.stats_panel = StatsPanel()
        mid_col.addWidget(self.stats_panel)
        main_layout.addLayout(mid_col, 2)

        # --- prawa kolumna: wykresy liniowe ---
        right_col = QVBoxLayout()
        right_col.setSpacing(8)
        self.chart_rho = ChartWidget("ρ — Intensywność ruchu",      "#2d6a4f", "ρ")
        self.chart_q   = ChartWidget("Q — Średnia dł. kolejki",     "#e94560", "Q")
        self.chart_w   = ChartWidget("W — Średni czas oczekiwania", "#58a6ff", "W [s]")
        for chart in [self.chart_rho, self.chart_q, self.chart_w]:
            right_col.addWidget(chart)
        main_layout.addLayout(right_col, 3)

    # ------------------------------------------------------------------ helpers

    def _make_btn(self, text, bg, hover, slot, enabled=True):
        btn = QPushButton(text)
        btn.setStyleSheet(_btn_style(bg, hover))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(slot)
        btn.setEnabled(enabled)
        return btn

    def _make_group(self, title):
        g = QGroupBox(title)
        g.setStyleSheet(_GROUP_STYLE)
        QVBoxLayout(g)
        return g

    def _add_spin(self, layout, row, label_text, spin_cls, min_val, max_val, default, decimals=None):
        lbl = QLabel(label_text)
        lbl.setStyleSheet(_LABEL_STYLE)
        spin = spin_cls()
        spin.setRange(min_val, max_val)
        spin.setValue(default)
        if decimals is not None:
            spin.setDecimals(decimals)
            spin.setSingleStep(0.1)
        spin.setStyleSheet(self._spin_style())
        layout.addWidget(lbl, row, 0)
        layout.addWidget(spin, row, 1)
        return spin

    def _spin_style(self):
        up, dn = self._up_icon, self._down_icon
        return f"""
            QSpinBox, QDoubleSpinBox {{
                background:#0d1117; color:#e6edf3;
                border:1px solid #30363d; border-radius:5px;
                padding:4px 8px; font-size:12px; min-width:80px;
            }}
            QSpinBox:focus, QDoubleSpinBox:focus {{ border-color:#58a6ff; }}
            QSpinBox::up-button, QDoubleSpinBox::up-button {{
                subcontrol-origin:border; subcontrol-position:top right;
                width:20px; background:#21262d;
                border-left:1px solid #30363d; border-bottom:1px solid #30363d;
                border-top-right-radius:4px;
            }}
            QSpinBox::down-button, QDoubleSpinBox::down-button {{
                subcontrol-origin:border; subcontrol-position:bottom right;
                width:20px; background:#21262d;
                border-left:1px solid #30363d; border-bottom-right-radius:4px;
            }}
            QSpinBox::up-arrow, QDoubleSpinBox::up-arrow   {{ image:url({up}); width:10px; height:6px; }}
            QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{ image:url({dn}); width:10px; height:6px; }}
            QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
            QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{ background:#30363d; }}
        """

    # ------------------------------------------------------------------ simulation logic

    def _toggle_simulation(self):
        if not self.is_running:
            if self.engine is None:
                self._start_simulation()
            else:
                self.timer.start(self.spin_speed.value())
                self.is_running = True
                self.btn_start.setText("STOP")
                self.btn_start.setStyleSheet(_btn_style("#e76f51", "#f4a261"))
                self._set_params_enabled(False)
        else:
            self.timer.stop()
            self.is_running = False
            self.btn_start.setText("START")
            self.btn_start.setStyleSheet(_btn_style("#2d6a4f", "#40916c"))

    def _start_simulation(self):
        num_ch, queue_size = self.spin_channels.value(), self.spin_queue.value()
        lam    = self.spin_lambda.value()
        n_mean = self.spin_n.value()
        sigma  = self.spin_sigma.value()
        min_dur, max_dur = self.spin_min.value(), self.spin_max.value()
        sim_time = self.spin_sim_time.value()

        if min_dur >= max_dur:
            max_dur = min_dur + 1
            self.spin_max.setValue(max_dur)

        self.engine = SimulationEngine(num_ch, queue_size, lam, n_mean, sigma, min_dur, max_dur, sim_time)
        self.channels_grid.setup_channels(num_ch)
        self.queue_widget.update_queue(0, queue_size)
        self.table.setRowCount(0)
        for chart in [self.chart_rho, self.chart_q, self.chart_w]:
            chart.reset()

        self.timer.start(self.spin_speed.value())
        self.is_running = True
        self.btn_start.setText("STOP")
        self.btn_start.setStyleSheet(_btn_style("#e76f51", "#f4a261"))
        self.btn_restart.setEnabled(True)
        self._set_params_enabled(False)

    def _restart_simulation(self):
        self.timer.stop()
        self.is_running = False
        self.engine = None
        self.btn_start.setText("START")
        self.btn_start.setStyleSheet(_btn_style("#2d6a4f", "#40916c"))
        self.btn_restart.setEnabled(False)
        self._set_params_enabled(True)
        self.time_label.setText("Czas: 0 / 0 s")
        self.channels_grid.setup_channels(self.spin_channels.value())
        self.queue_widget.update_queue(0, self.spin_queue.value())
        self.stats_panel.update_stats(0, 0, 0, 0, 0)
        self.table.setRowCount(0)
        for chart in [self.chart_rho, self.chart_q, self.chart_w]:
            chart.reset()

    def _simulation_step(self):
        if self.engine is None:
            return
        result = self.engine.step()

        if not result.finished:
            self.channels_grid.update_channels(result.channels)
            self.queue_widget.update_queue(result.queue_len, self.spin_queue.value())
            self.time_label.setText(f"Czas: {result.current_time} / {self.spin_sim_time.value()} s")
            self.stats_panel.update_stats(
                result.total_served, result.rejected, result.rho, result.avg_q, result.avg_w)
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, val in enumerate([str(result.current_time),
                                       f"{result.rho:.4f}", f"{result.avg_q:.4f}", f"{result.avg_w:.4f}"]):
                self.table.setItem(row, col, QTableWidgetItem(val))
            self.table.scrollToBottom()
            if result.current_time % 2 == 0 or result.current_time <= 5:
                self._update_charts()

        if result.finished:
            self.timer.stop()
            self.is_running = False
            self.btn_start.setText("START")
            self.btn_start.setStyleSheet(_btn_style("#2d6a4f", "#40916c"))
            self.btn_start.setEnabled(False)
            self._update_charts()
            self._save_results()

    def _update_charts(self):
        for chart, hist in zip(
            [self.chart_rho, self.chart_q, self.chart_w],
            [self.engine.rho_history, self.engine.q_history, self.engine.w_history]
        ):
            chart.update_chart(self.engine.time_history, hist)

    def _save_results(self):
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wyniki_symulacji.txt")
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.engine.get_results_for_file())
            self.time_label.setText(
                f"Czas: {self.engine.current_time} / {self.spin_sim_time.value()} s  —  Wyniki zapisane!")
        except Exception as e:
            self.time_label.setText(f"Błąd zapisu: {e}")

    def _set_params_enabled(self, enabled):
        for spin in [self.spin_channels, self.spin_queue, self.spin_lambda,
                     self.spin_n, self.spin_sigma, self.spin_min, self.spin_max, self.spin_sim_time]:
            spin.setEnabled(enabled)
        if enabled:
            self.btn_start.setEnabled(True)
