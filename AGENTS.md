# Town Heritage review prototype

This is deliberately unlisted and uses a personal Europeana key for project review. Keep it out of the CoolCode public catalogue, main homepage, sitemap, scheduled collectors and watchdog. The owner explicitly wants the standard aggregate visit statistics: register its ID as an unlisted measured tool in the hub and Worker and include the shared counter. Measurement does not promote the prototype. Noindex is deliberate. Do not claim it is private; the review URL is public but unlisted.

Keep app source in web/, collector/build code in scripts/, configuration in config/, tests in tests/. Never publish raw API responses or credentials. The first main push collects if no sanitized snapshot exists; later pushes reuse it. Manual workflow_dispatch refreshes the capture. PRs only check. A successful real keyed capture is required for deployment. No synthetic data in published output.

Render source metadata with textContent, validate URLs, preserve per-item licence attribution and source links. Do not equate keyword matches or provider countries with depicted object locations. Saved collections must preserve earlier capture metadata.

Run Node tests, Python unittest, the offline build and Chromium smoke checks. Before eventual production promotion, follow the normal CoolCode lifecycle after the user authorizes promotion and has a project key.
