# Masker for Windows

[English](#english) · [Español](#español) · [Português](#português) · [Français](#français)

## English

Masker is a Windows 10/11 MAC address changer with **automatic and manual modes**, available in this public source repository.

Download [Masker.exe](https://github.com/luizgustavocastro-create/Masker.exe./raw/refs/heads/main/Masker.exe), run it as administrator, and select your network adapter. Choose **Automatic at startup** or **Manual**, then click **Save mode**. Automatic mode requests a new random MAC each time Windows starts. Manual mode disables the startup task; use **Generate new** and **Activate masking** whenever you want. You can switch modes at any time. **Restore original** removes the custom address; it does not disable automatic mode.

The active MAC can be observed on the local network by its infrastructure and, on Wi-Fi, by nearby radio observers. Websites normally do not receive your MAC through routed Internet traffic. Software running on your computer may read adapter information. Randomization does not hide your IP, accounts, cookies, or browser fingerprint and cannot guarantee anonymity.

Driver support is required; some adapters reject changes. Changing the MAC briefly disconnects the adapter. Startup means a Windows boot, not opening the lid or resuming sleep; there is no guarantee it runs before the first network connection. Manual is the default on a fresh installation and keeps the current MAC when selected. All opinions are welcome—please share feedback and feel free to request new tools through [Issues](https://github.com/luizgustavocastro-create/Masker.exe./issues).

## Español

Masker cambia la dirección MAC en Windows 10/11 y ofrece **modo automático y manual** en este repositorio público de código fuente.

Descarga [Masker.exe](https://github.com/luizgustavocastro-create/Masker.exe./raw/refs/heads/main/Masker.exe), ejecútalo como administrador y selecciona el adaptador. Elige **Automatic at startup** o **Manual** y pulsa **Save mode**. El modo automático solicita una MAC aleatoria en cada inicio de Windows. El manual desactiva la tarea de inicio; usa **Generate new** y **Activate masking** cuando quieras. Puedes cambiar de modo en cualquier momento. **Restore original** elimina la dirección personalizada, pero no desactiva el modo automático.

La infraestructura de la red local puede observar la MAC activa; en Wi-Fi también pueden hacerlo observadores cercanos de la señal. Los sitios web normalmente no reciben tu MAC a través de Internet enrutado. El software local puede consultar información del adaptador. Cambiar la MAC no oculta la IP, las cuentas, las cookies ni la huella del navegador, y no garantiza anonimato.

Depende del controlador: algunos adaptadores rechazan el cambio. La conexión se interrumpe brevemente. El inicio es el arranque de Windows, no abrir la tapa ni salir de suspensión; puede haber conexión antes del cambio. Una instalación nueva usa el modo manual, que conserva la MAC actual. Todas las opiniones son bienvenidas: comparte comentarios y solicita nuevas herramientas en [Issues](https://github.com/luizgustavocastro-create/Masker.exe./issues).

## Português

O Masker altera o endereço MAC no Windows 10/11 e oferece **modo automático e manual** neste repositório público de código-fonte.

Baixe o [Masker.exe](https://github.com/luizgustavocastro-create/Masker.exe./raw/refs/heads/main/Masker.exe), execute como administrador e selecione o adaptador. Escolha **Automatic at startup** ou **Manual** e clique em **Save mode**. O automático solicita um MAC aleatório toda vez que o Windows inicia. O manual desativa a tarefa de inicialização; use **Generate new** e **Activate masking** quando quiser. Você pode alternar os modos a qualquer momento. **Restore original** remove o endereço personalizado, mas não desativa o modo automático.

A infraestrutura da rede local pode observar o MAC ativo; no Wi-Fi, observadores próximos do sinal também podem vê-lo. Sites normalmente não recebem seu MAC pelo tráfego roteado da Internet. Programas locais podem consultar informações do adaptador. Alterar o MAC não oculta IP, contas, cookies ou a impressão digital do navegador e não garante anonimato.

É necessário suporte do driver: alguns adaptadores rejeitam a alteração. A conexão cai brevemente durante a troca. Inicialização significa iniciar o Windows, não abrir a tampa ou sair da suspensão; a rede pode conectar antes da troca. Uma instalação nova começa em manual, que mantém o MAC atual. Qualquer opinião é bem-vinda: compartilhe comentários e fique à vontade para pedir novas ferramentas em [Issues](https://github.com/luizgustavocastro-create/Masker.exe./issues).

## Français

Masker modifie l'adresse MAC sous Windows 10/11 et propose un **mode automatique et manuel** dans ce dépôt public de code source.

Téléchargez [Masker.exe](https://github.com/luizgustavocastro-create/Masker.exe./raw/refs/heads/main/Masker.exe), exécutez-le en tant qu'administrateur et sélectionnez l'adaptateur. Choisissez **Automatic at startup** ou **Manual**, puis **Save mode**. Le mode automatique demande une nouvelle MAC aléatoire à chaque démarrage de Windows. Le mode manuel désactive la tâche de démarrage ; utilisez **Generate new** et **Activate masking** quand vous le souhaitez. Vous pouvez changer de mode à tout moment. **Restore original** supprime l'adresse personnalisée sans désactiver le mode automatique.

L'infrastructure du réseau local peut observer la MAC active ; en Wi-Fi, des observateurs radio à proximité le peuvent aussi. Les sites web ne reçoivent normalement pas votre MAC via le trafic Internet routé. Les logiciels locaux peuvent consulter les informations de l'adaptateur. Changer la MAC ne masque ni l'IP, ni les comptes, ni les cookies, ni l'empreinte du navigateur et ne garantit pas l'anonymat.

Le pilote doit accepter la modification. La connexion est brièvement interrompue. Le démarrage désigne celui de Windows, pas l'ouverture du capot ou la sortie de veille ; une connexion peut précéder le changement. Une nouvelle installation utilise le mode manuel, qui conserve la MAC actuelle. Tous les avis sont bienvenus : partagez vos commentaires et demandez de nouveaux outils dans les [Issues](https://github.com/luizgustavocastro-create/Masker.exe./issues).

## Technical notes / Notas técnicas / Notes techniques

- Windows 10/11, administrator privileges, compatible network driver.
- Automatic mode copies the executable into the protected `%ProgramFiles%\Masker` folder and creates `Masker Randomize MAC at Startup`, a Windows Scheduled Task running as SYSTEM at boot. Save automatic mode again after updating the executable to update this copy.
- The setting applies to the selected adapter. Changing the adapter for automatic mode requires **Save mode** again.
- Manual mode removes the startup task and saves a disabled flag. It does not revert the current MAC. Select manual before removing the application.
- Local state is stored using AES-256-GCM in `%ProgramData%\Masker`. This protects local data, not the MAC transmitted over the network, and does not protect against a local administrator.
- A requested MAC is checked against the address reported by Windows; a mismatch is reported as an error.
- The interface labels are in English, with some messages in Portuguese. This README provides instructions in all four languages.

## Build and tests

```powershell
python -m pip install -r requirements-build.txt
python -m unittest discover -s tests -v
python -m PyInstaller --clean --noconfirm Masker.spec
```

Output: `dist\Masker.exe`. Tests mock system operations and do not change the host MAC or install a startup task.

## References

- [Microsoft: Wi-Fi connections and random hardware addresses](https://support.microsoft.com/en-us/windows/experience/connectivity-networking/connect-to-a-wi-fi-network-in-windows)
- [IETF RFC 9724: State of Affairs for Randomized and Changing MAC Addresses](https://www.rfc-editor.org/rfc/rfc9724.html)
- [IETF RFC 9797: MAC randomization context, network impacts, and use cases](https://www.rfc-editor.org/rfc/rfc9797.html)

License: [CC0 1.0 Universal](LICENSE).
