def test_performance_metrics(page, browser_name):
    page.goto("https://the-internet.herokuapp.com/login", wait_until="domcontentloaded", timeout=60000)

    performance = page.evaluate("""() => {
        const navEntries = performance.getEntriesByType('navigation');
        const paintEntries = performance.getEntriesByType('paint');
        const timing = performance.timing;

        let navigation = null;
        if (navEntries.length > 0) {
            navigation = navEntries[0];
        }

        // Get paint metrics
        let firstPaint = null;
        let firstContentfulPaint = null;
        for (const p of paintEntries) {
            if (p.name === 'first-paint') {
                firstPaint = p.startTime;
            }
            if (p.name === 'first-contentful-paint') {
                firstContentfulPaint = p.startTime;
            }
        }

        // Approximate Time To Interactive (not perfect)
        // Using domInteractive to loadEventStart difference as rough estimate
        let timeToInteractive = null;
        if (navigation) {
            timeToInteractive = navigation.domInteractive - (navigation.startTime || 0);
        } else {
            timeToInteractive = timing.domInteractive - timing.navigationStart;
        }

        return {
            domContentLoaded: navigation ? navigation.domContentLoadedEventEnd : (timing.domContentLoadedEventEnd - timing.navigationStart),
            load: navigation ? navigation.loadEventEnd : (timing.loadEventEnd - timing.navigationStart),
            firstPaint,
            firstContentfulPaint,
            timeToInteractive,
            responseStart: navigation ? navigation.responseStart : (timing.responseStart - timing.navigationStart)
        };
    }""")

    print(f"Performance metrics for {browser_name}:")
    print(f"  DOM Content Loaded: {performance['domContentLoaded']:.2f} ms")
    print(f"  Load Event: {performance['load']:.2f} ms")
    print(f"  First Paint: {performance['firstPaint']:.2f} ms" if performance['firstPaint'] is not None else "  First Paint: N/A")
    print(f"  First Contentful Paint: {performance['firstContentfulPaint']:.2f} ms" if performance['firstContentfulPaint'] is not None else "  First Contentful Paint: N/A")
    print(f"  Time to Interactive (approx): {performance['timeToInteractive']:.2f} ms")
    print(f"  Response Start: {performance['responseStart']:.2f} ms")

    # Assert thresholds - adjust as needed
    assert performance['load'] < 3000, "Page load time is too high"
    assert performance['timeToInteractive'] < 4000, "Time to Interactive is too high"

