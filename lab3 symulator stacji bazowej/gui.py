from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QSpinBox, QDoubleSpinBox, QPushButton, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPolygon
from PyQt6.QtCore import QPoint
from widgets import ChannelsGridWidget, QueueWidget, ChartWidget, StatsPanel, PieChartWidget
from simulation import SimulationEngine
import os


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
        self._up_icon = os.path.join(arrow_dir, "up.png").replace("\\", "/")
        self._down_icon = os.path.join(arrow_dir, "down.png").replace("\\", "/")

        if not os.path.exists(self._up_icon):
            for path, pts in [
                (self._up_icon,   [QPoint(2,8), QPoint(8,2), QPoint(14,8)]),
                (self._down_icon, [QPoint(2,2), QPoint(8,8), QPoint(14,2)])
            ]:
                px = QPixmap(16, 10)
                px.fill(QColor(0, 0, 0, 0))
                p = QPainter(px)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                p.setBrush(QColor("#8b949e"))
                p.setPen(QColor("#8b949e"))
                p.drawPolygon(QPolygon(pts))
                p.end()
                px.save(path)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # --- lewa kolumna: parametry + tabela wyników ---
        left_col = QVBoxLayout()
        left_col.setSpacing(10)

        params_group = QGroupBox("Parametry")
        params_group.setStyleSheet(self._group_style())
        params_layout = QGridLayout(params_group)
        params_layout.setSpacing(6)

        self.spin_channels  = self._add_spin(params_layout, 0, "Liczba kanałów:",     1,    50,   10)
        self.spin_queue     = self._add_spin(params_layout, 1, "Długość kolejki:",    1,   100,   10)
        self.spin_lambda    = self._add_dspin(params_layout, 2, "λ (Poisson):",      0.01, 100.0, 1.0, 2)
        self.spin_n         = self._add_dspin(params_layout, 3, "N (śr. rozmowy):", 1.0, 1000.0, 20.0, 1)
        self.spin_sigma     = self._add_dspin(params_layout, 4, "σ (odch. std.):",  0.1,  100.0,  5.0, 1)
        self.spin_min       = self._add_spin(params_layout, 5, "Min rozmowy [s]:",   1,   999,   10)
        self.spin_max       = self._add_spin(params_layout, 6, "Maks rozmowy [s]:",  1,   999,   30)
        self.spin_sim_time  = self._add_spin(params_layout, 7, "Czas symulacji [s]:", 1, 9999,   60)
        self.spin_speed     = self._add_spin(params_layout, 8, "Prędkość [ms/krok]:", 50, 2000, 300)

        left_col.addWidget(params_group)

        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("START")
        self.btn_start.setStyleSheet(self._btn_style("#2d6a4f", "#40916c"))
        self.btn_start.clicked.connect(self._toggle_simulation)
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_restart = QPushButton("RESTART")
        self.btn_restart.setStyleSheet(self._btn_style("#e94560", "#ff6b6b"))
        self.btn_restart.clicked.connect(self._restart_simulation)
        self.btn_restart.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_restart.setEnabled(False)

        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_restart)
        left_col.addLayout(btn_layout)

        self.time_label = QLabel("Czas: 0 / 0 s")
        self.time_label.setStyleSheet(
            "color: #e6edf3; font-size: 14px; font-weight: bold; font-family: 'Segoe UI';"
        )
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_col.addWidget(self.time_label)

        results_group = QGroupBox("Wyniki symulacji")
        results_group.setStyleSheet(self._group_style())
        results_layout = QVBoxLayout(results_group)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Czas", "ρ", "Q", "W"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("""
            QTableWidget {
                background: #0d1117;
                color: #e6edf3;
                border: none;
                gridline-color: #21262d;
                font-size: 11px;
            }
            QHeaderView::section {
                background: #161b22;
                color: #58a6ff;
                border: 1px solid #21262d;
                padding: 4px;
                font-weight: bold;
            }
            QTableWidget::item { padding: 2px 4px; }
        """)
        self.table.verticalHeader().setVisible(False)
        results_layout.addWidget(self.table)
        left_col.addWidget(results_group, 1)

        main_layout.addLayout(left_col, 2)

        # --- środkowa kolumna: kanały + kolejka + statystyki + pie ---
        mid_col = QVBoxLayout()
        mid_col.setSpacing(10)

        channels_group = QGroupBox("Kanały")
        channels_group.setStyleSheet(self._group_style())
        ch_layout = QVBoxLayout(channels_group)
        self.channels_grid = ChannelsGridWidget()
        ch_layout.addWidget(self.channels_grid)
        mid_col.addWidget(channels_group, 3)

        queue_group = QGroupBox("Kolejka")
        queue_group.setStyleSheet(self._group_style())
        q_layout = QVBoxLayout(queue_group)
        self.queue_widget = QueueWidget()
        q_layout.addWidget(self.queue_widget)
        mid_col.addWidget(queue_group)

        self.stats_panel = StatsPanel()
        mid_col.addWidget(self.stats_panel)

        self.pie_chart = PieChartWidget()
        mid_col.addWidget(self.pie_chart)

        main_layout.addLayout(mid_col, 2)

        # --- prawa kolumna: trzy wykresy liniowe ---
        right_col = QVBoxLayout()
        right_col.setSpacing(8)

        self.chart_rho = ChartWidget("ρ — Intensywność ruchu",        "#2d6a4f", "ρ")
        self.chart_q   = ChartWidget("Q — Średnia dł. kolejki",       "#e94560", "Q")
        self.chart_w   = ChartWidget("W — Średni czas oczekiwania",   "#58a6ff", "W [s]")

        right_col.addWidget(self.chart_rho)
        right_col.addWidget(self.chart_q)
        right_col.addWidget(self.chart_w)

        main_layout.addLayout(right_col, 3)

    # --- logika przycisków ---

    def _toggle_simulation(self):
        if not self.is_running:
            if self.engine is None:
                self._start_simulation()
            else:
                # wznowienie po pauzie
                self.timer.start(self.spin_speed.value())
                self.is_running = True
                self.btn_start.setText("STOP")
                self.btn_start.setStyleSheet(self._btn_style("#e76f51", "#f4a261"))
                self._set_params_enabled(False)
        else:
            self.timer.stop()
            self.is_running = False
            self.btn_start.setText("START")
            self.btn_start.setStyleSheet(self._btn_style("#2d6a4f", "#40916c"))

    def _start_simulation(self):
        num_ch     = self.spin_channels.value()
        queue_size = self.spin_queue.value()
        lam        = self.spin_lambda.value()
        n_mean     = self.spin_n.value()
        sigma      = self.spin_sigma.value()
        min_dur    = self.spin_min.value()
        max_dur    = self.spin_max.value()
        sim_time   = self.spin_sim_time.value()

        if min_dur >= max_dur:
            self.spin_max.setValue(min_dur + 1)
            max_dur = min_dur + 1

        self.engine = SimulationEngine(num_ch, queue_size, lam, n_mean, sigma, min_dur, max_dur, sim_time)
        self.channels_grid.setup_channels(num_ch)
        self.queue_widget.update_queue(0, queue_size)
        self.table.setRowCount(0)

        for chart in [self.chart_rho, self.chart_q, self.chart_w]:
            chart.reset()
        self.pie_chart.reset()

        self.timer.start(self.spin_speed.value())
        self.is_running = True
        self.btn_start.setText("STOP")
        self.btn_start.setStyleSheet(self._btn_style("#e76f51", "#f4a261"))
        self.btn_restart.setEnabled(True)
        self._set_params_enabled(False)

    def _restart_simulation(self):
        self.timer.stop()
        self.is_running = False
        self.engine = None
        self.btn_start.setText("START")
        self.btn_start.setStyleSheet(self._btn_style("#2d6a4f", "#40916c"))
        self.btn_restart.setEnabled(False)
        self._set_params_enabled(True)

        self.time_label.setText("Czas: 0 / 0 s")
        self.channels_grid.setup_channels(self.spin_channels.value())
        self.queue_widget.update_queue(0, self.spin_queue.value())
        self.stats_panel.update_stats(0, 0, 0, 0, 0)
        self.table.setRowCount(0)
        for chart in [self.chart_rho, self.chart_q, self.chart_w]:
            chart.reset()
        self.pie_chart.reset()

    def _simulation_step(self):
        if self.engine is None:
            return

        result = self.engine.step()

        if not result.finished:
            self.channels_grid.update_channels(result.channels)
            self.queue_widget.update_queue(result.queue_len, self.spin_queue.value())
            self.time_label.setText(f"Czas: {result.current_time} / {self.spin_sim_time.value()} s")
            self.stats_panel.update_stats(
                result.total_served, result.rejected,
                result.rho, result.avg_q, result.avg_w
            )

            # wiersz do tabeli
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(result.current_time)))
            self.table.setItem(row, 1, QTableWidgetItem(f"{result.rho:.4f}"))
            self.table.setItem(row, 2, QTableWidgetItem(f"{result.avg_q:.4f}"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{result.avg_w:.4f}"))
            self.table.scrollToBottom()

            # wykresy co 2 sekundy żeby nie lagowało za mocno
            if result.current_time % 2 == 0 or result.current_time <= 5:
                self._update_charts(result)

        if result.finished:
            self.timer.stop()
            self.is_running = False
            self.btn_start.setText("START")
            self.btn_start.setStyleSheet(self._btn_style("#2d6a4f", "#40916c"))
            self.btn_start.setEnabled(False)
            self._update_charts(result)
            self._save_results()

    def _update_charts(self, result):
        self.chart_rho.update_chart(self.engine.time_history, self.engine.rho_history)
        self.chart_q.update_chart(self.engine.time_history, self.engine.q_history)
        self.chart_w.update_chart(self.engine.time_history, self.engine.w_history)
        self.pie_chart.update_pie(result.total_served, result.rejected)

    def _save_results(self):
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wyniki_symulacji.txt")
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.engine.get_results_for_file())
            self.time_label.setText(
                f"Czas: {self.engine.current_time} / {self.spin_sim_time.value()} s  —  Wyniki zapisane!"
            )
        except Exception as e:
            self.time_label.setText(f"Błąd zapisu: {e}")

    def _set_params_enabled(self, enabled):
        for spin in [self.spin_channels, self.spin_queue, self.spin_lambda,
                     self.spin_n, self.spin_sigma, self.spin_min, self.spin_max,
                     self.spin_sim_time]:
            spin.setEnabled(enabled)
        if enabled:
            self.btn_start.setEnabled(True)

    # --- pomocnicze metody do budowania UI ---

    def _add_spin(self, layout, row, label_text, min_val, max_val, default):
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #e6edf3; font-size: 12px;")
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(default)
        spin.setStyleSheet(self._spin_style())
        layout.addWidget(lbl, row, 0)
        layout.addWidget(spin, row, 1)
        return spin

    def _add_dspin(self, layout, row, label_text, min_val, max_val, default, decimals):
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #e6edf3; font-size: 12px;")
        spin = QDoubleSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(default)
        spin.setDecimals(decimals)
        spin.setSingleStep(0.1)
        spin.setStyleSheet(self._spin_style())
        layout.addWidget(lbl, row, 0)
        layout.addWidget(spin, row, 1)
        return spin

    def _spin_style(self):
        up = self._up_icon
        dn = self._down_icon
        return f"""
            QSpinBox, QDoubleSpinBox {{
                background: #0d1117;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 5px;
                padding: 4px 8px;
                font-size: 12px;
                min-width: 80px;
            }}
            QSpinBox:focus, QDoubleSpinBox:focus {{
                border-color: #58a6ff;
            }}
            QSpinBox::up-button, QDoubleSpinBox::up-button {{
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 20px;
                background: #21262d;
                border-left: 1px solid #30363d;
                border-bottom: 1px solid #30363d;
                border-top-right-radius: 4px;
            }}
            QSpinBox::down-button, QDoubleSpinBox::down-button {{
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 20px;
                background: #21262d;
                border-left: 1px solid #30363d;
                border-bottom-right-radius: 4px;
            }}
            QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
                image: url({up});
                width: 10px;
                height: 6px;
            }}
            QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
                image: url({dn});
                width: 10px;
                height: 6px;
            }}
            QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
            QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
                background: #30363d;
            }}
        """

    @staticmethod
    def _group_style():
        return """
            QGroupBox {
                background: #161b22;
                border: 1px solid #30363d;
                border-radius: 10px;
                margin-top: 14px;
                padding-top: 14px;
                font-size: 13px;
                font-weight: bold;
                color: #58a6ff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }
        """

    @staticmethod
    def _btn_style(bg, hover):
        return f"""
            QPushButton {{
                background: {bg};
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                font-family: 'Segoe UI';
            }}
            QPushButton:hover {{ background: {hover}; }}
            QPushButton:disabled {{ background: #21262d; color: #484f58; }}
        """
