#!/usr/bin/env python3
"""Automatic MAC address changer for Windows 10/11.

Uses Windows' network-adapter registry setting and native PowerShell cmdlets.
Run from an elevated (Administrator) terminal.
"""

import argparse
import ctypes
import json
import os
import random
import re
import subprocess
import sys
import time


MAC_RE = re.compile(r"^(?:[0-9A-Fa-f]{2}[:-]?){5}[0-9A-Fa-f]{2}$")
NETWORK_CLASS_KEY = (
    "HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Class\\"
    r"{4D36E972-E325-11CE-BFC1-08002BE10318}"
)


def require_windows_and_admin():
    if os.name != "nt":
        raise SystemExit("Este programa deve ser executado no Windows.")
    if not ctypes.windll.shell32.IsUserAnAdmin():
        raise SystemExit(
            "Abra o PowerShell ou Prompt de Comando como Administrador e tente novamente."
        )


def ps_quote(value):
    """Quote a value as a literal single-quoted PowerShell string."""
    return "'" + value.replace("'", "''") + "'"


def run_powershell(script, capture=True):
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        check=False,
        text=True,
        capture_output=capture,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout or "Falha desconhecida").strip()
        raise RuntimeError(detail)
    return result.stdout.strip() if capture else ""


def get_adapters():
    script = r"""
$classRoot = 'HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4D36E972-E325-11CE-BFC1-08002BE10318}'
$items = Get-NetAdapter -ErrorAction Stop | ForEach-Object {
    $adapter = $_
    $guid = $adapter.InterfaceGuid.ToString()
    $key = Get-ChildItem -LiteralPath $classRoot | Where-Object {
        (Get-ItemProperty -LiteralPath $_.PSPath -Name NetCfgInstanceId -ErrorAction SilentlyContinue).NetCfgInstanceId -eq $guid
    } | Select-Object -First 1
    $customMac = if ($key) {
        (Get-ItemProperty -LiteralPath $key.PSPath -Name NetworkAddress -ErrorAction SilentlyContinue).NetworkAddress
    } else { $null }
    [pscustomobject]@{
        Name = $adapter.Name
        InterfaceDescription = $adapter.InterfaceDescription
        Status = $adapter.Status
        MacAddress = $adapter.MacAddress
        CustomMac = $customMac
    }
}
$items | ConvertTo-Json -Compress
"""
    raw = run_powershell(script)
    if not raw:
        return []
    adapters = json.loads(raw)
    if isinstance(adapters, dict):
        adapters = [adapters]
    return adapters


def list_adapters():
    adapters = get_adapters()
    if not adapters:
        print("Nenhum adaptador encontrado.")
        return
    print(f"{'NOME':<25} {'STATUS':<14} {'MAC':<18} DESCRICAO")
    print("-" * 90)
    for adapter in adapters:
        print(
            f"{(adapter.get('Name') or ''):<25} "
            f"{(adapter.get('Status') or ''):<14} "
            f"{(adapter.get('MacAddress') or ''):<18} "
            f"{adapter.get('InterfaceDescription') or ''}"
        )


def normalize_mac(value):
    if not MAC_RE.fullmatch(value):
        raise argparse.ArgumentTypeError(
            "MAC invalido. Use 12 digitos hexadecimais, por exemplo: 02A1B2C3D4E5."
        )
    compact = re.sub(r"[:-]", "", value).upper()
    first_octet = int(compact[:2], 16)
    if first_octet & 1:
        raise argparse.ArgumentTypeError("O MAC deve ser unicast (primeiro byte par).")
    return compact


def random_mac():
    octets = [random.randrange(256) for _ in range(6)]
    octets[0] = (octets[0] | 0x02) & 0xFE  # locally administered, unicast
    return "".join(f"{octet:02X}" for octet in octets)


