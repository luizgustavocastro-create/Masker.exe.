# Masker para Windows

Esta versao funciona no Windows 10/11 e nao depende do `macchanger` do Linux.
Ela altera o valor `NetworkAddress` do adaptador e reinicia o dispositivo de rede.

## Requisitos

- Python 3.9 ou mais recente
- PowerShell 5.1 ou mais recente
- Terminal aberto como **Administrador**

Alguns drivers, principalmente de Wi-Fi, nao permitem trocar o endereco MAC.
A rede sera interrompida brevemente sempre que o adaptador for reiniciado.

## Uso

### Interface grafica (troca manual)

Abra o atalho **Masker** na Area de Trabalho ou execute `amc_windows_gui.pyw`.
Confirme a solicitacao de administrador,
escolha o adaptador e clique em **Trocar MAC** somente quando quiser aplicar a mudanca.
Nao existe temporizador nessa interface.

### Linha de comando

Liste os adaptadores:

```powershell
python .\amc_windows.py --list
```

Defina um MAC aleatorio uma vez:

```powershell
python .\amc_windows.py --interface "Wi-Fi"
```

Defina um MAC especifico:

```powershell
python .\amc_windows.py --interface "Ethernet" --mac 02A1B2C3D4E5
```

Troque automaticamente a cada 60 segundos:

```powershell
python .\amc_windows.py --interface "Wi-Fi" --time 60
```

Restaure o endereco definido pelo fabricante/driver:

```powershell
python .\amc_windows.py --interface "Wi-Fi" --restore
```

No modo automatico, `Ctrl+C` remove a configuracao personalizada antes de sair.

## Protecao na inicializacao

O executavel pode instalar uma tarefa elevada que aplica um novo MAC aleatorio ao
adaptador `Wi-Fi` em cada inicializacao, antes do uso normal da VPN. O estado local
da operacao fica protegido com AES-256-GCM em `C:\ProgramData\Masker`.

Essa criptografia protege apenas os dados locais do Masker. Um endereco MAC nao pode
ser criptografado durante a comunicacao Wi-Fi porque precisa permanecer legivel no
protocolo da rede local.
