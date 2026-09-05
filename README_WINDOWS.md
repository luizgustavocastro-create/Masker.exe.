# Masker para Windows

Consulte o [README em inglês, espanhol, português e francês](README.md) para download, modos automático/manual e limites de privacidade.

Na interface, selecione o adaptador, escolha **Automatic at startup** ou **Manual** e clique em **Save mode**. O modo automático solicita um MAC aleatório em cada inicialização do Windows; o manual permite trocar quando quiser. Restaurar o MAC não desativa o modo automático.

A linha de comando continua disponível:

```powershell
python .\amc_windows.py --list
python .\amc_windows.py --interface "Wi-Fi"
python .\amc_windows.py --interface "Ethernet" --mac 02A1B2C3D4E5
python .\amc_windows.py --interface "Wi-Fi" --restore
```

Execute como administrador. A troca depende do driver e interrompe brevemente a conexão.
