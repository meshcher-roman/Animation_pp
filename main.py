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
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
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

        self.init_grid(rows=75, cols=40)

    def init_grid(self, rows, cols):
        """
        создание сетки
        """
        self.rows = rows
        self.cols = cols
        self.grid_cells = {}

        for i in reversed(range(self.grid_layout.count())):
            item = self.grid_layout.itemAt(i)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
            self.grid_layout.removeItem(item)

        for r in range(rows):
            for c in range(cols):
                cell = QWidget()
                cell.setObjectName(f"cell_{r}_{c}")
                border_right = "1px solid #ddd;" if c < cols - 1 else "none;"
                border_bottom = "1px solid #ddd;" if r < rows - 1 else "none;"

                cell.setStyleSheet(f"""
                    background-color: white;
                    border-right: {border_right};
                    border-bottom: {border_bottom};
                    /* Также убираем padding и margin, чтобы быть уверенным */
                    padding: 0;
                    margin: 0;
                """)

                cell.setFixedSize(8, 8)
                self.grid_layout.addWidget(cell, r, c)
                self.grid_cells[(r, c)] = cell


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AStarVisualizer()
    window.show()
    sys.exit(app.exec())
