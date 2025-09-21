from playwright.sync_api import sync_playwright

def take_shot(page, path):
    page.wait_for_timeout(800)  # allow highlight/theme to settle
    page.screenshot(path=path, full_page=True)

def capture(theme, suffix):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # Force theme
        page.emulate_media(color_scheme=theme)

        # --- Write ---
        page.goto("http://localhost:8000/")
        take_shot(page, f"docs/screenshots/write-{suffix}.png")

        # --- Preview Python ---
        page.fill("#content", "print('Hello EncryptBin!')")
        page.click(".tab[data-tab='preview']")
        take_shot(page, f"docs/screenshots/preview-python-{suffix}.png")

        # --- Preview JSON ---
        page.click(".tab[data-tab='write']")
        page.fill("#content", '{"hello": "world"}')
        page.click(".tab[data-tab='preview']")
        take_shot(page, f"docs/screenshots/preview-json-{suffix}.png")

        # --- View page (Python paste) ---
        page.click(".tab[data-tab='write']")
        page.fill("#content", "def add(a, b):\n    return a+b")
        page.click("button.btn.primary")
        page.wait_for_load_state("networkidle")
        take_shot(page, f"docs/screenshots/view-python-{suffix}.png")

        browser.close()

if __name__ == "__main__":
    capture("dark", "dark")
    capture("light", "light")

