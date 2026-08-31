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
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image

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
        self.root.geometry("980x650")
        self.root.minsize(900, 610)
        self.root.configure(fg_color="#090a0c")
        resource_root = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(resource_root, "masker.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)

        self.adapters = {}
        self.adapter_name = tk.StringVar()
        self.mac_value = tk.StringVar(value=amc_windows.format_mac(amc_windows.random_mac()))
        self.current_value = tk.StringVar(value="-")
        self.status_value = tk.StringVar(value="Carregando adaptadores...")
        self.protection_title = tk.StringVar(value="CHECKING STATUS")
        self.protection_detail = tk.StringVar(value="Reading network configuration...")
        self.security_value = tk.StringVar(value="AES-256-GCM  •  STARTUP CHECKING")

        shell = ctk.CTkFrame(root, fg_color="#090a0c", corner_radius=0)
        shell.pack(fill="both", expand=True)
        shell.grid_columnconfigure(1, weight=1)
        shell.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(shell, width=216, fg_color="#111317", corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        if os.path.exists(icon_path):
            logo_image = ctk.CTkImage(Image.open(icon_path), size=(42, 42))
            logo = ctk.CTkLabel(sidebar, text="", image=logo_image)
            logo.image = logo_image
            logo.pack(anchor="w", padx=28, pady=(30, 8))
        ctk.CTkLabel(sidebar, text="MASKER", text_color="#ffffff", font=ctk.CTkFont("Segoe UI", 21, "bold")).pack(anchor="w", padx=28)
        ctk.CTkLabel(sidebar, text="NETWORK PRIVACY", text_color="#747b87", font=ctk.CTkFont("Segoe UI", 9, "bold")).pack(anchor="w", padx=28, pady=(2, 34))
        ctk.CTkButton(sidebar, text="Overview", anchor="w", height=42, corner_radius=10, fg_color="#ffffff", hover_color="#e4e7eb", text_color="#090a0c", font=ctk.CTkFont("Segoe UI", 11, "bold"), command=lambda: None).pack(fill="x", padx=18)
        ctk.CTkButton(sidebar, text="Network identity", anchor="w", height=42, corner_radius=10, fg_color="transparent", hover_color="#1c2026", text_color="#9ca3ad", command=lambda: None).pack(fill="x", padx=18, pady=(7, 0))
        ctk.CTkLabel(sidebar, text="LOCAL-ONLY CONTROL\nNo cloud connection", justify="left", text_color="#666d78", font=ctk.CTkFont("Segoe UI", 9)).pack(side="bottom", anchor="w", padx=28, pady=26)

        content = ctk.CTkScrollableFrame(shell, fg_color="#090a0c", corner_radius=0)
        content.grid(row=0, column=1, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(content, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=34, pady=(28, 22))
        ctk.CTkLabel(header, text="Network identity", text_color="#ffffff", font=ctk.CTkFont("Segoe UI", 26, "bold")).pack(anchor="w")
        ctk.CTkLabel(header, text="Control the hardware address presented to your local network.", text_color="#8b929d", font=ctk.CTkFont("Segoe UI", 11)).pack(anchor="w", pady=(4, 0))

        hero = ctk.CTkFrame(content, fg_color="#15181d", border_width=1, border_color="#242830", corner_radius=18)
        hero.grid(row=1, column=0, sticky="ew", padx=34, pady=(0, 14))
        hero.grid_columnconfigure(1, weight=1)
        self.status_icon = tk.Canvas(hero, width=64, height=64, bg="#15181d", highlightthickness=0)
        self.status_icon.grid(row=0, column=0, rowspan=2, padx=(24, 18), pady=24)
        self.status_dot = self.status_icon.create_oval(7, 7, 57, 57, fill="#68707c", outline="")
        self.status_check = self.status_icon.create_text(32, 32, text="✓", fill="#0b0d10", font=("Segoe UI", 20, "bold"))
        ctk.CTkLabel(hero, textvariable=self.protection_title, text_color="#ffffff", font=ctk.CTkFont("Segoe UI", 16, "bold")).grid(row=0, column=1, sticky="sw", pady=(24, 0))
        ctk.CTkLabel(hero, textvariable=self.protection_detail, text_color="#9ba2ad", font=ctk.CTkFont("Segoe UI", 10)).grid(row=1, column=1, sticky="nw", pady=(3, 24))
        self.refresh_button = ctk.CTkButton(hero, text="Refresh status", width=118, height=36, corner_radius=9, fg_color="#242932", hover_color="#313741", command=self.refresh_adapters)
        self.refresh_button.grid(row=0, column=2, rowspan=2, padx=24)

        metrics = ctk.CTkFrame(content, fg_color="transparent")
        metrics.grid(row=2, column=0, sticky="ew", padx=34, pady=(0, 14))
        metrics.grid_columnconfigure((0, 1, 2), weight=1, uniform="metric")

        mac_card = ctk.CTkFrame(metrics, fg_color="#15181d", border_width=1, border_color="#242830", corner_radius=16)
        mac_card.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        ctk.CTkLabel(mac_card, text="CURRENT MAC", text_color="#747d89", font=ctk.CTkFont("Segoe UI", 9, "bold")).pack(anchor="w", padx=18, pady=(17, 7))
        ctk.CTkLabel(mac_card, textvariable=self.current_value, text_color="#ffffff", font=ctk.CTkFont("Consolas", 13, "bold")).pack(anchor="w", padx=18, pady=(0, 18))

        adapter_card = ctk.CTkFrame(metrics, fg_color="#15181d", border_width=1, border_color="#242830", corner_radius=16)
        adapter_card.grid(row=0, column=1, sticky="nsew", padx=7)
        ctk.CTkLabel(adapter_card, text="ADAPTER", text_color="#747d89", font=ctk.CTkFont("Segoe UI", 9, "bold")).pack(anchor="w", padx=18, pady=(17, 7))
        ctk.CTkLabel(adapter_card, textvariable=self.adapter_name, text_color="#ffffff", font=ctk.CTkFont("Segoe UI", 13, "bold")).pack(anchor="w", padx=18, pady=(0, 18))

        crypto_card = ctk.CTkFrame(metrics, fg_color="#15181d", border_width=1, border_color="#242830", corner_radius=16)
        crypto_card.grid(row=0, column=2, sticky="nsew", padx=(7, 0))
        ctk.CTkLabel(crypto_card, text="LOCAL STATE", text_color="#747d89", font=ctk.CTkFont("Segoe UI", 9, "bold")).pack(anchor="w", padx=18, pady=(17, 7))
        ctk.CTkLabel(crypto_card, text="AES-256-GCM", text_color="#ffffff", font=ctk.CTkFont("Segoe UI", 13, "bold")).pack(anchor="w", padx=18, pady=(0, 18))

        control = ctk.CTkFrame(content, fg_color="#15181d", border_width=1, border_color="#242830", corner_radius=18)
        control.grid(row=3, column=0, sticky="ew", padx=34, pady=(0, 14))
        control.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(control, text="Masking control", text_color="#ffffff", font=ctk.CTkFont("Segoe UI", 15, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=22, pady=(20, 3))
        ctk.CTkLabel(control, text="Select an adapter and apply a locally administered unicast address.", text_color="#858d98", font=ctk.CTkFont("Segoe UI", 10)).grid(row=1, column=0, columnspan=2, sticky="w", padx=22, pady=(0, 17))

        self.adapter_box = ctk.CTkComboBox(control, variable=self.adapter_name, values=[], height=42, corner_radius=10, fg_color="#20242a", border_color="#303640", button_color="#303640", button_hover_color="#3b424d", dropdown_fg_color="#20242a", command=self.on_adapter_selected)
        self.adapter_box.grid(row=2, column=0, sticky="ew", padx=(22, 8), pady=(0, 12))
        self.generate_button = ctk.CTkButton(control, text="Generate new", width=128, height=42, corner_radius=10, fg_color="#262b33", hover_color="#343a44", command=self.generate_mac)
        self.generate_button.grid(row=2, column=1, padx=(8, 22), pady=(0, 12))

        self.mac_entry = ctk.CTkEntry(control, textvariable=self.mac_value, height=44, corner_radius=10, fg_color="#20242a", border_color="#303640", font=ctk.CTkFont("Consolas", 12))
        self.mac_entry.grid(row=3, column=0, columnspan=2, sticky="ew", padx=22, pady=(0, 16))

        button_frame = ctk.CTkFrame(control, fg_color="transparent")
        button_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=22, pady=(0, 22))
        button_frame.grid_columnconfigure((0, 1), weight=1)
        self.change_button = ctk.CTkButton(button_frame, text="Activate masking", height=46, corner_radius=11, fg_color="#ffffff", hover_color="#e2e5e9", text_color="#090a0c", font=ctk.CTkFont("Segoe UI", 11, "bold"), command=self.change_mac)
        self.change_button.grid(row=0, column=0, sticky="ew", padx=(0, 7))
        self.restore_button = ctk.CTkButton(button_frame, text="Restore original", height=46, corner_radius=11, fg_color="#252a32", hover_color="#343b45", font=ctk.CTkFont("Segoe UI", 11), command=self.restore_mac)
        self.restore_button.grid(row=0, column=1, sticky="ew", padx=(7, 0))

        footer = ctk.CTkFrame(content, fg_color="transparent")
        footer.grid(row=4, column=0, sticky="ew", padx=34, pady=(0, 26))
        ctk.CTkLabel(footer, textvariable=self.security_value, text_color="#747b86", font=ctk.CTkFont("Segoe UI", 9, "bold")).pack(anchor="w")
        ctk.CTkLabel(footer, textvariable=self.status_value, text_color="#747b86", font=ctk.CTkFont("Segoe UI", 9), wraplength=650, justify="left").pack(anchor="w", pady=(4, 0))

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
        self.adapter_box.configure(state="disabled" if busy else "normal")
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
        self.adapter_box.configure(values=names)
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

    ctk.set_appearance_mode("dark")
    if not relaunch_as_admin():
        return
    root = ctk.CTk()
    if "--install-startup" in sys.argv:
        root.withdraw()
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
    MacChangerApp(root)
    root.lift()
    root.focus_force()
    root.mainloop()


if __name__ == "__main__":
    main()
