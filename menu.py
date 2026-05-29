import tkinter as tk
from tkinter import messagebox
from game import GameScene
import resources
import traceback

WIDTH = 1800
HEIGHT = 1000


class MainMenu:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Стреляющие башни")
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(self.root, width=WIDTH, height=HEIGHT, highlightthickness=0)
        self.canvas.pack()

        self.center_x = WIDTH // 2
        self.center_y = HEIGHT // 2

        self._load_ui_assets()
        self.draw_ui()
        self.root.mainloop()

    def _load_ui_assets(self):
        assets_dir = resources.resolve_assets_dir()

        self.menu_bg = resources.load_photo(assets_dir, "background.png")
        self.btn_play_img = resources.load_photo(assets_dir, "button_play.png")
        self.btn_about_img = resources.load_photo(assets_dir, "button_about.png")
        self.btn_exit_img = resources.load_photo(assets_dir, "button_exit.png")

        self.font_title = resources.get_font(self.root, 56, "bold")

    def clear(self):
        self.canvas.delete("all")

    def draw_ui(self):
        if self.menu_bg:
            self.canvas.create_image(0, 0, anchor="nw", image=self.menu_bg)
        else:
            self.canvas.configure(bg="#1e1e2e")

        self.draw_title()
        self.draw_buttons()

    def draw_title(self):
        self.canvas.create_text(
            self.center_x,
            self.center_y - 200,
            text="СТРЕЛЯЮЩИЕ БАШНИ",
            font=self.font_title,
            fill="black",
        )

    def draw_buttons(self):
        button_start_y = self.center_y - 50
        gap = 90

        self._sprite_button(self.btn_play_img, self.center_x, button_start_y, self.start_game)
        self._sprite_button(
            self.btn_about_img, self.center_x, button_start_y + gap, self.show_about
        )
        self._sprite_button(
            self.btn_exit_img, self.center_x, button_start_y + gap * 2, self.exit_game
        )

    def _sprite_button(self, image, x, y, command):
        if not image:
            return
        item = self.canvas.create_image(x, y, anchor="center", image=image, tags=("menu_btn",))

        def on_click(_event):
            command()

        self.canvas.tag_bind(item, "<Button-1>", on_click)
        self.canvas.tag_bind(item, "<Enter>", lambda _e: self.canvas.config(cursor="hand2"))
        self.canvas.tag_bind(item, "<Leave>", lambda _e: self.canvas.config(cursor=""))

    def start_game(self):
        try:
            self.clear()
            GameScene(self.root, self.canvas)
        except Exception as e:
            messagebox.showerror(
                "Ошибка запуска игры",
                f"Не удалось открыть игровой экран.\n\n{e}",
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
