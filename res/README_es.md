<img align="left" width="80" height="80" src="https://raw.githubusercontent.com/alexal1/Insomniac/master/res/icon.jpg" alt="Insomniac">

# Insomniac
![GitHub tag (latest by date)](https://img.shields.io/github/v/tag/alexal1/Insomniac?label=latest%20version)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat)


[inglés](https://github.com/alexal1/Insomniac/blob/master/README.md) | [portugués](https://github.com/alexal1/Insomniac/blob/master/res/README_pt_BR.md)

Dale like y sigue automáticamente en tu teléfono / tableta Android. No se requiere root: funciona con UI Automator, que es una estructura de prueba oficial UI de Android.

<img src="https://raw.githubusercontent.com/alexal1/Insomniac/master/res/demo.gif">

### Cómo instalar
1. Clone el proyecto: `git clone https://github.com/alexal1/Insomniac.git`
2. Instalar [uiautomator](https://github.com/xiaocong/uiautomator) y [colorama](https://pypi.org/project/colorama/): `pip3 install uiautomator colorama`
3. Download y unzip [Android platform tools](https://developer.android.com/studio/releases/platform-tools), moverlos a un directorio donde no los eliminará accidentalmente, ejemplo:
```
mkdir -p ~/Library/Android/sdk
mv <ruta-para-downloads>/platform-tools/ ~/Library/Android/sdk
```
4. [Agregue la ruta de platform-tools a las variables de entorno del sistema](https://github.com/alexal1/Insomniac/wiki/Agregue-la-ruta-de-platform-tools-a-las-variables-de-entorno-del-sistema-es). Si lo hace correctamente, el comando en la terminal (Símbolo del sistema) `adb devices` imprimirá `List of devices attached`

### Cómo instalar en Raspberry Pi OS
1. Update apt-get: `sudo apt-get update`
2. Instalar ADB y Fastboot: `sudo apt-get install -y android-tools-adb android-tools-fastboot`
3. Clone el proyecto: `git clone https://github.com/alexal1/Insomniac.git`
4. Instalar [uiautomator](https://github.com/xiaocong/uiautomator) y [colorama](https://pypi.org/project/colorama/): `pip3 install uiautomator colorama`

### Comenzando
1. Conecte el dispositivo Android a su computadora con un cable USB
2. Habilite [Opciones para desarrolladores](https://developer.android.com/studio/debug/dev-options?hl=es) en el dispositivo
>En Android 4.1 y versiones anteriores, la pantalla Opciones para desarrolladores está disponible de forma predeterminada. En Android 4.2 y versiones posteriores, debes habilitarla. Si quieres habilitar las Opciones para desarrolladores, presiona la opción Número de compilación 7 veces. Puedes encontrar esta opción en una de las siguientes ubicaciones, según tu versión de Android:
>
> Android 9 (API nivel 28) y versiones posteriores: Configuración > Acerca del dispositivo > Número de compilación
>
> Android 8.0.0 (API nivel 26) y Android 8.1.0 (API nivel 26): Configuración > Sistema > Acerca del dispositivo > Número de compilación
>
> Android 7.1 (API nivel 25) y versiones anteriores: Configuración > Acerca del dispositivo > Número de compilación
3. Active **Depuración de USB** (e **Instalación de aplicaciones a través de USB** si existe tal opción) en la pantalla de opciones para desarrolladores.
4. El dispositivo le pedirá que permita la conexión de la computadora. Presione "Conectar"
5. Escriba `adb devices` en terminal. Mostrará los dispositivos conectados. Debe haber exactamente un dispositivo. Luego ejecute el script (funciona en Python 3):
```
cd <ruta-del-proyecto>/Insomniac
python3 insomniac.py --interact <username1> <username2> ...
```
Asegúrese de que la pantalla esté encendida y que el dispositivo esté desbloqueado. No tiene que abrir la aplicación de Instagram, la secuencia de comandos la abre y se cierra cuando está terminada. Solo asegúrate de que la aplicación de Instagram esté instalada. Si todo está bien, el script abrirá los seguidores de cada blogger y les gustará sus publicaciones.

### Uso
Lista completa de argumentos de línea de comando:
```
  --interact username1 [username2 ...]
                        lista de usernames con cuyos seguidores desea
                        interactuar
  --likes-count 2       número de likes para cada usuario interactuado, 2 por defecto
  --total-likes-limit 300
                        limit on total amount of likes during the session, 300
                        por defecto
  --interactions-count 70
                        cantidad de interacciones por cada blogger, 70 por
                        defecto. Only successful interactions count
  --repeat 180          repita la misma sesión nuevamente después de N minutos
                        completos, deshabilitada por defecto
  --follow-percentage 50
                        segue el porcentaje dado de usuarios, 0 por
                        defecto
  --follow-limit 50     límite en la cantidad de seguidores durante la interacción con
                        los seguidores de cada usuario, deshabilitada por defecto
  --unfollow 100        deja de seguir el numero maximo de usuarios. Solo usuario
                        que fue seguido por el script será dejado de seguir. El orden
                        es del más antiguo al más nuevo.
  --unfollow-non-followers 100
                        deja de seguir el numero maximo de usuarios, que no
                        te siguen de vuelta. Solo usuario que fue seguido por el script
                        será dejado de seguir. El orden es del más antiguo al
                        más nuevo.
  --device 2443de990e017ece
                        identificador de dispositivo. Debe usarse solo cuando hay varios
                        dispositivos conectados a la vez
```

### FAQ
- ¿Puedo evitar que mi teléfono se quede dormido? Si. Configuración -> Opciones para desarrolladores -> Stay awake.
- [¿Cómo conectar un teléfono Android a través de WiFi?](https://www.patreon.com/posts/connect-android-38655552)
- [¿Cómo ejecutar en 2 o más dispositivos a la vez?](https://www.patreon.com/posts/38683736)
- [Script crash con **OSError: RPC server not started!** o **ReadTimeoutError**](https://www.patreon.com/posts/problems-with-to-38702683)
- [Las cuentas privadas siempre se ignoran. ¿Cómo seguirlas también?](https://www.patreon.com/posts/enable-private-39097751) **(Por favor, únete a Patreon - Plan $ 10)**
- [Filtrar por seguidores / número de seguidores, ratio, business / no business](https://www.patreon.com/posts/38826184) **(Por favor, únete a Patreon - Plan $ 10)**

### Análisis
También hay una herramienta de análisis para este bot. Es un script que crea un informe en formato PDF. El informe contiene gráficos de crecimiento de seguidores de la cuenta para diferentes períodos. Las cantidades de acciones de likes, seguir y dejar de seguir están en el mismo eje para determinar la efectividad del bot. El informe también contiene estadísticas de la duración de las sesiones para las diferentes configuraciones que ha utilizado. Todos los datos se toman del archivo `sessions.json` que se genera durante la ejecución del bot.
<img src="https://raw.githubusercontent.com/alexal1/Insomniac/master/res/analytics_sample.png">

Para obtener acceso a la herramienta de análisis, debe [unirte a Patreon - Plan $10](https://www.patreon.com/insomniac_bot).

### Recursos en progreso
- [x] Siga el porcentaje dado de usuarios interaccionado con `--follow-percentage 50`
- [x] Deja de seguir el porcentaje dado de usuarios (solo aquellos que fueron seguidos por el script) con `--unfollow 100`
- [x] Deja de seguir el porcentaje dado de usuarios no seguidores (solo aquellos que fueron seguidos por el script) con `--unfollow-non-followers 100`
- [ ] Agregar acciones aleatorias para comportarse más como un humano (ver su propio feed, stories, etc.)
- [ ] Soporte para intervalos de likes y cuenta de interacciones `--likes-count 2-3`
- [ ] Interacción por hashtags
- [ ] Comentar durante la interacción

### ¿Por qué Insomniac?
Ya existe [InstaPy](https://github.com/timgrossmann/InstaPy), que funciona en la versión web de Instagram. Desafortunadamente, el sistema de detección de bots de Instagram se ha vuelto muy sospechoso a las acciones del navegador. Ahora InstaPy y scripts similares funcionan como máximo una hora, luego Instagram bloquea la posibilidad de realizar cualquier acción, y si continúa usando InstaPy, puede bloquear su cuenta.

Es por eso que surgió la necesidad de una solución para dispositivos móviles. Instagram no puede distinguir un bot de un humano cuando se trata de tu teléfono. Sin embargo, incluso un ser humano puede alcanzar límites cuando usa la aplicación, así que no deje de tener cuidado. Establezca siempre `--total-likes-limit` en 300 o menos. También es mejor usar `--repeat` para actuar periódicamente durante 2-3 horas, porque Instagram realiza un seguimiento de cuánto tiempo funciona la aplicación.

### Comunidad
Tenemos [Discord server](https://discord.gg/59pUYCw) que es el lugar más conveniente para discutir todos los errores, nuevas funciones, límites de Instagram, etc. Si no está familiarizado con Discord, también puede unirse a nuestro [Telegram chat](https://t.me/insomniac_chat). Y finalmente, toda la información útil se publica en nuestro [Patreon page](https://www.patreon.com/insomniac_bot). La mayoría de las publicaciones están disponibles para todos, pero algunas requieren unirse al Plan de $ 10: Esta es nuestra manera de seguir evolucionando y mejorando el bot.


<a href="https://t.me/insomniac_chat">	<p>
  <img hspace="3" alt="Telegram Group" src="https://raw.githubusercontent.com/alexal1/Insomniac/master/res/telegram.png" width=214/>	  <a href="https://discord.gg/59pUYCw">
</a>	    <img hspace="3" alt="Discord Server" src="https://raw.githubusercontent.com/alexal1/Insomniac/master/res/discord.png" height=84/>
  </a>
  <a href="https://t.me/insomniac_chat">
    <img hspace="3" alt="Telegram Chat" src="https://raw.githubusercontent.com/alexal1/Insomniac/master/res/telegram.png" height=84/>
  </a>
  <a href="https://www.patreon.com/insomniac_bot">
    <img hspace="3" alt="Patreon Page" src="https://raw.githubusercontent.com/alexal1/Insomniac/master/res/patreon.png" height=84/>
  </a>
</p>
