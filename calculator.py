import tkinter as tk
from tkinter import messagebox

class Calculator:
    def __init__(self, root):
        self.root = root
        self.root.title("Calculator")
        self.root.geometry("300x400")

        self.result_var = tk.StringVar()
        self.result_var.set("")

        self.entry = tk.Entry(root, textvariable=self.result_var, font=('Arial', 24), bd=10, insertwidth=2, width=14, borderwidth=4)
        self.entry.grid(row=0, column=0, columnspan=4)

        buttons = [
            ('7', 1, 0), ('8', 1, 1), ('9', 1, 2), ('/', 1, 3),
            ('4', 2, 0), ('5', 2, 1), ('6', 2, 2), ('*', 2, 3),
            ('1', 3, 0), ('2', 3, 1), ('3', 3, 2), ('-', 3, 3),
            ('0', 4, 0), ('.', 4, 1), ('+', 4, 2), ('=', 4, 3),
            ('C', 5, 0)
        ]

        for (text, row, col) in buttons:
            if text == '=':
                btn = tk.Button(root, text=text, padx=20, pady=20, command=self.calculate)
            elif text == 'C':
                btn = tk.Button(root, text=text, padx=20, pady=20, command=self.clear)
            else:
                btn = tk.Button(root, text=text, padx=20, pady=20, command=lambda t=text: self.append(t))
            btn.grid(row=row, column=col, sticky="nsew")

        # Configure grid weights
        for i in range(5):
            root.grid_rowconfigure(i, weight=1)
        for i in range(4):
            root.grid_columnconfigure(i, weight=1)

    def append(self, char):
        self.result_var.set(self.result_var.get() + char)

    def clear(self):
        self.result_var.set("")

    def calculate(self):
        try:
            self.result_var.set(eval(self.result_var.get()))
        except Exception:
            self.result_var.set("Error")

if __name__ == "__main__":
    root = tk.Tk()
    app = Calculator(root)
    root.mainloop()
