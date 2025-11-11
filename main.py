import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QGridLayout,
    QLabel,
    QLCDNumber,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class AStarVisualizer(QMainWindow):
    """
    Основное окно визуализации
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Визуализация алгоритма A*")
        self.setGeometry(100, 100, 800, 600)

        # создание виджета
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # создание сетки
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(0)
        self.main_layout.addWidget(self.grid_container)

        # виджет настроек
        self.controls_widget = QWidget()
        self.controls_layout = QVBoxLayout(self.controls_widget)

        # доавление кнопок
        self.start_button = QPushButton("Начать поиск")
        self.reset_button = QPushButton("Сброс")
        self.status_label = QLabel("Поиск...")

        # добавление кнопок и ячеек на виджет настроек
        self.controls_layout.addWidget(self.start_button)
        self.controls_layout.addWidget(self.reset_button)
        self.controls_layout.addWidget(self.status_label)

        self.main_layout.addWidget(self.controls_widget)

        self.init_grid(rows=20, cols=20)

    def init_grid(self, rows, cols):
        """
        создание сетки
        """
        self.rows = rows
        self.cols = cols
        self.grid_cells = {}


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AStarVisualizer()
    window.show()
    sys.exit(app.exec())
