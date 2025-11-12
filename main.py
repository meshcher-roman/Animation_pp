import sys

from PyQt6.QtCore import Qt, pyqtSignal
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


class Node:
    """
    храниние информации про каждую клетку сетки
    """

    def __init__(self, row, col):
        self.row = row
        self.col = col

        self.g_cost = float("inf")
        self.h_cost = 0
        self.f_cost = float("inf")

        self.parent = None

        self.is_wall = False
        self.is_start = False
        self.is_end = False

    def __lt__(self, other):
        return self.f_cost < other.f_cost

    def calculate_h_cost(self, end_node):
        """вычисление манхэттенского расстояния"""
        dr = abs(self.row - end_node.row)
        dc = abs(self.col - end_node.col)
        self.h_cost = dr + dc
        self.f_cost = self.h_cost + self.g_cost


class NodeWidget(QWidget):
    clicked = pyqtSignal(int, int)

    STATE_COLORS = {
        0: "white",  # пустая клетка
        1: "#212121",  # стена
        2: "#2e7d32",  # старт
        3: "#b71c1c",  # конец
        4: "#a5d6a7",  # открытая клетка
        5: "#ef9a9a",  # закрытая клетка
        6: "#ff80ab",  # кратчайший путь
    }

    def __init__(self, r, c, fixed_size=8):
        super().__init__()
        self.row = r
        self.col = c
        self.state = 0
        self.setFixedSize(fixed_size, fixed_size)
        self.update_style(r, c)

    def set_state(self, state, rows, cols):
        """обновление стиля и состояния ячейки"""
        if self.state == 0:
            return
        self.state = state
        self.update_style(rows, cols)

    def update_style(self, state, rows, cols):
        """обновление css для ячейки в зависимости от состояния"""
        border_right = "1px solid #ddd;" if self.col < cols - 1 else "none"
        border_bottom = "1px solid #ddd;" if self.row < rows - 1 else "none"

        color = self.STATE_COLORS.get(self.state, "white")

        self.setStyleSheet(f"""
            background-color: {color};
            border-right: {border_right};
            border-bottom: {border_bottom};
            padding: 0;
            margin: 0;
            """)

        def mousePressEvent(self, event):
            """сигнал при клике"""
            if event.button() == Qt.MouseButton.LeftButton:
                self.clicked.emit(self.row, self.col)


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
