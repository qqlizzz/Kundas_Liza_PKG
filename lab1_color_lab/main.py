import tkinter as tk
from viewmodel import ColorViewModel
from view import ColorView


def main():
    root = tk.Tk()
    vm = ColorViewModel()
    view = ColorView(root, vm)
    root.mainloop()


if __name__ == "__main__":
    main()