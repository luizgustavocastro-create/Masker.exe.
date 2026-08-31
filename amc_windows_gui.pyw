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
        self.root.title("Masker")
        self.root.geometry("620x390")
        self.root.minsize(560, 360)
        resource_root = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(resource_root, "masker.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)

        self.adapters = {}
        self.adapter_name = tk.StringVar()
        self.mac_value = tk.StringVar(value=amc_windows.format_mac(amc_windows.random_mac()))
        self.current_value = tk.StringVar(value="-")
        self.status_value = tk.StringVar(value="Carregando adaptadores...")

        frame = ttk.Frame(root, padding=22)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Adaptador de rede").grid(row=0, column=0, sticky="w")
        self.adapter_box = ttk.Combobox(
            frame, textvariable=self.adapter_name, state="readonly", width=45
        )
        self.adapter_box.grid(row=1, column=0, sticky="ew", pady=(5, 8))
        self.adapter_box.bind("<<ComboboxSelected>>", self.on_adapter_selected)
        self.refresh_button = ttk.Button(frame, text="Atualizar", command=self.refresh_adapters)
        self.refresh_button.grid(row=1, column=1, padx=(10, 0), pady=(5, 8))

        ttk.Label(frame, text="MAC atual").grid(row=2, column=0, sticky="w", pady=(7, 0))
        ttk.Label(frame, textvariable=self.current_value, font=("Segoe UI", 11, "bold")).grid(
            row=3, column=0, sticky="w", pady=(4, 12)
        )

        ttk.Label(frame, text="Novo MAC").grid(row=4, column=0, sticky="w")
        self.mac_entry = ttk.Entry(frame, textvariable=self.mac_value, width=30)
        self.mac_entry.grid(row=5, column=0, sticky="ew", pady=(5, 12))
        self.generate_button = ttk.Button(frame, text="Gerar outro", command=self.generate_mac)
        self.generate_button.grid(row=5, column=1, padx=(10, 0), pady=(5, 12))

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(8, 14))
        self.change_button = ttk.Button(button_frame, text="Trocar MAC", command=self.change_mac)
        self.change_button.pack(side="left", fill="x", expand=True)
        self.restore_button = ttk.Button(
            button_frame, text="Restaurar original", command=self.restore_mac
        )
        self.restore_button.pack(side="left", fill="x", expand=True, padx=(10, 0))

        ttk.Separator(frame).grid(row=7, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        ttk.Label(frame, textvariable=self.status_value, wraplength=550).grid(
            row=8, column=0, columnspan=2, sticky="w"
        )
        ttk.Label(
            frame,
            text="A conexao cai por alguns segundos somente quando voce clica em Trocar ou Restaurar.",
            foreground="#666666",
            wraplength=550,
        ).grid(row=9, column=0, columnspan=2, sticky="w", pady=(16, 0))

        frame.columnconfigure(0, weight=1)
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
        self.current_value.set(adapter.get("MacAddress") or "-")

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
