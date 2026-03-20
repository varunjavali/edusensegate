import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3, os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "attendance.db")

def approve_window(root):

    win = tk.Toplevel(root)
    win.title("Approve Students (One Time)")
    win.geometry("550x300")

    table = ttk.Treeview(
        win,
        columns=("Roll No", "Name", "IP Address"),
        show="headings"
    )

    for c in ("Roll No", "Name", "IP Address"):
        table.heading(c, text=c)
        table.column(c, width=170)

    table.pack(fill="both", expand=True, padx=10, pady=10)

    def load_pending():
        table.delete(*table.get_children())
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            SELECT roll_no, name, ip_address
            FROM students
            WHERE approved = 0
        """)
        for row in cur.fetchall():
            table.insert("", "end", values=row)
        conn.close()

    def approve_selected():
        selected = table.selection()
        if not selected:
            messagebox.showwarning("Select Student", "Please select a student")
            return

        roll_no = table.item(selected[0])["values"][0]

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            UPDATE students
            SET approved = 1
            WHERE roll_no = ?
        """, (roll_no,))
        conn.commit()
        conn.close()

        messagebox.showinfo("Approved", f"Student {roll_no} approved successfully")
        load_pending()

    tk.Button(
        win,
        text="✅ Approve Selected Student",
        command=approve_selected
    ).pack(pady=10)

    load_pending()