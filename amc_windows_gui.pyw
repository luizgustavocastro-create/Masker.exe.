#!/usr/bin/env python3
"""Graphical, manual-only Windows interface for amc_windows.py."""

import ctypes
import datetime
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

import amc_windows
import masker_secure_state


def relaunch_as_admin():
    if os.name != "nt":
        messagebox.showerror("Sistema nao suportado", "Esta interface funciona apenas no Windows.")
        return False
    if ctypes.windll.shell32.IsUserAnAdmin():
        return True
    executable = sys.executable
    if getattr(sys, "frozen", False):
        parameters = subprocess.list2cmdline(sys.argv[1:])
        working_directory = os.path.dirname(executable)
    else:
        script = os.path.abspath(__file__)
        parameters = f'"{script}"'
        working_directory = os.path.dirname(script)
    result = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", executable, parameters, working_directory, 1
    )
    if result <= 32:
        messagebox.showerror("Permissao necessaria", "Nao foi possivel obter permissao de administrador.")
    return False


def install_startup_task():
    if not getattr(sys, "frozen", False):
        raise RuntimeError("Instale a inicializacao usando a versao Masker.exe.")
    executable = os.path.abspath(sys.executable)
    task_name = "Masker Randomize MAC at Startup"
    task_command = f'"{executable}" --startup-randomize'
    result = subprocess.run(
        [
            "schtasks.exe",
            "/Create",
            "/TN",
            task_name,
            "/SC",
            "ONSTART",
            "/RU",
            "SYSTEM",
            "/RL",
            "HIGHEST",
            "/TR",
            task_command,
            "/F",
        ],
        text=True,
        capture_output=True,
        check=False,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or "Falha ao criar a tarefa.").strip())
    verification = subprocess.run(
        ["schtasks.exe", "/Query", "/TN", task_name],
        text=True,
        capture_output=True,
        check=False,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if verification.returncode:
        raise RuntimeError("A tarefa foi criada, mas nao pode ser confirmada.")
    state = masker_secure_state.load_state()
    state.update(
        {
            "adapter": "Wi-Fi",
            "startup_enabled": True,
            "encryption": "AES-256-GCM",
            "installed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
    )
    masker_secure_state.save_state(state)


def startup_randomize():
    state = masker_secure_state.load_state()
    interface = state.get("adapter", "Wi-Fi")
    last_error = None
    for _attempt in range(18):
        try:
            adapters = amc_windows.get_adapters()
            if any(item.get("Name") == interface for item in adapters):
                mac = amc_windows.random_mac()
                amc_windows.set_mac(interface, mac)
                state.update(
                    {
                        "adapter": interface,
                        "startup_enabled": True,
                        "encryption": "AES-256-GCM",
                        "last_requested_mac": mac,
                        "last_result": "success",
                        "last_run": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    }
                )
                masker_secure_state.save_state(state)
                return 0
        except Exception as error:
            last_error = str(error)
        time.sleep(5)
    state.update(
        {
            "adapter": interface,
            "last_result": "error",
            "last_error": last_error or "Adaptador nao encontrado.",
            "last_run": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
    )
    masker_secure_state.save_state(state)
    return 1


class MacChangerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Masker — Network Privacy")
        self.root.geometry("760x610")
        self.root.minsize(700, 570)
        self.root.configure(bg="#0b0d10")
        resource_root = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(resource_root, "masker.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("App.TFrame", background="#0b0d10")
        style.configure("Card.TFrame", background="#15181d")
        style.configure("Title.TLabel", background="#0b0d10", foreground="#ffffff", font=("Segoe UI Semibold", 24))
        style.configure("Subtitle.TLabel", background="#0b0d10", foreground="#8f98a6", font=("Segoe UI", 10))
        style.configure("CardTitle.TLabel", background="#15181d", foreground="#8f98a6", font=("Segoe UI Semibold", 9))
        style.configure("Value.TLabel", background="#15181d", foreground="#ffffff", font=("Consolas", 14, "bold"))
        style.configure("Body.TLabel", background="#15181d", foreground="#c9d0da", font=("Segoe UI", 10))
        style.configure("Primary.TButton", font=("Segoe UI Semibold", 10), padding=(18, 11), background="#ffffff", foreground="#0b0d10")
        style.map("Primary.TButton", background=[("active", "#dfe4ea"), ("disabled", "#555b63")])
        style.configure("Secondary.TButton", font=("Segoe UI", 10), padding=(15, 10), background="#242932", foreground="#ffffff")
        style.map("Secondary.TButton", background=[("active", "#323945")])
        style.configure("App.TCombobox", fieldbackground="#20242b", background="#20242b", foreground="#ffffff", arrowcolor="#ffffff", padding=8)
        style.configure("App.TEntry", fieldbackground="#20242b", foreground="#ffffff", insertcolor="#ffffff", padding=9)

        self.adapters = {}
        self.adapter_name = tk.StringVar()
        self.mac_value = tk.StringVar(value=amc_windows.format_mac(amc_windows.random_mac()))
        self.current_value = tk.StringVar(value="-")
        self.status_value = tk.StringVar(value="Carregando adaptadores...")
        self.protection_title = tk.StringVar(value="CHECKING STATUS")
        self.protection_detail = tk.StringVar(value="Reading network configuration...")
        self.security_value = tk.StringVar(value="AES-256-GCM  •  STARTUP CHECKING")

        frame = ttk.Frame(root, style="App.TFrame", padding=(34, 28))
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)

        header = ttk.Frame(frame, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 22))
        ttk.Label(header, text="MASKER", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="Local network identity control", style="Subtitle.TLabel").pack(anchor="w", pady=(2, 0))

        status_card = ttk.Frame(frame, style="Card.TFrame", padding=(22, 19))
        status_card.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        status_card.columnconfigure(1, weight=1)
        self.status_icon = tk.Canvas(status_card, width=44, height=44, bg="#15181d", highlightthickness=0)
        self.status_icon.grid(row=0, column=0, rowspan=2, padx=(0, 15))
        self.status_dot = self.status_icon.create_oval(7, 7, 37, 37, fill="#68707c", outline="")
        self.status_check = self.status_icon.create_text(22, 22, text="✓", fill="#0b0d10", font=("Segoe UI", 15, "bold"))
        ttk.Label(status_card, textvariable=self.protection_title, background="#15181d", foreground="#ffffff", font=("Segoe UI Semibold", 13)).grid(row=0, column=1, sticky="sw")
        ttk.Label(status_card, textvariable=self.protection_detail, style="Body.TLabel").grid(row=1, column=1, sticky="nw", pady=(3, 0))

        network_card = ttk.Frame(frame, style="Card.TFrame", padding=(22, 18))
        network_card.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        network_card.columnconfigure(0, weight=1)
        ttk.Label(network_card, text="NETWORK ADAPTER", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.adapter_box = ttk.Combobox(
            network_card, textvariable=self.adapter_name, state="readonly", style="App.TCombobox"
        )
        self.adapter_box.grid(row=1, column=0, sticky="ew", pady=(8, 15))
        self.adapter_box.bind("<<ComboboxSelected>>", self.on_adapter_selected)
        self.refresh_button = ttk.Button(network_card, text="Refresh", style="Secondary.TButton", command=self.refresh_adapters)
        self.refresh_button.grid(row=1, column=1, padx=(10, 0), pady=(8, 15))
        ttk.Label(network_card, text="CURRENT MAC", style="CardTitle.TLabel").grid(row=2, column=0, sticky="w")
        ttk.Label(network_card, textvariable=self.current_value, style="Value.TLabel").grid(row=3, column=0, sticky="w", pady=(5, 0))

        action_card = ttk.Frame(frame, style="Card.TFrame", padding=(22, 18))
        action_card.grid(row=3, column=0, sticky="ew", pady=(0, 14))
        action_card.columnconfigure(0, weight=1)
        ttk.Label(action_card, text="NEW RANDOMIZED MAC", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.mac_entry = ttk.Entry(action_card, textvariable=self.mac_value, style="App.TEntry")
        self.mac_entry.grid(row=1, column=0, sticky="ew", pady=(8, 14))
        self.generate_button = ttk.Button(action_card, text="Generate", style="Secondary.TButton", command=self.generate_mac)
        self.generate_button.grid(row=1, column=1, padx=(10, 0), pady=(8, 14))

        button_frame = ttk.Frame(action_card, style="Card.TFrame")
        button_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.change_button = ttk.Button(button_frame, text="Activate Masking", style="Primary.TButton", command=self.change_mac)
        self.change_button.pack(side="left", fill="x", expand=True)
        self.restore_button = ttk.Button(
            button_frame, text="Restore Original", style="Secondary.TButton", command=self.restore_mac
        )
        self.restore_button.pack(side="left", fill="x", expand=True, padx=(10, 0))

        footer = ttk.Frame(frame, style="App.TFrame")
        footer.grid(row=4, column=0, sticky="ew")
        ttk.Label(footer, textvariable=self.security_value, style="Subtitle.TLabel").pack(anchor="w")
        ttk.Label(footer, textvariable=self.status_value, style="Subtitle.TLabel", wraplength=680).pack(anchor="w", pady=(5, 0))

        try:
            secure_state = masker_secure_state.load_state()
            startup_label = "STARTUP ON" if secure_state.get("startup_enabled") else "STARTUP OFF"
            self.security_value.set(f"AES-256-GCM  •  {startup_label}")
        except Exception:
            self.security_value.set("AES-256-GCM  •  STATE UNAVAILABLE")
        self.refresh_adapters()

    def set_busy(self, busy, message=None):
        state = "disabled" if busy else "normal"
        self.refresh_button.configure(state=state)
        self.generate_button.configure(state=state)
        self.change_button.configure(state=state)
        self.restore_button.configure(state=state)
        self.adapter_box.configure(state="disabled" if busy else "readonly")
        if message:
            self.status_value.set(message)

    def run_background(self, action, success_message, refresh_after=False):
        self.set_busy(True)

        def worker():
            try:
                action()
            except Exception as error:
                self.root.after(0, lambda: self.operation_failed(str(error)))
                return
            self.root.after(0, lambda: self.operation_succeeded(success_message, refresh_after))

        threading.Thread(target=worker, daemon=True).start()

    def operation_failed(self, detail):
        self.set_busy(False, "Operacao nao concluida.")
        messagebox.showerror("Erro", detail)

    def operation_succeeded(self, message, refresh_after):
        self.set_busy(False, message)
        if refresh_after:
            self.refresh_adapters()
        messagebox.showinfo("Concluido", message)

    def refresh_adapters(self):
        self.set_busy(True, "Consultando adaptadores...")

        def worker():
            try:
                adapters = amc_windows.get_adapters()
            except Exception as error:
                self.root.after(0, lambda: self.operation_failed(str(error)))
                return
            self.root.after(0, lambda: self.load_adapters(adapters))

        threading.Thread(target=worker, daemon=True).start()

    def load_adapters(self, adapters):
        previous = self.adapter_name.get()
        self.adapters = {item.get("Name", ""): item for item in adapters if item.get("Name")}
        names = list(self.adapters)
        self.adapter_box["values"] = names
        if previous in self.adapters:
            self.adapter_name.set(previous)
        elif names:
            wifi = next((name for name in names if "wi-fi" in name.lower() or "wifi" in name.lower()), names[0])
            self.adapter_name.set(wifi)
        else:
            self.adapter_name.set("")
        self.on_adapter_selected()
        self.set_busy(False, f"{len(names)} adaptador(es) encontrado(s).")

    def on_adapter_selected(self, _event=None):
        adapter = self.adapters.get(self.adapter_name.get(), {})
        current = adapter.get("MacAddress") or "-"
        custom = adapter.get("CustomMac") or ""
        self.current_value.set(current)
        normalized_current = current.replace("-", "").replace(":", "").upper()
        normalized_custom = custom.replace("-", "").replace(":", "").upper()
        if normalized_custom and normalized_custom == normalized_current:
            self.status_icon.itemconfigure(self.status_dot, fill="#38d27a")
            self.status_icon.itemconfigure(self.status_check, text="✓", fill="#07130c")
            self.protection_title.set("MASKING ACTIVE")
            self.protection_detail.set(f"{self.adapter_name.get()} is using a randomized hardware address.")
        elif normalized_custom:
            self.status_icon.itemconfigure(self.status_dot, fill="#f4b942")
            self.status_icon.itemconfigure(self.status_check, text="!", fill="#1b1200")
            self.protection_title.set("RESTART REQUIRED")
            self.protection_detail.set("A custom address is configured but is not currently active.")
        else:
            self.status_icon.itemconfigure(self.status_dot, fill="#68707c")
            self.status_icon.itemconfigure(self.status_check, text="—", fill="#171a1f")
            self.protection_title.set("MASKING INACTIVE")
            self.protection_detail.set("The adapter is using its default hardware address.")

    def generate_mac(self):
        self.mac_value.set(amc_windows.format_mac(amc_windows.random_mac()))
        self.status_value.set("Novo endereco aleatorio gerado. Clique em Trocar MAC para aplicar.")

    def selected_adapter(self):
        name = self.adapter_name.get()
        if not name:
            messagebox.showwarning("Selecione um adaptador", "Escolha um adaptador de rede.")
            return None
        return name

    def change_mac(self):
        name = self.selected_adapter()
        if not name:
            return
        try:
            mac = amc_windows.normalize_mac(self.mac_value.get())
        except Exception as error:
            messagebox.showerror("MAC invalido", str(error))
            return
        if not messagebox.askokcancel(
            "Trocar MAC",
            "A conexao deste adaptador sera interrompida por alguns segundos. Continuar?",
        ):
            return
        self.run_background(
            lambda: amc_windows.set_mac(name, mac),
            "MAC alterado. O Windows pode levar alguns segundos para reconectar.",
            True,
        )

    def restore_mac(self):
        name = self.selected_adapter()
        if not name:
            return
        if not messagebox.askokcancel(
            "Restaurar MAC",
            "O adaptador sera reiniciado e a conexao caira por alguns segundos. Continuar?",
        ):
            return
        self.run_background(
            lambda: amc_windows.restore_mac(name),
            "Configuracao personalizada removida.",
            True,
        )


def main():
    if "--startup-randomize" in sys.argv:
        raise SystemExit(startup_randomize())

    root = tk.Tk()
    root.withdraw()
    if not relaunch_as_admin():
        root.destroy()
        return
    if "--install-startup" in sys.argv:
        try:
            install_startup_task()
        except Exception as error:
            messagebox.showerror("Masker", f"Nao foi possivel configurar a inicializacao:\n{error}")
        else:
            messagebox.showinfo(
                "Masker",
                "Inicializacao protegida ativada. Um novo MAC sera aplicado em cada boot.\nEstado local: AES-256-GCM.",
            )
        root.destroy()
        return
    root.deiconify()
    MacChangerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
