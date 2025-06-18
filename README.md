# TestPilot-AI

An advanced Python Playwright automation framework featuring:

- ✅ UI & API tests
- 🔁 Retry logic for flaky tests
- 📊 HTML and Allure reporting
- 🔔 Slack notifications via GitHub Actions
- 🌐 Cross-browser CI
- 📂 Self-healing locators and modular design
- 🖼 Visual comparison testing
- ⚡ Performance testing
- 🤖 ChatGPT-assisted test script generation

## 🚀 How to Use

1. Install dependencies:
    ```bash
    pip install -r requirements.txt
    playwright install
    ```

2. Run tests with:
    ```bash
    pytest --browser chromium
    ```

3. View reports:
    ```bash
    chmod +x run_allure.sh
    ./run_allure.sh
    ```

4. GitHub Actions handles CI across Chromium, Firefox, and WebKit.
