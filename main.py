import heapq
import json
import os
import random
import sys

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# --- ЗАГРУЗКА КОНФИГУРАЦИИ ---
CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "grid": {"rows": 100, "cols": 100, "cell_size": 8},
    "simulation": {"delay_ms": 1, "wall_density": 0.3},
    "colors": {
        "empty": [255, 255, 255],
        "wall": [33, 33, 33],
        "start": [76, 175, 80],
        "end": [244, 67, 54],
        "open": [165, 214, 167],
        "closed": [239, 154, 154],
        "path": [156, 39, 176],
    },
}


def load_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"Файл {CONFIG_FILE} не найден. Используются настройки по умолчанию.")
        return DEFAULT_CONFIG

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Ошибка чтения конфига: {e}. Используются настройки по умолчанию.")
        return DEFAULT_CONFIG


# Загружаем настройки
cfg = load_config()

# Глобальные настройки по умолчанию (могут быть перезаписаны при импорте файла)
DEFAULT_ROWS = cfg["grid"]["rows"]
DEFAULT_COLS = cfg["grid"]["cols"]
CELL_SIZE = cfg["grid"]["cell_size"]
DELAY_MS = cfg["simulation"]["delay_ms"]
WALL_DENSITY = cfg["simulation"]["wall_density"]

# Преобразуем списки цветов [R, G, B] в объекты QColor
COLORS = {}
for key, val in cfg["colors"].items():
    COLORS[key] = QColor(*val)


# --- МОДЕЛЬ ДАННЫХ (NODE) ---
class Node:
    def __init__(self, row, col):
        self.row = row
        self.col = col
        self.is_wall = False
        self.state = "empty"  # empty, open, closed, path, start, end
        self.g_cost = float("inf")
        self.h_cost = 0
        self.parent = None

    @property
    def f_cost(self):
        return self.g_cost + self.h_cost

    def __lt__(self, other):
        if self.f_cost == other.f_cost:
            return self.h_cost < other.h_cost
        return self.f_cost < other.f_cost

    def reset_calc(self):
        self.g_cost = float("inf")
        self.h_cost = 0
        self.parent = None
        # Не сбрасываем стены, старт и финиш при очистке пути
        if self.state in ["open", "closed", "path"]:
            self.state = "empty"


