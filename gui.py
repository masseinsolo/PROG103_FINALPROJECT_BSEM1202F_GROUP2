"""
GUI – All graphical interface code (LoginWindow, CropAdvisorApp)
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
import csv
import os
import subprocess
import sys

# Import from our modules
from config import C, CROP_ICONS, CROP_TIPS, MATURITY_DAYS, ALL_CROPS, LOCAL_CROPS, TEST_CROPS
from models import (
    crops_planted, harvest_records, sales_records, current_user, start_work_time,
    USERS, load_data, save_data, load_users, save_users
)
from logic import (
    recommend_crop, get_fertilizer, get_current_season,
    days_since_planting, estimate_harvest_seconds_left,
    fmt_time, pct_complete, _lighten
)

# ══════════════════════════════════════════════════════════════════
#  REUSABLE WIDGETS
# ══════════════════════════════════════════════════════════════════
def styled_label(parent, text, size=11, bold=False, color=None, **kw):
    weight = "bold" if bold else "normal"
    fg     = color or C["text"]
    return tk.Label(parent, text=text, font=("Segoe UI", size, weight),
                    bg=parent["bg"], fg=fg, **kw)

def styled_button(parent, text, command, color=None, width=None, **kw):
    bg = color or C["accent"]
    fg = "#0a1a0b" if bg == C["accent"] else "white"
    b  = tk.Button(parent, text=text, command=command,
                   bg=bg, fg=fg, font=("Segoe UI", 10, "bold"),
                   relief="flat", bd=0, activebackground="#66bb6a",
                   activeforeground="#0a1a0b", cursor="hand2",
                   padx=14, pady=7, **kw)
    if width:
        b.config(width=width)
    return b

def entry_widget(parent, width=25, **kw):
    return tk.Entry(parent, width=width, font=("Segoe UI", 10),
                    bg=C["card"], fg=C["text"], insertbackground=C["accent"],
                    relief="flat", highlightthickness=1,
                    highlightbackground=C["border"],
                    highlightcolor=C["accent"], **kw)

def combo_widget(parent, var, values, width=25):
    style = ttk.Style()
    style.configure("Dark.TCombobox",
                     fieldbackground=C["card"],
                     background=C["card"],
                     foreground=C["text"],
                     arrowcolor=C["accent"],
                     selectbackground=C["accent"],
                     selectforeground="#0a1a0b")
    c = ttk.Combobox(parent, textvariable=var, values=values,
                     state="readonly", width=width, style="Dark.TCombobox")
    return c

def kpi_card(parent, title, value, color=None):
    frm = tk.Frame(parent, bg=C["card"], padx=18, pady=14)
    frm.pack(side="left", expand=True, fill="both", padx=6)
    tk.Label(frm, text=value, font=("Segoe UI", 22, "bold"),
             bg=C["card"], fg=color or C["accent"]).pack()
    tk.Label(frm, text=title, font=("Segoe UI", 9),
             bg=C["card"], fg=C["muted"]).pack()
    return frm

def scrollable(parent):
    """Return (canvas, inner_frame) with autoscroll."""
    canvas = tk.Canvas(parent, bg=C["bg"], highlightthickness=0)
    vsb    = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    vsb.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    inner = tk.Frame(canvas, bg=C["bg"])
    window_id = canvas.create_window((0,0), window=inner, anchor="nw")
    def _config(e):
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.itemconfig(window_id, width=canvas.winfo_width())
    inner.bind("<Configure>", _config)
    canvas.bind("<Configure>",
        lambda e: canvas.itemconfig(window_id, width=e.width))
    def _scroll(e):
        canvas.yview_scroll(int(-1*(e.delta/120)), "units")
    canvas.bind_all("<MouseWheel>", _scroll)
    return canvas, inner

# ══════════════════════════════════════════════════════════════════
#  LOGIN WINDOW
# ══════════════════════════════════════════════════════════════════
class LoginWindow:
    def __init__(self, master):
        self.master = master
        master.title("Crop Advisor – Login")
        master.geometry("480x560")
        master.configure(bg=C["bg"])
        master.resizable(False, False)
        load_users()

        # Outer card
        card = tk.Frame(master, bg=C["panel"], padx=40, pady=35)
        card.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(card, text="🌿", font=("Segoe UI", 36), bg=C["panel"]).pack()
        tk.Label(card, text="CROP ADVISOR", font=("Segoe UI", 20, "bold"),
                 bg=C["panel"], fg=C["accent"]).pack()
        tk.Label(card, text="Smart Farming Management System",
                 font=("Segoe UI", 9), bg=C["panel"], fg=C["muted"]).pack(pady=(2,20))

        tk.Label(card, text="Username / Phone",
                 font=("Segoe UI", 10), bg=C["panel"], fg=C["muted"]).pack(anchor="w")
        self.e_user = entry_widget(card, width=30)
        self.e_user.pack(pady=(3,12), ipady=5)

        tk.Label(card, text="Password",
                 font=("Segoe UI", 10), bg=C["panel"], fg=C["muted"]).pack(anchor="w")
        self.e_pass = entry_widget(card, width=30, show="*")
        self.e_pass.pack(pady=(3,6), ipady=5)

        # Show/hide password
        self.show_pw = tk.BooleanVar()
        tk.Checkbutton(card, text="Show password", variable=self.show_pw,
                       bg=C["panel"], fg=C["muted"], selectcolor=C["card"],
                       activebackground=C["panel"], activeforeground=C["muted"],
                       font=("Segoe UI", 9),
                       command=lambda: self.e_pass.config(
                           show="" if self.show_pw.get() else "*")).pack(anchor="w", pady=(0,14))

        btn_frame = tk.Frame(card, bg=C["panel"])
        btn_frame.pack(fill="x")
        styled_button(btn_frame, "Login", self.do_login, width=15).pack(side="left")
        styled_button(btn_frame, "Register", self.open_register,
                      color=C["border"], width=13).pack(side="left", padx=10)

        self.lbl_err = tk.Label(card, text="", fg=C["danger"],
                                bg=C["panel"], font=("Segoe UI", 9))
        self.lbl_err.pack(pady=(10,0))

        tk.Label(card, text="Default: farmer1 / crop123",
                 font=("Segoe UI", 8), bg=C["panel"], fg=C["border"]).pack(pady=(16,0))

        self.e_user.bind("<Return>", lambda e: self.e_pass.focus())
        self.e_pass.bind("<Return>", lambda e: self.do_login())
        self.e_user.focus()

    def do_login(self):
        global current_user, start_work_time
        u = self.e_user.get().strip()
        p = self.e_pass.get().strip()
        if u in USERS and USERS[u]["password"] == p:
            current_user    = u
            start_work_time = datetime.now()
            save_data()
            self.master.destroy()
            open_main_app()
        else:
            self.lbl_err.config(text=" Incorrect username or password.")

    def open_register(self):
        reg = tk.Toplevel(self.master)
        reg.title("Register New Farmer")
        reg.geometry("420x460")
        reg.configure(bg=C["bg"])
        reg.transient(self.master); reg.grab_set()

        card = tk.Frame(reg, bg=C["panel"], padx=30, pady=28)
        card.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(card, text="New Farmer Account",
                 font=("Segoe UI", 14, "bold"), bg=C["panel"], fg=C["accent"]).pack(pady=(0,16))

        fields = {}
        for lbl, key, hide in [("Full Name","fullname",False),
                                 ("Username","username",False),
                                 ("Phone Number","phone",False),
                                 ("Password","password",True),
                                 ("Confirm Password","confirm",True)]:
            tk.Label(card, text=lbl, font=("Segoe UI",10),
                     bg=C["panel"], fg=C["muted"]).pack(anchor="w")
            e = entry_widget(card, width=28, show="*" if hide else "")
            e.pack(pady=(3,10), ipady=4)
            fields[key] = e

        lbl_err = tk.Label(card, text="", fg=C["danger"],
                           bg=C["panel"], font=("Segoe UI",9))
        lbl_err.pack()

        def do_register():
            fn = fields["fullname"].get().strip()
            un = fields["username"].get().strip()
            ph = fields["phone"].get().strip()
            pw = fields["password"].get().strip()
            cf = fields["confirm"].get().strip()
            if not all([fn,un,ph,pw]):
                lbl_err.config(text="All fields are required."); return
            if pw != cf:
                lbl_err.config(text="Passwords do not match."); return
            if un in USERS:
                lbl_err.config(text="Username already taken."); return
            USERS[un] = {"password":pw,"phone":ph,"fullname":fn,"role":"farmer"}
            save_users()
            messagebox.showinfo("Account Created",
                f"Account for {fn} created!\nYou can now log in.", parent=reg)
            reg.destroy()

        styled_button(card, "Create Account", do_register).pack(pady=10)


# ══════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ══════════════════════════════════════════════════════════════════
class CropAdvisorApp:
    def __init__(self, root):
        self.root = root
        root.title(" Crop Advisor – Smart Farming")
        root.geometry("1280x780")
        root.configure(bg=C["bg"])
        root.minsize(960, 620)

        # Style
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=C["card"], foreground=C["text"],
                        fieldbackground=C["card"], rowheight=26,
                        font=("Segoe UI",10))
        style.configure("Treeview.Heading", background=C["panel"],
                        foreground=C["accent"], font=("Segoe UI",10,"bold"), relief="flat")
        style.map("Treeview", background=[("selected",C["accent"])],
                  foreground=[("selected","#0a1a0b")])
        style.configure("green.Horizontal.TProgressbar",
                        troughcolor=C["border"], background=C["accent"], thickness=8)
        style.configure("amber.Horizontal.TProgressbar",
                        troughcolor=C["border"], background=C["warn"], thickness=8)
        style.configure("red.Horizontal.TProgressbar",
                        troughcolor=C["border"], background=C["danger"], thickness=8)

        load_data()
        self._alarm_shown   = set()
        self._live_labels   = {}  # crop key → (time_label, bar_widget)
        self._active_page   = None

        self._build_layout()
        self.show_dashboard()
        self._tick()          # 1-second heartbeat

    # ── Layout ──────────────────────────────────────────────────
    def _build_layout(self):
        # ── Sidebar ──────────────────────────────────────────────
        self.sidebar = tk.Frame(self.root, bg=C["sidebar"], width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Logo
        logo = tk.Frame(self.sidebar, bg=C["sidebar"])
        logo.pack(pady=(20,5), padx=15, fill="x")
        tk.Label(logo, text="🌿", font=("Segoe UI",28), bg=C["sidebar"]).pack(side="left")
        lf = tk.Frame(logo, bg=C["sidebar"]); lf.pack(side="left", padx=8)
        tk.Label(lf, text="CROP", font=("Segoe UI",14,"bold"),
                 bg=C["sidebar"], fg=C["accent"]).pack(anchor="w")
        tk.Label(lf, text="ADVISOR", font=("Segoe UI",11),
                 bg=C["sidebar"], fg=C["muted"]).pack(anchor="w")

        tk.Frame(self.sidebar, bg=C["border"], height=1).pack(fill="x", padx=15, pady=12)

        # Nav items – no emojis
        self._nav_btns = {}
        nav = [
            ("Dashboard",    self.show_dashboard),
            ("Crop Rotation", self.show_rotation),
            ("Harvest",      self.show_harvest_management),
            ("Crop Sale",    self.show_crop_sale),
            ("Analytics",    self.show_analytics),
            ("History",      self.show_history),
            ("Settings",     self.show_settings),
        ]
        for name, cmd in nav:
            self._make_nav_btn(name, cmd)

        tk.Frame(self.sidebar, bg=C["border"], height=1).pack(fill="x", padx=15, pady=12)

        # Notification badge
        self._notif_var = tk.StringVar(value="  Alerts: 0")
        tk.Label(self.sidebar, textvariable=self._notif_var,
                 font=("Segoe UI",9), bg=C["sidebar"], fg=C["muted"]).pack(padx=15, anchor="w")

        # Session info (bottom of sidebar)
        self._session_var = tk.StringVar()
        tk.Label(self.sidebar, textvariable=self._session_var,
                 font=("Segoe UI",8), bg=C["sidebar"],
                 fg=C["border"], wraplength=190, justify="left").pack(side="bottom", padx=15, pady=15, anchor="w")

        # ── Top bar ──────────────────────────────────────────────
        topbar = tk.Frame(self.root, bg=C["panel"], height=52)
        topbar.pack(side="top", fill="x")
        topbar.pack_propagate(False)

        self._page_title = tk.StringVar(value="Dashboard")
        tk.Label(topbar, textvariable=self._page_title,
                 font=("Segoe UI",15,"bold"), bg=C["panel"],
                 fg=C["accent"]).pack(side="left", padx=25, pady=14)

        right = tk.Frame(topbar, bg=C["panel"])
        right.pack(side="right", padx=20)
        self._clock_var = tk.StringVar()
        tk.Label(right, textvariable=self._clock_var,
                 font=("Segoe UI",10), bg=C["panel"], fg=C["muted"]).pack(side="right")
        self._user_var = tk.StringVar()
        tk.Label(right, textvariable=self._user_var,
                 font=("Segoe UI",10,"bold"), bg=C["panel"],
                 fg=C["text"]).pack(side="right", padx=20)

        # ── Content area ─────────────────────────────────────────
        self.content_frame = tk.Frame(self.root, bg=C["bg"])
        self.content_frame.pack(side="right", fill="both", expand=True)
        self.current_frame = None

    def _make_nav_btn(self, name, cmd):
        frm = tk.Frame(self.sidebar, bg=C["sidebar"], cursor="hand2")
        frm.pack(fill="x", padx=10, pady=2)
        lbl = tk.Label(frm, text=f"  {name}", font=("Segoe UI",11),
                       bg=C["sidebar"], fg=C["muted"], anchor="w", padx=8, pady=9)
        lbl.pack(fill="x")
        self._nav_btns[name] = (frm, lbl)
        def enter(e, f=frm, l=lbl):
            f.config(bg=C["card"]); l.config(bg=C["card"], fg=C["text"])
        def leave(e, f=frm, l=lbl, n=name):
            if self._active_page != n:
                f.config(bg=C["sidebar"]); l.config(bg=C["sidebar"], fg=C["muted"])
        def click(e=None, f=frm, l=lbl, n=name, c=cmd):
            self._set_active(n); c()
        frm.bind("<Button-1>", click); lbl.bind("<Button-1>", click)
        frm.bind("<Enter>", enter);    lbl.bind("<Enter>", enter)
        frm.bind("<Leave>", leave);    lbl.bind("<Leave>", leave)

    def _set_active(self, name):
        if self._active_page and self._active_page in self._nav_btns:
            f, l = self._nav_btns[self._active_page]
            f.config(bg=C["sidebar"]); l.config(bg=C["sidebar"], fg=C["muted"])
        self._active_page = name
        f, l = self._nav_btns[name]
        f.config(bg=C["accent"]); l.config(bg=C["accent"], fg="#0a1a0b", font=("Segoe UI",11,"bold"))
        self._page_title.set(name)

    # ── Heartbeat ────────────────────────────────────────────────
    def _tick(self):
        now = datetime.now()
        self._clock_var.set(now.strftime("  %a %d %b %Y  |  %H:%M:%S"))
        if current_user and current_user in USERS:
            fn = USERS[current_user]["fullname"]
            self._user_var.set(f"👤 {fn}")
            if start_work_time:
                elapsed = now - start_work_time
                h, rem = divmod(int(elapsed.total_seconds()), 3600)
                m, s   = divmod(rem, 60)
                self._session_var.set(f"Session: {h:02d}:{m:02d}:{s:02d}\nUser: {current_user}")
        # Live timers
        ready_count = 0
        for crop in crops_planted:
            key = crop["name"] + crop["planted_date"].isoformat()
            sec_left, adj_days = estimate_harvest_seconds_left(crop)
            pct = pct_complete(crop)
            if sec_left <= 0:
                ready_count += 1
                if key not in self._alarm_shown:
                    self._alarm_shown.add(key)
                    self._show_alarm(crop["name"])
            if key in self._live_labels:
                tlbl, bar, plbl = self._live_labels[key]
                tlbl.config(text=fmt_time(sec_left))
                bar["value"] = pct
                plbl.config(text=f"{pct:.0f}%")
                if sec_left <= 0:
                    tlbl.config(fg=C["danger"])
                    bar.config(style="red.Horizontal.TProgressbar")
                elif pct >= 75:
                    tlbl.config(fg=C["warn"])
                    bar.config(style="amber.Horizontal.TProgressbar")
                else:
                    tlbl.config(fg=C["accent"])
                    bar.config(style="green.Horizontal.TProgressbar")
        self._notif_var.set(f"🔔  Ready to harvest: {ready_count}")
        self.root.after(1000, self._tick)

    def _show_alarm(self, crop_name):
        pop = tk.Toplevel(self.root)
        pop.title("🚨 Harvest Alert")
        pop.geometry("340x140")
        pop.configure(bg=C["panel"])
        pop.transient(self.root)
        tk.Label(pop, text="🚨 HARVEST READY!", font=("Segoe UI",14,"bold"),
                 bg=C["panel"], fg=C["danger"]).pack(pady=(20,5))
        tk.Label(pop, text=f"{crop_name} is ready to harvest now!",
                 font=("Segoe UI",11), bg=C["panel"], fg=C["text"]).pack()
        styled_button(pop, "OK", pop.destroy).pack(pady=12)

    # ── Content utilities ────────────────────────────────────────
    def clear_content(self):
        self._live_labels.clear()
        if self.current_frame:
            self.current_frame.destroy()
        self.current_frame = tk.Frame(self.content_frame, bg=C["bg"])
        self.current_frame.pack(fill="both", expand=True)

    def _section(self, parent, title):
        f = tk.Frame(parent, bg=C["panel"], padx=16, pady=12)
        tk.Label(f, text=title, font=("Segoe UI",12,"bold"),
                 bg=C["panel"], fg=C["accent"]).pack(anchor="w")
        tk.Frame(f, bg=C["border"], height=1).pack(fill="x", pady=(6,8))
        return f

    # ══════════════════════════════════════════════════════════════
    #  DASHBOARD
    # ══════════════════════════════════════════════════════════════
    def show_dashboard(self):
        self.clear_content()
        _, inner = scrollable(self.current_frame)

        pad = tk.Frame(inner, bg=C["bg"])
        pad.pack(fill="both", expand=True, padx=24, pady=18)

        # KPI row
        kpi_row = tk.Frame(pad, bg=C["bg"])
        kpi_row.pack(fill="x", pady=(0,18))
        total_rev  = sum(s["total"] for s in sales_records)
        total_harv = sum(h["amount_kg"] for h in harvest_records)
        kpi_card(kpi_row, "Crops Planted",   str(len(crops_planted)),       C["accent"])
        kpi_card(kpi_row, "Total Harvested",  f"{total_harv:.0f} kg",        C["accent2"])
        kpi_card(kpi_row, "Total Revenue",    f"Le {total_rev:,.0f}",        C["gold"])
        kpi_card(kpi_row, "Season",           get_current_season(),          C["warn"])
        kpi_card(kpi_row, "Sales Records",    str(len(sales_records)),        C["muted"])

        # Bar chart of planted crops
        chart_sec = self._section(pad, "Currently Planted Crops")
        chart_sec.pack(fill="x", pady=(0,14))
        if crops_planted:
            self._draw_bar_chart(chart_sec)
        else:
            tk.Label(chart_sec, text="No crops planted yet. Go to Crop Rotation to start.",
                     bg=C["panel"], fg=C["muted"], font=("Segoe UI",11)).pack(pady=20)

        # Harvest soon
        soon_sec = self._section(pad, "Upcoming Harvests (within 7 days)")
        soon_sec.pack(fill="x", pady=(0,14))
        soon = [c for c in crops_planted if 0 < estimate_harvest_seconds_left(c)[0] <= 7*86400]
        if soon:
            for c in soon:
                sec_left,_ = estimate_harvest_seconds_left(c)
                r = tk.Frame(soon_sec, bg=C["card"], pady=6)
                r.pack(fill="x", pady=2)
                icon = CROP_ICONS.get(c["name"],"🌱")
                tk.Label(r, text=f"{icon} {c['name']}", font=("Segoe UI",11,"bold"),
                         bg=C["card"], fg=C["text"]).pack(side="left", padx=12)
                tk.Label(r, text=fmt_time(sec_left), font=("Segoe UI",11),
                         bg=C["card"], fg=C["warn"]).pack(side="right", padx=12)
        else:
            tk.Label(soon_sec, text="No harvests due in the next 7 days.",
                     bg=C["panel"], fg=C["muted"]).pack(pady=8)

        # Harvest summary
        if harvest_records:
            h_sec = self._section(pad, "Harvest Summary by Crop")
            h_sec.pack(fill="x")
            summary = {}
            for h in harvest_records:
                summary[h["crop"]] = summary.get(h["crop"],0) + h["amount_kg"]
            for crop, amt in summary.items():
                r = tk.Frame(h_sec, bg=C["card"], pady=5)
                r.pack(fill="x", pady=2)
                icon = CROP_ICONS.get(crop,"🌱")
                tk.Label(r, text=f"{icon} {crop}", font=("Segoe UI",10),
                         bg=C["card"], fg=C["text"]).pack(side="left", padx=12)
                tk.Label(r, text=f"{amt:.1f} kg", font=("Segoe UI",10,"bold"),
                         bg=C["card"], fg=C["accent"]).pack(side="right", padx=12)

    def _draw_bar_chart(self, parent):
        if not crops_planted:
            return
        names  = [c["name"] for c in crops_planted]
        counts = [c["plants"] for c in crops_planted]
        max_c  = max(counts) if counts else 1

        W, H    = 760, 260
        pad_l   = 60; pad_b = 60; pad_t = 20; pad_r = 20
        plot_w  = W - pad_l - pad_r
        plot_h  = H - pad_t - pad_b
        n       = len(names)
        bw      = max(20, min(70, plot_w // (n+1)))
        gap     = max(8,  (plot_w - n*bw) // (n+1))

        canvas = tk.Canvas(parent, bg=C["panel"], width=W, height=H, highlightthickness=0)
        canvas.pack(pady=10)

        # Axes
        canvas.create_line(pad_l, pad_t, pad_l, H-pad_b, fill=C["border"], width=1)
        canvas.create_line(pad_l, H-pad_b, W-pad_r, H-pad_b, fill=C["border"], width=1)

        # Y grid & labels
        steps = 5
        for i in range(steps+1):
            y_val = max_c * i / steps
            y_px  = H - pad_b - (y_val/max_c)*plot_h
            canvas.create_line(pad_l, y_px, W-pad_r, y_px,
                               fill=C["border"], dash=(2,4), width=1)
            canvas.create_text(pad_l-6, y_px, text=f"{int(y_val)}", anchor="e",
                               fill=C["muted"], font=("Segoe UI",8))

        # Bars
        for i, (name, count) in enumerate(zip(names, counts)):
            x0   = pad_l + gap + i*(bw+gap)
            x1   = x0 + bw
            bh   = (count/max_c)*plot_h
            y0   = H - pad_b - bh
            y1   = H - pad_b
            col  = C["chartbars"][i % len(C["chartbars"])]
            canvas.create_rectangle(x0, y0, x1, y1, fill=col, outline="", width=0)
            canvas.create_rectangle(x0, y0, x0+bw//3, y1, fill=_lighten(col), outline="", width=0)
            canvas.create_text((x0+x1)//2, y0-6, text=str(count),
                               fill=C["text"], font=("Segoe UI",8,"bold"))
            icon = CROP_ICONS.get(name,"🌱")
            canvas.create_text((x0+x1)//2, H-pad_b+10, text=icon,
                               fill=C["text"], font=("Segoe UI",12), anchor="n")
            canvas.create_text((x0+x1)//2, H-pad_b+26, text=name[:8],
                               fill=C["muted"], font=("Segoe UI",8), anchor="n")

        canvas.create_text(pad_l//2, pad_t + plot_h//2, text="Plants",
                           fill=C["muted"], font=("Segoe UI",9), angle=90)

    # ══════════════════════════════════════════════════════════════
    #  CROP ROTATION
    # ══════════════════════════════════════════════════════════════
    def show_rotation(self):
        self.clear_content()
        _, inner = scrollable(self.current_frame)
        pad = tk.Frame(inner, bg=C["bg"])
        pad.pack(fill="both", expand=True, padx=24, pady=18)

        left  = tk.Frame(pad, bg=C["bg"])
        right = tk.Frame(pad, bg=C["bg"])
        left.pack(side="left", fill="both", expand=True, padx=(0,10))
        right.pack(side="left", fill="both", expand=True)

        # ── Form ─────────────────────────────────────────────────
        form_sec = self._section(left, "Plan Your Next Crop")
        form_sec.pack(fill="x")

        def row(parent, lbl_text):
            r = tk.Frame(parent, bg=C["panel"])
            r.pack(fill="x", pady=5)
            tk.Label(r, text=lbl_text, font=("Segoe UI",10),
                     bg=C["panel"], fg=C["muted"], width=22, anchor="w").pack(side="left")
            return r

        r0 = row(form_sec, "Plot Name / ID")
        e_plot = entry_widget(r0, width=26); e_plot.pack(side="left", ipady=4)

        r1 = row(form_sec, "Last Crop Planted")
        v_last = tk.StringVar()
        combo_widget(r1, v_last, ALL_CROPS, width=26).pack(side="left")

        r2 = row(form_sec, "Soil Condition")
        v_soil = tk.StringVar(value="Fair")
        combo_widget(r2, v_soil, ["Poor","Fair","Rich"], width=26).pack(side="left")

        r3 = row(form_sec, "Plot Size (acres)")
        e_acres = entry_widget(r3, width=10); e_acres.pack(side="left", ipady=4)
        e_acres.insert(0,"1")

        r4 = row(form_sec, "Number of Plants")
        e_plants = entry_widget(r4, width=10); e_plants.pack(side="left", ipady=4)
        e_plants.insert(0,"Auto")

        # Results area
        res_sec = self._section(left, "Recommendation")
        res_sec.pack(fill="x", pady=10)

        v_next  = tk.StringVar(value="—")
        v_fert  = tk.StringVar(value="—")
        v_tip   = tk.StringVar(value="—")
        v_maturity = tk.StringVar(value="—")

        for lbl, var, col in [
            ("Next Crop →",      v_next,     C["accent"]),
            ("Fertiliser →",     v_fert,     C["text"]),
            ("Maturity →",       v_maturity, C["muted"]),
            ("Farming Tip →",    v_tip,      C["warn"]),
        ]:
            r = tk.Frame(res_sec, bg=C["panel"]); r.pack(fill="x", pady=3)
            tk.Label(r, text=lbl, font=("Segoe UI",10), bg=C["panel"],
                     fg=C["muted"], width=18, anchor="w").pack(side="left")
            tk.Label(r, textvariable=var, font=("Segoe UI",10),
                     bg=C["panel"], fg=col, wraplength=340, justify="left").pack(side="left")

        # Btn row
        btn_row = tk.Frame(left, bg=C["bg"]); btn_row.pack(fill="x", pady=8)

        def get_rec():
            last = v_last.get(); soil = v_soil.get()
            try:
                acres = float(e_acres.get())
                if acres <= 0: raise ValueError
            except:
                messagebox.showerror("Invalid","Plot size must be a positive number."); return
            if not last:
                messagebox.showerror("Missing","Select last crop planted."); return
            nc   = recommend_crop(last, soil)
            fert = get_fertilizer(soil, nc, acres)
            mat  = MATURITY_DAYS.get(nc, 90)
            tip  = CROP_TIPS.get(nc,"—")
            v_next.set(f"{CROP_ICONS.get(nc,'')} {nc}")
            v_fert.set(fert)
            v_maturity.set(f"~{mat} days" if mat >= 1 else "~20 seconds (test)")
            v_tip.set(tip)

        def plant_it():
            last = v_last.get(); soil = v_soil.get()
            try:
                acres = float(e_acres.get()); assert acres > 0
            except:
                messagebox.showerror("Invalid","Enter a valid plot size."); return
            if not last:
                messagebox.showerror("Missing","Select last crop."); return
            nc      = recommend_crop(last, soil)
            mat     = MATURITY_DAYS.get(nc, 90)
            try:
                pl = int(e_plants.get())
            except:
                pl = int(acres * 500)
            crops_planted.append({
                "name": nc, "plants": pl,
                "planted_date": datetime.now(),
                "maturity_days": mat, "plot_acres": acres
            })
            save_data()
            ready_in = "~20 seconds (test)" if mat < 0.01 else f"~{mat} days"
            messagebox.showinfo("Planted ✅",
                f"{CROP_ICONS.get(nc,'')} {nc} planted on {acres} acre(s).\n"
                f"Ready in {ready_in}.")

        def plant_test():
            crops_planted.append({
                "name": "TestCrop1", "plants": 100,
                "planted_date": datetime.now(),
                "maturity_days": 0.0002, "plot_acres": 0.1
            })
            save_data()
            messagebox.showinfo("Test Planted 🧪",
                "TestCrop1 planted — ready for harvest in ~20 seconds.\n"
                "Go to Harvest to see the countdown.")

        styled_button(btn_row, "Get Recommendation", get_rec).pack(side="left")
        styled_button(btn_row, "Plant This Crop", plant_it,
                      color="#2e7d32").pack(side="left", padx=8)
        styled_button(btn_row, "Plant Test Crop (20 sec)", plant_test,
                      color=C["warn"]).pack(side="left")

        # ── Soil guide ───────────────────────────────────────────
        soil_sec = self._section(right, "Soil Condition Guide")
        soil_sec.pack(fill="x")
        for title, desc, col in [
            ("🔴 Poor",  "Cracked, compacted, poor water absorption. Needs heavy amendment.", C["danger"]),
            ("🟡 Fair",  "Moderate structure. Retains some moisture. Light fertiliser helps.", C["warn"]),
            ("🟢 Rich",  "Loose, dark, excellent drainage & nutrients. Minimal inputs needed.", C["accent"]),
        ]:
            r = tk.Frame(soil_sec, bg=C["card"], padx=12, pady=10)
            r.pack(fill="x", pady=4)
            tk.Label(r, text=title, font=("Segoe UI",10,"bold"),
                     bg=C["card"], fg=col).pack(anchor="w")
            tk.Label(r, text=desc, font=("Segoe UI",9),
                     bg=C["card"], fg=C["muted"], wraplength=290, justify="left").pack(anchor="w")

        # Rotation guide
        rot_sec = self._section(right, "Rotation Principles")
        rot_sec.pack(fill="x", pady=10)
        for line in [
            "• After cereals (Rice/Maize) → plant legumes to fix nitrogen.",
            "• After legumes → plant cereals or roots to exploit soil N.",
            "• After roots → plant leafy vegetables or cereals.",
            "• Avoid planting the same family 2 seasons in a row.",
            "• Rainy season boosts Maize, Cassava & Groundnut by ~8%.",
            "• Dry season boosts Tomato, Pepper & Okra by ~12%.",
        ]:
            tk.Label(rot_sec, text=line, font=("Segoe UI",9),
                     bg=C["panel"], fg=C["muted"], anchor="w",
                     wraplength=290, justify="left").pack(anchor="w", pady=2)

    # ══════════════════════════════════════════════════════════════
    #  HARVEST MANAGEMENT
    # ══════════════════════════════════════════════════════════════
    def show_harvest_management(self):
        self.clear_content()
        _, inner = scrollable(self.current_frame)
        pad = tk.Frame(inner, bg=C["bg"])
        pad.pack(fill="both", expand=True, padx=24, pady=18)

        hdr = tk.Frame(pad, bg=C["bg"])
        hdr.pack(fill="x", pady=(0,14))
        tk.Label(hdr, text="Harvest Management", font=("Segoe UI",16,"bold"),
                 bg=C["bg"], fg=C["text"]).pack(side="left")
        styled_button(hdr, "↻ Refresh", self.show_harvest_management,
                      color=C["panel"]).pack(side="right")

        if not crops_planted:
            empty = tk.Frame(pad, bg=C["panel"], padx=30, pady=40)
            empty.pack(fill="x")
            tk.Label(empty, text="🌱 No crops planted yet.",
                     font=("Segoe UI",14), bg=C["panel"], fg=C["muted"]).pack()
            tk.Label(empty, text="Go to Crop Rotation to plant your first crop.",
                     font=("Segoe UI",10), bg=C["panel"], fg=C["border"]).pack(pady=6)
            return

        for crop in crops_planted:
            self._harvest_card(pad, crop)

    def _harvest_card(self, parent, crop):
        key           = crop["name"] + crop["planted_date"].isoformat()
        sec_left, adj = estimate_harvest_seconds_left(crop)
        pct           = pct_complete(crop)
        icon          = CROP_ICONS.get(crop["name"], "🌱")

        card = tk.Frame(parent, bg=C["card"], padx=16, pady=14, relief="flat")
        card.pack(fill="x", pady=6)
        tk.Frame(card, bg=C["border"], width=4).pack(side="left", fill="y", padx=(0,14))

        body = tk.Frame(card, bg=C["card"])
        body.pack(side="left", fill="both", expand=True)

        # Header row
        h_row = tk.Frame(body, bg=C["card"]); h_row.pack(fill="x")
        tk.Label(h_row, text=f"{icon} {crop['name']}", font=("Segoe UI",13,"bold"),
                 bg=C["card"], fg=C["text"]).pack(side="left")

        # Status badge
        if sec_left <= 0:
            badge_text, badge_col = "● READY NOW", C["danger"]
        elif pct >= 75:
            badge_text, badge_col = "● Almost Ready", C["warn"]
        else:
            badge_text, badge_col = "● Growing", C["accent"]
        tk.Label(h_row, text=badge_text, font=("Segoe UI",9,"bold"),
                 bg=C["card"], fg=badge_col).pack(side="right")

        # Details row
        d_row = tk.Frame(body, bg=C["card"]); d_row.pack(fill="x", pady=4)
        planted_str  = crop["planted_date"].strftime("%d %b %Y  %H:%M")
        expected_date = crop["planted_date"] + timedelta(days=adj)
        exp_str = expected_date.strftime("%d %b %Y") if adj >= 1 else expected_date.strftime("%H:%M:%S")
        for txt in [f"Planted: {planted_str}", f"Expected: {exp_str}",
                    f"Plants: {crop['plants']}", f"Acres: {crop.get('plot_acres',1)}"]:
            tk.Label(d_row, text=txt, font=("Segoe UI",9), bg=C["card"],
                     fg=C["muted"]).pack(side="left", padx=12)

        # Countdown
        c_row = tk.Frame(body, bg=C["card"]); c_row.pack(fill="x", pady=(4,6))
        tk.Label(c_row, text="Time left:", font=("Segoe UI",9),
                 bg=C["card"], fg=C["muted"]).pack(side="left")
        t_lbl = tk.Label(c_row, text=fmt_time(sec_left),
                         font=("Segoe UI",11,"bold"), bg=C["card"], fg=C["accent"])
        t_lbl.pack(side="left", padx=8)
        p_lbl = tk.Label(c_row, text=f"{pct:.0f}%", font=("Segoe UI",9,"bold"),
                         bg=C["card"], fg=C["muted"])
        p_lbl.pack(side="right")

        # Progress bar
        pb_style = "red.Horizontal.TProgressbar" if sec_left <= 0 else \
                   "amber.Horizontal.TProgressbar" if pct >= 75 else \
                   "green.Horizontal.TProgressbar"
        pb = ttk.Progressbar(body, value=pct, maximum=100,
                             style=pb_style, length=500)
        pb.pack(fill="x", pady=(2,8))

        # Tip
        tip = CROP_TIPS.get(crop["name"],"")
        if tip:
            tk.Label(body, text=f"💡 {tip}", font=("Segoe UI",9,"italic"),
                     bg=C["card"], fg=C["muted"], wraplength=600, justify="left").pack(anchor="w")

        # Buttons
        btn_row = tk.Frame(body, bg=C["card"]); btn_row.pack(anchor="w", pady=(8,0))
        if sec_left <= 0:
            def do_harvest(cn=crop["name"]):
                self.record_harvest_dialog(cn)
            styled_button(btn_row, "🌾 Record Harvest", do_harvest).pack(side="left")
        else:
            tk.Label(btn_row, text="Harvest will be available when ready.",
                     font=("Segoe UI",9), bg=C["card"], fg=C["border"]).pack(side="left")

        def do_delete(cn=crop["name"], pd=crop["planted_date"]):
            if messagebox.askyesno("Remove Crop",
                    f"Remove {cn} from planted list? (Not a harvest — crop will be lost.)"):
                global crops_planted
                crops_planted = [c for c in crops_planted
                                  if not (c["name"]==cn and c["planted_date"]==pd)]
                save_data()
                self.show_harvest_management()
        styled_button(btn_row, "🗑 Remove", do_delete,
                      color="#3e1a1a").pack(side="left", padx=8)

        # Register for live updates
        self._live_labels[key] = (t_lbl, pb, p_lbl)

    def record_harvest_dialog(self, crop_name):
        dlg = tk.Toplevel(self.root)
        dlg.title("Record Harvest")
        dlg.geometry("440x380")
        dlg.configure(bg=C["bg"])
        dlg.resizable(False, False)
        dlg.transient(self.root); dlg.grab_set()

        card = tk.Frame(dlg, bg=C["panel"], padx=28, pady=24)
        card.place(relx=0.5, rely=0.5, anchor="center")

        icon = CROP_ICONS.get(crop_name,"🌱")
        tk.Label(card, text=f"{icon} Harvesting: {crop_name}",
                 font=("Segoe UI",14,"bold"), bg=C["panel"], fg=C["accent"]).pack(pady=(0,18))

        def frow(lbl, hide=False):
            r = tk.Frame(card, bg=C["panel"]); r.pack(fill="x", pady=5)
            tk.Label(r, text=lbl, font=("Segoe UI",10), bg=C["panel"],
                     fg=C["muted"], width=28, anchor="w").pack(side="left")
            e = entry_widget(r, width=20, show="*" if hide else "")
            e.pack(side="left", ipady=4)
            return e

        e_amt   = frow("Amount harvested (kg):")
        v_soil  = tk.StringVar(value="Fair")
        r_soil  = tk.Frame(card, bg=C["panel"]); r_soil.pack(fill="x", pady=5)
        tk.Label(r_soil, text="Soil condition after harvest:", font=("Segoe UI",10),
                 bg=C["panel"], fg=C["muted"], width=28, anchor="w").pack(side="left")
        combo_widget(r_soil, v_soil, ["Poor","Fair","Rich"], width=18).pack(side="left")
        e_notes = frow("Notes (optional):")

        err = tk.Label(card, text="", fg=C["danger"], bg=C["panel"], font=("Segoe UI",9))
        err.pack()

        def save():
            global crops_planted
            try:
                amt = float(e_amt.get())
                if amt <= 0: raise ValueError
            except:
                err.config(text="Enter a positive number for kg."); return
            soil  = v_soil.get()
            notes = e_notes.get().strip()
            crops_planted = [c for c in crops_planted if c["name"] != crop_name]
            harvest_records.append({
                "crop": crop_name, "amount_kg": amt,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "notes": notes, "soil": soil
            })
            save_data()
            messagebox.showinfo("Harvest Recorded ✅",
                f"{icon} {crop_name}: {amt} kg recorded.\n"
                f"Crop is now available for sale.", parent=dlg)
            dlg.destroy()
            self.show_harvest_management()

        styled_button(card, "Save Harvest", save).pack(side="left", pady=12, padx=4)
        styled_button(card, "Cancel", dlg.destroy, color="#3e1a1a").pack(side="left", padx=4)

    # ══════════════════════════════════════════════════════════════
    #  CROP SALE
    # ══════════════════════════════════════════════════════════════
    def show_crop_sale(self):
        self.clear_content()
        _, inner = scrollable(self.current_frame)
        pad = tk.Frame(inner, bg=C["bg"])
        pad.pack(fill="both", expand=True, padx=24, pady=18)

        form_sec = self._section(pad, "Register New Sale")
        form_sec.pack(fill="x", pady=(0,14))

        def frow(parent, lbl_text):
            r = tk.Frame(parent, bg=C["panel"]); r.pack(fill="x", pady=5)
            tk.Label(r, text=lbl_text, font=("Segoe UI",10), bg=C["panel"],
                     fg=C["muted"], width=24, anchor="w").pack(side="left")
            return r

        r0 = frow(form_sec, "Crop")
        v_crop = tk.StringVar()
        crop_opts = list(dict.fromkeys([h["crop"] for h in harvest_records]))
        combo_widget(r0, v_crop, crop_opts, width=24).pack(side="left")
        if not crop_opts:
            tk.Label(form_sec, text="⚠ No harvested crops yet. Record a harvest first.",
                     bg=C["panel"], fg=C["warn"], font=("Segoe UI",9)).pack(anchor="w")

        r1 = frow(form_sec, "Quantity sold (kg)")
        e_qty = entry_widget(r1, width=18); e_qty.pack(side="left", ipady=4)

        r2 = frow(form_sec, "Price per kg (Le)")
        e_price = entry_widget(r2, width=18); e_price.pack(side="left", ipady=4)

        r3 = frow(form_sec, "Buyer Name (optional)")
        e_buyer = entry_widget(r3, width=24); e_buyer.pack(side="left", ipady=4)

        err_lbl = tk.Label(form_sec, text="", fg=C["danger"],
                           bg=C["panel"], font=("Segoe UI",9))
        err_lbl.pack(anchor="w")

        def record_sale():
            crop = v_crop.get()
            if not crop:
                err_lbl.config(text="Select a crop."); return
            try:
                qty   = float(e_qty.get()); price = float(e_price.get())
                if qty <= 0 or price <= 0: raise ValueError
            except:
                err_lbl.config(text="Enter positive numbers for qty and price."); return
            total = qty * price
            sales_records.append({
                "crop": crop, "qty_kg": qty, "price": price,
                "total": total, "buyer": e_buyer.get().strip(),
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            save_data()
            err_lbl.config(text="")
            e_qty.delete(0,tk.END); e_price.delete(0,tk.END); e_buyer.delete(0,tk.END)
            messagebox.showinfo("Sale Recorded ✅",
                f"Sold {qty} kg of {crop}\n@ Le {price}/kg = Le {total:,.0f}")
            refresh_table()

        styled_button(form_sec, "Record Sale", record_sale).pack(anchor="w", pady=10)

        # Table
        tbl_sec = self._section(pad, "Sales History")
        tbl_sec.pack(fill="both", expand=True)

        self._sale_tbl_parent = tbl_sec

        def refresh_table():
            for w in tbl_sec.winfo_children():
                if isinstance(w, (ttk.Treeview, tk.Label, tk.Frame)) and getattr(w,"_sale_widget",False):
                    w.destroy()
            cols = ("Crop","Qty (kg)","Price/kg","Total (Le)","Buyer","Date")
            tree = ttk.Treeview(tbl_sec, columns=cols, show="headings", height=10)
            for col in cols:
                tree.heading(col, text=col)
                tree.column(col, width=130)
            tree._sale_widget = True
            total_rev = 0
            for s in sales_records:
                tree.insert("","end", values=(
                    s["crop"], s["qty_kg"], s["price"],
                    f"{s['total']:,.0f}", s.get("buyer","—"), s["date"]
                ))
                total_rev += s["total"]
            tree.pack(fill="both", expand=True, padx=4, pady=4)
            lbl = tk.Label(tbl_sec, text=f"TOTAL REVENUE: Le {total_rev:,.0f}",
                           font=("Segoe UI",12,"bold"), bg=C["panel"], fg=C["gold"])
            lbl._sale_widget = True
            lbl.pack(anchor="e", padx=12, pady=8)

            # Export button
            def export_csv():
                path = filedialog.asksaveasfilename(
                    defaultextension=".csv", filetypes=[("CSV","*.csv")],
                    initialfile="sales_report.csv")
                if not path: return
                with open(path,"w", newline="") as f:
                    w = csv.writer(f)
                    w.writerow(cols)
                    for s in sales_records:
                        w.writerow([s["crop"],s["qty_kg"],s["price"],
                                    f"{s['total']:.2f}",s.get("buyer",""),s["date"]])
                messagebox.showinfo("Exported","Sales report saved to CSV.")
            exp = styled_button(tbl_sec, "⬇ Export CSV", export_csv, color=C["panel"])
            exp._sale_widget = True
            exp.pack(anchor="e", padx=12, pady=(0,8))

        refresh_table()

    # ══════════════════════════════════════════════════════════════
    #  ANALYTICS
    # ══════════════════════════════════════════════════════════════
    def show_analytics(self):
        self.clear_content()
        _, inner = scrollable(self.current_frame)
        pad = tk.Frame(inner, bg=C["bg"])
        pad.pack(fill="both", expand=True, padx=24, pady=18)

        # Revenue by crop
        rev_sec = self._section(pad, "Revenue by Crop")
        rev_sec.pack(fill="x", pady=(0,14))
        rev_by_crop = {}
        for s in sales_records:
            rev_by_crop[s["crop"]] = rev_by_crop.get(s["crop"],0) + s["total"]

        if rev_by_crop:
            total   = sum(rev_by_crop.values())
            sorted_ = sorted(rev_by_crop.items(), key=lambda x:-x[1])
            for crop, rev in sorted_:
                r = tk.Frame(rev_sec, bg=C["card"]); r.pack(fill="x", pady=3)
                icon = CROP_ICONS.get(crop,"🌱")
                tk.Label(r, text=f"{icon} {crop}", font=("Segoe UI",10),
                         bg=C["card"], fg=C["text"], width=20, anchor="w").pack(side="left", padx=10)
                pct = rev/total*100 if total else 0
                bar_w = int(pct * 4)
                tk.Frame(r, bg=C["accent"], width=max(4,bar_w), height=16).pack(side="left")
                tk.Label(r, text=f"  Le {rev:,.0f}  ({pct:.1f}%)",
                         font=("Segoe UI",10), bg=C["card"], fg=C["gold"]).pack(side="left")
        else:
            tk.Label(rev_sec, text="No sales recorded yet.",
                     bg=C["panel"], fg=C["muted"]).pack(pady=12)

        # Harvest yield
        yld_sec = self._section(pad, "Harvest Yield Summary")
        yld_sec.pack(fill="x", pady=(0,14))
        yld = {}
        for h in harvest_records:
            yld[h["crop"]] = yld.get(h["crop"],0) + h["amount_kg"]
        if yld:
            for crop, kg in sorted(yld.items(), key=lambda x:-x[1]):
                r = tk.Frame(yld_sec, bg=C["card"]); r.pack(fill="x", pady=3)
                icon = CROP_ICONS.get(crop,"🌱")
                tk.Label(r, text=f"{icon} {crop}", font=("Segoe UI",10),
                         bg=C["card"], fg=C["text"], width=20, anchor="w").pack(side="left", padx=10)
                tk.Label(r, text=f"{kg:.1f} kg", font=("Segoe UI",10,"bold"),
                         bg=C["card"], fg=C["accent2"]).pack(side="right", padx=10)
        else:
            tk.Label(yld_sec, text="No harvest data yet.",
                     bg=C["panel"], fg=C["muted"]).pack(pady=12)

        # Profit estimate (revenue - fertiliser cost estimate)
        prof_sec = self._section(pad, "Estimated Profit Snapshot")
        prof_sec.pack(fill="x")
        total_rev = sum(s["total"] for s in sales_records)
        # rough: assume avg 50 Le/kg fertiliser
        est_cost  = sum(h["amount_kg"] * 50 for h in harvest_records)
        profit    = total_rev - est_cost
        p_color   = C["accent"] if profit >= 0 else C["danger"]
        for lbl, val, col in [
            ("Total Revenue",         f"Le {total_rev:,.0f}", C["gold"]),
            ("Est. Fertiliser Cost",  f"Le {est_cost:,.0f}",  C["warn"]),
            ("Est. Net Profit",       f"Le {profit:,.0f}",    p_color),
        ]:
            r = tk.Frame(prof_sec, bg=C["card"]); r.pack(fill="x", pady=4)
            tk.Label(r, text=lbl, font=("Segoe UI",11), bg=C["card"],
                     fg=C["muted"], width=26, anchor="w").pack(side="left", padx=12)
            tk.Label(r, text=val, font=("Segoe UI",13,"bold"),
                     bg=C["card"], fg=col).pack(side="right", padx=12)
        tk.Label(prof_sec, text="* Fertiliser cost is estimated at Le 50/kg of yield.",
                 font=("Segoe UI",8), bg=C["panel"], fg=C["border"]).pack(anchor="w")

    # ══════════════════════════════════════════════════════════════
    #  HISTORY
    # ══════════════════════════════════════════════════════════════
    def show_history(self):
        self.clear_content()
        pad = tk.Frame(self.current_frame, bg=C["bg"])
        pad.pack(fill="both", expand=True, padx=24, pady=18)

        nb = ttk.Notebook(pad)
        nb.pack(fill="both", expand=True)
        style = ttk.Style()
        style.configure("TNotebook", background=C["bg"])
        style.configure("TNotebook.Tab", background=C["panel"],
                        foreground=C["text"], padding=(12,6))
        style.map("TNotebook.Tab", background=[("selected",C["accent"])],
                  foreground=[("selected","#0a1a0b")])

        # Harvest tab
        ht = tk.Frame(nb, bg=C["card"]); nb.add(ht, text="🌾  Harvest Records")
        cols_h = ("Crop","Amount (kg)","Date","Soil","Notes")
        t_h = ttk.Treeview(ht, columns=cols_h, show="headings")
        for col, w in zip(cols_h,[120,110,160,80,200]):
            t_h.heading(col,text=col); t_h.column(col,width=w)
        for rec in harvest_records:
            t_h.insert("","end", values=(
                rec["crop"],rec["amount_kg"],rec["date"],
                rec.get("soil","—"),rec.get("notes","")
            ))
        vsb = ttk.Scrollbar(ht, orient="vertical", command=t_h.yview)
        t_h.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y"); t_h.pack(fill="both", expand=True, padx=6, pady=6)

        def export_harvest():
            path = filedialog.asksaveasfilename(defaultextension=".csv",
                                                filetypes=[("CSV","*.csv")],
                                                initialfile="harvest_records.csv")
            if not path: return
            with open(path,"w",newline="") as f:
                w = csv.writer(f)
                w.writerow(cols_h)
                for rec in harvest_records:
                    w.writerow([rec["crop"],rec["amount_kg"],rec["date"],
                                rec.get("soil",""),rec.get("notes","")])
            messagebox.showinfo("Exported","Harvest records saved.")
        styled_button(ht,"⬇ Export Harvest CSV", export_harvest,
                      color=C["panel"]).pack(anchor="e", padx=8, pady=6)

        # Sales tab
        st = tk.Frame(nb, bg=C["card"]); nb.add(st, text="💰  Sales Records")
        cols_s = ("Crop","Qty (kg)","Price/kg","Total (Le)","Buyer","Date")
        t_s = ttk.Treeview(st, columns=cols_s, show="headings")
        for col, w in zip(cols_s,[110,90,90,110,130,160]):
            t_s.heading(col,text=col); t_s.column(col,width=w)
        for s in sales_records:
            t_s.insert("","end", values=(
                s["crop"],s["qty_kg"],s["price"],
                f"{s['total']:,.0f}", s.get("buyer","—"), s["date"]
            ))
        vsb2 = ttk.Scrollbar(st, orient="vertical", command=t_s.yview)
        t_s.configure(yscrollcommand=vsb2.set)
        vsb2.pack(side="right",fill="y"); t_s.pack(fill="both",expand=True,padx=6,pady=6)

    # ══════════════════════════════════════════════════════════════
    #  SETTINGS
    # ══════════════════════════════════════════════════════════════
    def show_settings(self):
        self.clear_content()
        _, inner = scrollable(self.current_frame)
        pad = tk.Frame(inner, bg=C["bg"])
        pad.pack(fill="both", expand=True, padx=24, pady=18)

        # Profile
        prof_sec = self._section(pad, "👤 Farmer Profile")
        prof_sec.pack(fill="x", pady=(0,14))

        if current_user and current_user in USERS:
            u = USERS[current_user]
            fields_data = [
                ("Full Name",    u.get("fullname","")),
                ("Username",     current_user),
                ("Phone",        u.get("phone","")),
                ("Role",         u.get("role","farmer")),
            ]
            for lbl, val in fields_data:
                r = tk.Frame(prof_sec, bg=C["card"]); r.pack(fill="x", pady=3)
                tk.Label(r, text=lbl, font=("Segoe UI",10), bg=C["card"],
                         fg=C["muted"], width=18, anchor="w").pack(side="left", padx=12)
                tk.Label(r, text=val, font=("Segoe UI",10,"bold"),
                         bg=C["card"], fg=C["text"]).pack(side="left")

        # Change password
        pw_sec = self._section(pad, "🔑 Change Password")
        pw_sec.pack(fill="x", pady=(0,14))

        def prow(lbl):
            r = tk.Frame(pw_sec, bg=C["panel"]); r.pack(fill="x", pady=4)
            tk.Label(r, text=lbl, font=("Segoe UI",10), bg=C["panel"],
                     fg=C["muted"], width=22, anchor="w").pack(side="left")
            e = entry_widget(r, width=22, show="*"); e.pack(side="left", ipady=4)
            return e

        e_curr = prow("Current Password")
        e_new  = prow("New Password")
        e_conf = prow("Confirm New Password")
        pw_err = tk.Label(pw_sec, text="", fg=C["danger"],
                          bg=C["panel"], font=("Segoe UI",9))
        pw_err.pack(anchor="w")

        def change_pw():
            if not current_user: return
            if USERS[current_user]["password"] != e_curr.get():
                pw_err.config(text="Current password incorrect."); return
            if e_new.get() != e_conf.get():
                pw_err.config(text="New passwords do not match."); return
            if len(e_new.get()) < 4:
                pw_err.config(text="Password must be at least 4 characters."); return
            USERS[current_user]["password"] = e_new.get()
            save_users()
            pw_err.config(text="", fg=C["accent"])
            messagebox.showinfo("Success","Password changed successfully.")

        styled_button(pw_sec, "Update Password", change_pw).pack(anchor="w", pady=8)

        # Data management
        data_sec = self._section(pad, "🗂 Data Management")
        data_sec.pack(fill="x")
        btn_row = tk.Frame(data_sec, bg=C["panel"]); btn_row.pack(pady=8)

        def clear_sales():
            if messagebox.askyesno("Clear Sales","Clear ALL sales records? This cannot be undone."):
                sales_records.clear(); save_data()
                messagebox.showinfo("Done","Sales records cleared.")

        def clear_harvests():
            if messagebox.askyesno("Clear Harvests","Clear ALL harvest records?"):
                harvest_records.clear(); save_data()
                messagebox.showinfo("Done","Harvest records cleared.")

        def logout():
            global current_user, start_work_time
            if messagebox.askyesno("Logout","Log out and return to login screen?"):
                current_user = None; start_work_time = None
                save_data()
                self.root.destroy()
                subprocess.Popen([sys.executable, __file__])

        styled_button(btn_row,"Clear Sales", clear_sales, color="#3e1a1a").pack(side="left",padx=4)
        styled_button(btn_row,"Clear Harvests", clear_harvests, color="#3e1a1a").pack(side="left",padx=4)
        styled_button(btn_row,"🚪 Logout", logout, color=C["danger"]).pack(side="left",padx=10)


# ══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════
def open_main_app():
    root = tk.Tk()
    app = CropAdvisorApp(root)
    root.mainloop()

if __name__ == "__main__":
    # This is used when gui.py is run directly (for testing)
    # However, we use main.py as the entry point.
    pass
