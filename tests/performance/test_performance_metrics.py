def test_performance_metrics(page):
    page.goto("https://the-internet.herokuapp.com/login", wait_until="domcontentloaded", timeout=60000)
    performance = page.evaluate("""() => {
        return {
            domContentLoaded: performance.timing.domContentLoadedEventEnd - performance.timing.navigationStart,
            load: performance.timing.loadEventEnd - performance.timing.navigationStart
        };
    }""")
    print("Performance metrics:", performance)
    assert performance['load'] < 3000, "Page load time is too high"
