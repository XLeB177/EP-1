import tkinter as tk
from tkinter import messagebox
from game import GameScene
import traceback

WIDTH = 1800
HEIGHT = 1000


class MainMenu:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Стреляющие башни")
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(self.root, width=WIDTH, height=HEIGHT, bg="#1e1e2e")
        self.canvas.pack()

        # Координаты для центрирования
        self.center_x = WIDTH // 2
        self.center_y = HEIGHT // 2

        self.draw_ui()
        self.root.mainloop()

    def clear(self):
        self.canvas.delete("all")

    def draw_ui(self):
        self.draw_title()
        self.draw_buttons()

    def draw_title(self):
        # Заголовок над центром
        self.canvas.create_text(
            self.center_x,
            self.center_y - 200,
            text="СТРЕЛЯЮЩИЕ БАШНИ",
            font=("Arial", 56, "bold"),
            fill="white"
        )

    def draw_buttons(self):
        button_start_y = self.center_y - 50

        self.create_button("Играть", self.center_x, button_start_y, self.start_game)
        self.create_button("Об игре", self.center_x, button_start_y + 90, self.show_about)
        self.create_button("Выход", self.center_x, button_start_y + 180, self.exit_game)

    def create_button(self, text, x, y, command):
        button = tk.Button(
            self.root,
            text=text,
            font=("Arial", 22),
            width=25,
            height=1,
            bg="#4a4a6a",
            fg="white",
            activebackground="#6a6a8a",
            activeforeground="white",
            relief="raised",
            borderwidth=3,
            cursor="hand2",
            command=command
        )
        self.canvas.create_window(x, y, window=button)

    def start_game(self):
        try:
            self.clear()
            GameScene(self.root, self.canvas)
        except Exception as e:
            # В .exe исключения в callback часто "теряются" (кажется, что кнопка не работает).
            messagebox.showerror(
                "Ошибка запуска игры",
                f"Не удалось открыть игровой экран.\n\n{e}"
            )
            traceback.print_exc()
            self.clear()
            self.draw_ui()

    def show_about(self):
        text = (
            "Игра \"Стреляющие башни\".\n"
            "Написана на Python с использованием библиотеки Tkinter.\n\n"
            "Защищайте свою башню, выпускайте юнитов и уничтожьте башню врага."
        )
        messagebox.showinfo("Об игре", text)

    def exit_game(self):
        self.root.destroy()


if __name__ == "__main__":
    menu = MainMenu()