def adapter_registry_script(interface, operation, mac=None):
    name = ps_quote(interface)
    class_key = ps_quote(NETWORK_CLASS_KEY)
    if operation == "set":
        registry_action = (
            f"Set-ItemProperty -LiteralPath $key.PSPath -Name NetworkAddress "
            f"-Value {ps_quote(mac)} -Type String -ErrorAction Stop"
        )
    else:
        registry_action = (
            "Remove-ItemProperty -LiteralPath $key.PSPath -Name NetworkAddress "
            "-ErrorAction SilentlyContinue"
        )
    return f"""
$ErrorActionPreference = 'Stop'
$adapter = Get-NetAdapter | Where-Object {{ $_.Name -ceq {name} }} | Select-Object -First 1
if (-not $adapter) {{ throw 'Adaptador nao encontrado.' }}
$classRoot = {class_key}
$guid = $adapter.InterfaceGuid.ToString()
$key = Get-ChildItem -LiteralPath $classRoot | Where-Object {{
    (Get-ItemProperty -LiteralPath $_.PSPath -Name NetCfgInstanceId -ErrorAction SilentlyContinue).NetCfgInstanceId -eq $guid
}} | Select-Object -First 1
if (-not $key) {{ throw 'Chave de configuracao do adaptador nao encontrada.' }}
{registry_action}
Disable-NetAdapter -Name $adapter.Name -Confirm:$false -ErrorAction Stop
Start-Sleep -Milliseconds 800
Enable-NetAdapter -Name $adapter.Name -Confirm:$false -ErrorAction Stop
Start-Sleep -Seconds 2
(Get-NetAdapter -Name $adapter.Name -ErrorAction Stop).MacAddress
"""


def set_mac(interface, mac):
    current = run_powershell(adapter_registry_script(interface, "set", mac))
    print(f"MAC solicitado: {format_mac(mac)}")
    print(f"MAC informado pelo Windows apos reiniciar: {current or 'indisponivel'}")


def restore_mac(interface):
    current = run_powershell(adapter_registry_script(interface, "restore"))
    print("Configuracao personalizada removida.")
    print(f"MAC informado pelo Windows: {current or 'indisponivel'}")


def format_mac(mac):
    return "-".join(mac[i : i + 2] for i in range(0, 12, 2))


def parse_args():
    parser = argparse.ArgumentParser(
        description="Altera automaticamente o endereco MAC de um adaptador no Windows."
    )
    parser.add_argument("--list", action="store_true", help="lista os adaptadores")
    parser.add_argument("-i", "--interface", help='nome do adaptador, por exemplo "Wi-Fi"')
    parser.add_argument("-m", "--mac", type=normalize_mac, help="MAC especifico")
    parser.add_argument(
        "-t",
        "--time",
        type=int,
        metavar="SEGUNDOS",
        help="gera outro MAC repetidamente neste intervalo (minimo: 25)",
    )
    parser.add_argument("--restore", action="store_true", help="restaura o MAC do driver")
    args = parser.parse_args()
    if args.time is not None and args.time < 25:
        parser.error("--time deve ser de pelo menos 25 segundos")
    if not args.list and not args.interface:
        parser.error("informe --list ou --interface")
    if args.restore and (args.mac or args.time):
        parser.error("--restore nao pode ser combinado com --mac ou --time")
    return args


def main():
    args = parse_args()
    require_windows_and_admin()
    try:
        if args.list:
            list_adapters()
            return
        if args.restore:
            restore_mac(args.interface)
            return
        if args.time is None:
            set_mac(args.interface, args.mac or random_mac())
            return
        print("Alteracao automatica iniciada. Pressione Ctrl+C para restaurar e sair.")
        while True:
            set_mac(args.interface, random_mac())
            time.sleep(args.time)
    except KeyboardInterrupt:
        print("\nRestaurando a configuracao original...")
        restore_mac(args.interface)
    except (RuntimeError, json.JSONDecodeError) as error:
        raise SystemExit(f"Erro: {error}")


if __name__ == "__main__":
    main()
