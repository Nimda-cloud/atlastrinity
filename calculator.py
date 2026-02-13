import tkinter as tk
from tkinter import font


class ModernCalculator:
    def __init__(self, root):
        self.root = root
        self.root.title("Modern Calculator")
        self.root.geometry("350x550")
        self.root.configure(bg="#1e1e1e")

        self.expression = ""
        self.input_text = tk.StringVar()

        # UI Setup for better aesthetics
        display_frame = tk.Frame(self.root, width=350, height=120, bg="#1e1e1e", bd=0)
        display_frame.pack(expand=True, fill="both")

        # Large display
        input_field = tk.Label(
            display_frame,
            textvariable=self.input_text,
            font=("Helvetica", 48),
            fg="#ffffff",
            bg="#1e1e1e",
            anchor="e",
            padx=20,
            pady=20,
        )
        input_field.pack(expand=True, fill="both")

        # Button layout
        btns_frame = tk.Frame(self.root, width=350, height=430, bg="#1e1e1e")
        btns_frame.pack(expand=True, fill="both")

        buttons = [
            ("C", 0, 0),
            ("±", 0, 1),
            ("%", 0, 2),
            ("/", 0, 3),
            ("7", 1, 0),
            ("8", 1, 1),
            ("9", 1, 2),
            ("*", 1, 3),
            ("4", 2, 0),
            ("5", 2, 1),
            ("6", 2, 2),
            ("-", 2, 3),
            ("1", 3, 0),
            ("2", 3, 1),
            ("3", 3, 2),
            ("+", 3, 3),
            ("0", 4, 0, 2),
            (".", 4, 2),
            ("=", 4, 3),
        ]

        for btn_info in buttons:
            text = btn_info[0]
            row = btn_info[1]
            col = btn_info[2]
            colspan = btn_info[3] if len(btn_info) > 3 else 1

            # Stylized coloring
            bg_color = "#333333"
            fg_color = "white"
            active_bg = "#4d4d4d"

            if text in ["/", "*", "-", "+", "="]:
                bg_color = "#ff9500"  # iOS Orange
                active_bg = "#ffb041"
            elif text in ["C", "±", "%"]:
                bg_color = "#a5a5a5"
                fg_color = "black"
                active_bg = "#d4d4d4"

            btn = tk.Button(
                btns_frame,
                text=text,
                font=("Helvetica", 20, "bold"),
                fg=fg_color,
                bg=bg_color,
                activebackground=active_bg,
                activeforeground=fg_color,
                bd=0,
                highlightthickness=0,
                command=lambda t=text: self.on_click(t),
            )
            btn.grid(row=row, column=col, columnspan=colspan, padx=1, pady=1, sticky="nsew")

        # Equalize grid
        for i in range(5):
            btns_frame.grid_rowconfigure(i, weight=1)
        for i in range(4):
            btns_frame.grid_columnconfigure(i, weight=1)

    def on_click(self, char):
        if char == "=":
            try:
                # Basic protection for eval
                safe_expr = self.expression.replace("×", "*").replace("÷", "/")
                result = str(eval(safe_expr))
                self.input_text.set(result)
                self.expression = result
            except Exception:
                self.input_text.set("Error")
                self.expression = ""
        elif char == "C":
            self.expression = ""
            self.input_text.set("")
        else:
            self.expression += str(char)
            self.input_text.set(self.expression)


if __name__ == "__main__":
    root = tk.Tk()
    # Simple trick for modern look on macOS/Windows
    try:
        root.tk.call("tk_setPalette", "#1e1e1e")
    except:
        pass
    app = ModernCalculator(root)
    root.mainloop()
