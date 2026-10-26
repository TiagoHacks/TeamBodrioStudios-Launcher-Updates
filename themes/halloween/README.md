# Halloween RC8 — versión en preparación

Estado: **fuente preparada, actualización automática pendiente de compilar y publicar**.

Versión prevista del launcher: `1.0.0-rc.8`.

El nuevo tema se elige dentro de **Temas → Halloween**. Mantiene los temas Nocturno, Oscuro y Claro; incluye paleta naranja calabaza, violeta, negro, luna y murciélagos.

El paquete completo con el código y los scripts de publicación está en el ZIP `TeamBodrioStudios_Launcher_v1.0.0_RC8_Halloween.zip` entregado en la conversación.

## Publicación segura

1. En Windows, desde la raíz de RC8 ejecutar `powershell -ExecutionPolicy Bypass -File ".\Publicar_GitHub.ps1"`.
2. El script debe crear un GitHub Release con `TeamBodrioLauncher-1.0.0-rc.8-win-x64.zip`, verificar la descarga y su SHA-256.
3. **Solo después** publicará `stable/launcher-update.json`.

No publicar el manifiesto con una URL ficticia ni señalar al ZIP del proyecto fuente. El ZIP del release debe incluir `TeamBodrioLauncher.exe` y `Updater/TeamBodrioUpdater.exe`.

## FancyMenu

Pendiente de prueba local con Fabric 1.21.1, FancyMenu, Konkrete, Melody y Fabric API. El diseño de FancyMenu se exportará desde `config/fancymenu/` de la instancia Murder Mystery y luego se añadirá a `modos/manifest.json` con hashes. Esta publicación **no modifica aún el catálogo de modos**.

La versión RC7 continúa siendo la versión distribuida hasta que se publique y pruebe RC8.
