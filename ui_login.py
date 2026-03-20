import tkinter as tk
from tkinter import messagebox
import sqlite3

def login_window(root, on_success):

    frame = tk.Frame(root, bg="#f4f6f9")
    frame.pack(fill="both", expand=True)

    tk.Label(frame, text="Faculty Login",
             font=("Segoe UI", 20, "bold"),
             bg="#f4f6f9").pack(pady=30)

    user = tk.Entry(frame, font=("Segoe UI", 12))
    pwd = tk.Entry(frame, show="*", font=("Segoe UI", 12))
    user.pack(pady=8)
    pwd.pack(pady=8)

    def login():
        conn = sqlite3.connect("attendance.db")
        cur = conn.cursor()
        cur.execute("SELECT * FROM admin WHERE username=? AND password=?",
                    (user.get(), pwd.get()))
        if cur.fetchone():
            frame.destroy()
            on_success()
        else:
            messagebox.showerror("Error", "Invalid login")
        conn.close()

    tk.Button(frame, text="Login",
              bg="#0078D7", fg="white",
              font=("Segoe UI", 11),
              command=login).pack(pady=20)