# --- ВИДЖЕТ ОТРИСОВКИ КАРТЫ (ОПТИМИЗИРОВАННЫЙ) ---
class GridMapWidget(QWidget):
    # Сигналы для кликов (если нужно будет расширять логику)
    node_clicked = pyqtSignal(int, int)

    def __init__(self, rows, cols, cell_size, nodes):
        super().__init__()
        self.cell_size = cell_size
        self.update_grid_data(rows, cols, nodes)

        # Для отслеживания рисования мышью
        self.drawing_wall_mode = True
        self.last_drag_pos = None

    def update_grid_data(self, rows, cols, nodes):
        """Обновление размеров и ссылки на данные (для загрузки новых карт)"""
        self.rows = rows
        self.cols = cols
        self.nodes = nodes

        width = cols * self.cell_size
        height = rows * self.cell_size
        self.setFixedSize(width, height)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        # Оптимизация: не используем антиалиасинг для четких квадратов
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # Получаем область, которую нужно перерисовать (оптимизация partial update)
        rect = event.rect()

        # Вычисляем диапазоны индексов, попадающих в rect
        start_r = max(0, rect.top() // self.cell_size)
        end_r = min(self.rows, (rect.bottom() // self.cell_size) + 1)
        start_c = max(0, rect.left() // self.cell_size)
        end_c = min(self.cols, (rect.right() // self.cell_size) + 1)

        # Рисуем только то, что изменилось или видно
        for r in range(start_r, end_r):
            for c in range(start_c, end_c):
                node = self.nodes.get((r, c))
                if node:
                    # Выбираем цвет
                    if node.is_wall:
                        c_color = COLORS["wall"]
                    elif node.state in COLORS:
                        c_color = COLORS[node.state]
                    else:
                        c_color = COLORS["empty"]

                    painter.fillRect(
                        c * self.cell_size,
                        r * self.cell_size,
                        self.cell_size,
                        self.cell_size,
                        c_color,
                    )

                    # Рисуем легкую сетку (опционально, можно убрать для скорости на огромных картах)
                    painter.setPen(QPen(QColor(220, 220, 220), 1))
                    painter.drawRect(
                        c * self.cell_size,
                        r * self.cell_size,
                        self.cell_size,
                        self.cell_size,
                    )

    def update_node(self, r, c):
        """Обновляет только конкретную клетку"""
        self.update(
            c * self.cell_size, r * self.cell_size, self.cell_size, self.cell_size
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            r = event.pos().y() // self.cell_size
            c = event.pos().x() // self.cell_size

            if 0 <= r < self.rows and 0 <= c < self.cols:
                node = self.nodes.get((r, c))
                if node:
                    # Не рисуем поверх старта и финиша
                    if node.state in ["start", "end"]:
                        return

                    # Запоминаем режим (ставим стену или стираем)
                    self.drawing_wall_mode = not node.is_wall
                    self.apply_wall(r, c)
                    self.last_drag_pos = (r, c)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            r = event.pos().y() // self.cell_size
            c = event.pos().x() // self.cell_size

            if 0 <= r < self.rows and 0 <= c < self.cols:
                if (r, c) != self.last_drag_pos:
                    node = self.nodes.get((r, c))
                    if node and node.state not in ["start", "end"]:
                        self.apply_wall(r, c)
                    self.last_drag_pos = (r, c)

    def apply_wall(self, r, c):
        node = self.nodes.get((r, c))
        if node:
            node.is_wall = self.drawing_wall_mode
            self.update_node(r, c)


# --- РАБОЧИЙ ПОТОК (A*) ---
class AStarWorker(QThread):
    # Сигнал теперь передает: row, col, state_key
    cell_updated = pyqtSignal(int, int, str)
    finished_signal = pyqtSignal(str)

    def __init__(self, nodes, start_pos, end_pos):
        super().__init__()
        self.nodes = nodes
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.is_running = True

    def run(self):
        start_node = self.nodes.get(self.start_pos)
        end_node = self.nodes.get(self.end_pos)

        if not start_node or not end_node:
            self.finished_signal.emit("Ошибка: нет старта или финиша!")
            return

        open_set = []
        heapq.heappush(open_set, start_node)
        open_set_hash = {start_node}
        closed_set = set()

        start_node.g_cost = 0
        start_node.h_cost = self.heuristic(start_node, end_node)

        while open_set:
            if not self.is_running:
                return

            current = heapq.heappop(open_set)
            if current in open_set_hash:
                open_set_hash.remove(current)

            closed_set.add(current)

            # Визуализация closed
            if (current.row, current.col) != self.start_pos and (
                current.row,
                current.col,
            ) != self.end_pos:
                self.cell_updated.emit(current.row, current.col, "closed")
                # Чем меньше задержка, тем плавнее на больших картах
                if len(closed_set) % 5 == 0:  # Оптимизация: sleep не каждый шаг
                    self.msleep(1)

            if current == end_node:
                self.reconstruct_path(end_node)
                return

            for neighbor in self.get_neighbors(current):
                if neighbor in closed_set:
                    continue

                temp_g = current.g_cost + 1  # Вес ребра = 1

                if temp_g < neighbor.g_cost:
                    neighbor.parent = current
                    neighbor.g_cost = temp_g
                    neighbor.h_cost = self.heuristic(neighbor, end_node)

                    if neighbor not in open_set_hash:
                        heapq.heappush(open_set, neighbor)
                        open_set_hash.add(neighbor)

                        # Визуализация open
                        if (neighbor.row, neighbor.col) != self.end_pos:
                            self.cell_updated.emit(neighbor.row, neighbor.col, "open")

        self.finished_signal.emit("Путь не найден!")

    def heuristic(self, node_a, node_b):
        # Манхэттенское расстояние
        return abs(node_a.row - node_b.row) + abs(node_a.col - node_b.col)

    def get_neighbors(self, node):
        neighbors = []
        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            r, c = node.row + dr, node.col + dc
            if (r, c) in self.nodes:
                n = self.nodes[(r, c)]
                if not n.is_wall:
                    neighbors.append(n)
        return neighbors

    def reconstruct_path(self, end_node):
        path_nodes = []
        curr = end_node
        while curr:
            path_nodes.append(curr)
            curr = curr.parent
        path_nodes.reverse()

        steps = max(0, len(path_nodes) - 1)

        for node in path_nodes:
            if not self.is_running:
                break
            if (node.row, node.col) not in [self.start_pos, self.end_pos]:
                self.cell_updated.emit(node.row, node.col, "path")
                self.msleep(DELAY_MS * 5)

        self.finished_signal.emit(f"Готово! Путь: {steps} шагов")


# --- ГЛАВНОЕ ОКНО ---
class AStarApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("A* Maze Solver (Optimized)")

        self.grid_nodes = {}
        # Используем локальные переменные размеров, чтобы можно было их менять при загрузке файла
        self.current_rows = DEFAULT_ROWS
        self.current_cols = DEFAULT_COLS
        self.start_pos = (0, 0)
        self.end_pos = (self.current_rows - 1, self.current_cols - 1)
        self.worker = None

        # Инициализация данных
        self.init_data(self.current_rows, self.current_cols)

        # UI
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 1. Виджет карты
        self.map_widget = GridMapWidget(
            self.current_rows, self.current_cols, CELL_SIZE, self.grid_nodes
        )

        # Центрируем карту
        h_layout_map = QHBoxLayout()
        h_layout_map.addStretch()
        h_layout_map.addWidget(self.map_widget)
        h_layout_map.addStretch()
        main_layout.addLayout(h_layout_map)

        # 2. Панель управления
        controls = QHBoxLayout()

        btn_run = QPushButton("Запустить A*")
        btn_run.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold;"
        )
        btn_run.clicked.connect(self.start_thread)

        btn_random = QPushButton("🎲 Случайные стены")
        btn_random.clicked.connect(self.generate_random_walls)

        btn_load = QPushButton("📂 Загрузить")
        btn_load.clicked.connect(self.load_maze_from_file)

        btn_save = QPushButton("💾 Сохранить")
        btn_save.clicked.connect(self.save_maze_to_file)

        btn_reset = QPushButton("Очистить")
        btn_reset.clicked.connect(self.reset_grid)

        self.lbl_info = QLabel("ЛКМ: рисовать стены")
        self.lbl_info.setStyleSheet("font-weight: bold; margin-left: 10px;")

        controls.addWidget(btn_run)
        controls.addWidget(btn_random)
        controls.addWidget(btn_load)
        controls.addWidget(btn_save)
        controls.addWidget(btn_reset)
        controls.addWidget(self.lbl_info)

        main_layout.addLayout(controls)

        # Генерация стен при запуске
        self.generate_random_walls()

    def init_data(self, rows, cols):
        """Создает логическую структуру данных с нуля"""
        self.grid_nodes = {}
        for r in range(rows):
            for c in range(cols):
                node = Node(r, c)
                if (r, c) == self.start_pos:
                    node.state = "start"
                elif (r, c) == self.end_pos:
                    node.state = "end"
                self.grid_nodes[(r, c)] = node

    def generate_random_walls(self):
        """Случайная генерация лабиринта для текущих размеров"""
        if self.worker and self.worker.isRunning():
            return

        self.reset_data(keep_walls=False)

        for pos, node in self.grid_nodes.items():
            if pos == self.start_pos or pos == self.end_pos:
                continue
            if random.random() < WALL_DENSITY:
                node.is_wall = True
            else:
                node.is_wall = False

        self.map_widget.update()
        self.lbl_info.setText("Сгенерированы случайные стены")

    def load_maze_from_file(self):
        """Загрузка лабиринта из текстового файла"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Открыть лабиринт", "", "Text Files (*.txt);;All Files (*)"
        )

        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]

            if not lines:
                return

            rows = len(lines)
            cols = len(lines[0])

            # Проверка, что все строки одинаковой длины
            if any(len(line) != cols for line in lines):
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    "Лабиринт должен быть прямоугольным (все строки одинаковой длины).",
                )
                return

            # Останавливаем поток, если запущен
            if self.worker and self.worker.isRunning():
                self.worker.is_running = False
                self.worker.wait()

            # Обновляем размеры
            self.current_rows = rows
            self.current_cols = cols

            # Новая структура данных
            new_nodes = {}
            new_start = None
            new_end = None

            for r, line in enumerate(lines):
                for c, char in enumerate(line):
                    node = Node(r, c)
                    if char == "S":
                        node.state = "start"
                        new_start = (r, c)
                    elif char == "E":
                        node.state = "end"
                        new_end = (r, c)
                    elif char == "#":
                        node.is_wall = True
                    # Остальное считается пустым местом
                    new_nodes[(r, c)] = node

            # Если старт или финиш не найдены в файле, ставим по умолчанию
            if not new_start:
                new_start = (0, 0)
                new_nodes[new_start].state = "start"
                new_nodes[new_start].is_wall = False

            if not new_end:
                new_end = (rows - 1, cols - 1)
                new_nodes[new_end].state = "end"
                new_nodes[new_end].is_wall = False

            self.grid_nodes = new_nodes
            self.start_pos = new_start
            self.end_pos = new_end

            # Обновляем виджет карты
            self.map_widget.update_grid_data(rows, cols, self.grid_nodes)

            self.lbl_info.setText(f"Загружен лабиринт: {rows}x{cols}")

        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка", f"Не удалось загрузить файл:\n{str(e)}"
            )

    def save_maze_to_file(self):
        """Сохранение текущего лабиринта в текстовый файл"""
        if not self.grid_nodes:
            QMessageBox.warning(self, "Ошибка", "Нет данных для сохранения.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить лабиринт", "maze.txt", "Text Files (*.txt);;All Files (*)"
        )

        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                for r in range(self.current_rows):
                    line = ""
                    for c in range(self.current_cols):
                        node = self.grid_nodes.get((r, c))
                        char = "."
                        if node:
                            if node.state == "start":
                                char = "S"
                            elif node.state == "end":
                                char = "E"
                            elif node.is_wall:
                                char = "#"
                        line += char
                    f.write(line + "\n")

            QMessageBox.information(self, "Успех", "Лабиринт успешно сохранен!")
            self.lbl_info.setText(f"Сохранено в {os.path.basename(file_path)}")

        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка", f"Не удалось сохранить файл:\n{str(e)}"
            )

    def reset_grid(self):
        if self.worker and self.worker.isRunning():
            self.worker.is_running = False
            self.worker.wait()

        self.reset_data(keep_walls=False)
        self.map_widget.update()
        self.lbl_info.setText("Поле полностью очищено")

    def reset_data(self, keep_walls=True):
        """Сброс данных узлов"""
        for pos, node in self.grid_nodes.items():
            node.reset_calc()

            if pos == self.start_pos:
                node.state = "start"
            elif pos == self.end_pos:
                node.state = "end"
            else:
                if not keep_walls:
                    node.is_wall = False
                if not node.is_wall:
                    node.state = "empty"

    def start_thread(self):
        if self.worker and self.worker.isRunning():
            return

        self.reset_data(keep_walls=True)
        self.map_widget.update()
        self.lbl_info.setText("Поиск пути...")

        self.worker = AStarWorker(self.grid_nodes, self.start_pos, self.end_pos)
        self.worker.cell_updated.connect(self.on_cell_updated)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def on_cell_updated(self, r, c, state):
        if (r, c) in self.grid_nodes:
            node = self.grid_nodes[(r, c)]
            node.state = state
            self.map_widget.update_node(r, c)

    def on_finished(self, msg):
        self.lbl_info.setText(msg)

    def closeEvent(self, event):
        if self.worker:
            self.worker.is_running = False
            self.worker.quit()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AStarApp()
    window.show()
    sys.exit(app.exec())
