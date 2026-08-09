# Setup de Google Cloud para la integración de Calendar

Pasos manuales una sola vez para obtener `GOOGLE_CLIENT_ID` y
`GOOGLE_CLIENT_SECRET`. Requiere una cuenta de Google.

1. Entrar a [Google Cloud Console](https://console.cloud.google.com/) y crear
   un proyecto nuevo. Nombre sugerido: `wdigd`.

2. Habilitar la API: **APIs & Services → Library**, buscar "Google Calendar
   API", clic en **Enable**.

3. Configurar la pantalla de consentimiento: **APIs & Services → OAuth consent
   screen**.
   - User type: **External** (permite loguearse con cualquier cuenta de
     Google, no solo del workspace).
   - App name: `wdigd`. Support email: tu email.
   - Scopes: agregar `.../auth/calendar.readonly`, `openid`, `email`.
   - Test users: agregar los emails que van a usar la app (hasta 100).
   - Publishing status: dejar en **Testing**. Aparece un banner "app no
     verificada" al conectar por primera vez — es esperable, se pasa con dos
     clics en "Advanced → Continue".

4. Crear las credenciales: **APIs & Services → Credentials → Create
   credentials → OAuth client ID**.
   - Application type: **Web application**.
   - Name: `wdigd`.
   - Authorized redirect URIs:
     - `http://localhost:8000/calendar/callback` (dev)
     - `https://<tu-dominio-en-railway>/calendar/callback` (prod)
   - Guardar. Copiar el **Client ID** y el **Client secret**.

5. Configurar las variables de entorno.
   - Local: exportar antes de `uvicorn`:
     ```bash
     export GOOGLE_CLIENT_ID="…"
     export GOOGLE_CLIENT_SECRET="…"
     ```
   - Railway: agregar las mismas variables en el servicio de la app. Fijar
     también `GOOGLE_REDIRECT_URI=https://<dominio>/calendar/callback` para
     que el URI que arma la app coincida exacto con el que registraste.

Sin `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` la feature queda deshabilitada
silenciosamente: la sección "Google Calendar" en `/settings` no aparece.

## Rotación y desconexiones

- Revocar todos los accesos: **APIs & Services → Credentials**, borrar el
  OAuth client. Los usuarios conectados ven "reconectar" la próxima vez.
- Un usuario puede revocar el acceso desde su cuenta de Google
  ([myaccount.google.com/permissions](https://myaccount.google.com/permissions))
  sin tocar nuestro código. La app detecta la revocación cuando falla el
  siguiente refresh y muestra "reconectar" en `/settings`.
- Rotar `SECRET_KEY` invalida los refresh tokens guardados (están encriptados
  con una clave derivada de ella). Los usuarios tienen que reconectar. Ya
  pasaba con las sesiones; es consistente.
