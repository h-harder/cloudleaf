# CloudLeaf — a cloud browser for KOReader

Experimental version 0.1. The Kindle runs a KOReader plugin, not Chromium.
A cloud server runs Chromium and returns grayscale PNG frames. Tap a link on
Kindle to click it remotely; swipe vertically to scroll. Hold anywhere for controls.

## What is included

- `cloudleaf.koplugin/`: installable plugin with a bundled CA certificate store.
- `server.py`, `Dockerfile`, `requirements.txt`, `render.yaml`: cloud deployment.
- `tests/`: API contract tests, with browser rendering mocked.

## Free cloud deployment (Render)

No computer at home has to stay on. You need a GitHub account and a Render account.
This package has NOT been deployed for you and has no live server URL yet.

1. Create an empty GitHub repository. Upload the contents of this folder to its
   root, so `Dockerfile` and `render.yaml` are at the top level. Do not upload any
   browser tokens or your KOReader settings. The plugin folder is safe to upload.
2. Sign in at https://dashboard.render.com/ and choose **New > Blueprint**.
3. Connect the repository. Review that the service uses **Free**, then deploy.
   `render.yaml` selects Free and generates a secret `BROWSER_TOKEN`.
4. Wait for the build. The dashboard will give you an HTTPS address such as
   `https://YOUR-SERVICE.onrender.com`. Open it on your phone and confirm it says
   "CloudLeaf server is awake".
5. Open the service's **Environment** settings and copy the generated
   `BROWSER_TOKEN`. Treat this as a password; never put it in the repository.
6. Connect the Kindle by USB. Copy the entire `cloudleaf.koplugin` directory
   into the `plugins` directory inside the Kindle's existing KOReader directory.
   A common resulting path is `/mnt/us/koreader/plugins/cloudleaf.koplugin/main.lua`.
   Use your actual KOReader location if it differs. Restart KOReader.
7. In KOReader's tools menu choose **CloudLeaf cloud browser > Set cloud address
   & token**. Enter the HTTPS address with no path, then your token.
8. Enable Kindle Wi-Fi. Choose **Open browser**, hold the page, then choose
   **Address / Search** to open a website.

If your account lacks Blueprint creation, create **New > Web Service**, connect
that same repository, choose **Docker**, and explicitly select **Free**. Add a
secret `BROWSER_TOKEN` of at least 24 random characters before starting it.

## Controls

- Tap: click that location on the remote webpage.
- Swipe up/down: scroll roughly one screen; sideways swipe: open controls.
- Hold: open the controls dialog.
- Address / Search: navigate to a URL, domain, or search query.
- Type: tap an input on the webpage first, then hold and choose Type.
  Entry inserts text at the current cursor; it does not automatically clear fields.
- Enter, Backspace, Tab: send keyboard keys to the webpage.
- Refresh: capture the page again (useful for delayed JavaScript updates).
- Reload site: reload the website itself.
- Close: leave the plugin locally; the browser session remains alive on the server.
- Clear cloud session & close: close the remote context and clear its cookies.

## Free hosting constraints

This is a free-tier experiment, not a promise of full web compatibility or speed.
Render Free currently has 512 MB RAM and 0.1 CPU. Chromium and complex pages can
exceed those limits. One tab reduces resource usage but does not guarantee the
browser fits. If the host runs out of memory, the service can restart. Refresh or
reopen it; if a particular site repeatedly fails, this tier cannot handle it.

Render sleeps after 15 minutes without inbound traffic and takes about a minute
to wake. If the Kindle reports a connection error, visit the server address from
your phone, wait for it to wake, then retry. This plugin does not keep the server
awake artificially. Included usage quotas and provider terms still apply.

Cookies, history, and logins are memory-only and disappear on restart/sleep or
session clearing. This version has one shared browser session per server. Use a
separate deployment per user. Anyone with your token controls that session.

E-ink limits animation and scrolling, regardless of server speed. There is no
video/audio streaming, downloads, tab management, automatic live updates, popup
support, file uploads, WebAuthn/passkeys, or reader/text selection mode in v0.1.
JavaScript runs on the server; some sites may refuse cloud browser IP addresses
or present CAPTCHA. The current plugin uses synchronous requests, so KOReader
can temporarily stop responding during a slow request (up to about 45 seconds).
This remains a prototype until tested on your specific Kindle/KOReader build.

## Security and privacy

Use HTTPS. The plugin checks the certificate chain using its bundled CA store;
full platform-equivalent TLS hostname validation has not been verified across
KOReader/LuaSec builds. Do not use this prototype for sensitive accounts.
The cloud provider runs the browser and can have access to browser memory.
The token is stored in KOReader's local settings; text input is masked in the
plugin dialog but sent to the cloud browser. No access log, saved screenshots,
website URL logs, or persistent browser profile are intentionally created.

Requests reject private IP addresses, non-HTTP URLs, and nonstandard ports;
service workers are blocked. This is a request-level check, not a network
sandbox against DNS rebinding or a compromised browser. Keep it single-user,
protect the token, and do not expose this as a public shared browsing service.
The Docker Chromium process runs without its normal sandbox (Playwright's
default), inside the provider's container. It is not a hardened browsing service.

## Validation performed

- Lua source compiles in a Lua runtime.
- Six server API checks passed using a mocked page: authentication, validation,
  PNG grayscale response, tap coordinates, private navigation rejection,
  and session closure.
- Full Chromium execution, Docker deployment, free-tier memory usage, and real
  Kindle integration were NOT tested. The local Chromium download failed.

## Provider references

https://render.com/docs/free
https://render.com/docs/compute-plans
https://render.com/docs/docker
https://github.com/render-examples/playwright-mcp-render

The host's own browser example recommends 2 GB and warns about 512 MB OOM.
These limits were checked on October 13, 2026; verify in the deployment dashboard.
