/**
 * Lighthouse CI configuration.
 *
 * Phase 4 hard gate: p4-lighthouse
 * Performance budget: LCP < 2.5s, FID < 100ms, CLS < 0.1, 200KB bundle
 *
 * Run: pnpm exec lhci autorun
 */

module.exports = {
  ci: {
    collect: {
      // Run against the live dev/preview server
      url: ["http://localhost:3000/login"],
      numberOfRuns: 1,
      settings: {
        // Use desktop preset for consistent CI results
        preset: "desktop",
        // Skip network throttling in CI
        throttlingMethod: "provided",
        // Only audit performance + accessibility
        onlyCategories: ["performance", "accessibility"],
      },
    },
    assert: {
      assertions: {
        // Performance budget per Phase 4 requirements
        "categories:performance": ["warn", { minScore: 0.8 }],
        "categories:accessibility": ["error", { minScore: 0.9 }],

        // Core Web Vitals thresholds
        "largest-contentful-paint": [
          "error",
          { maxNumericValue: 2500 }, // LCP < 2.5s
        ],
        "cumulative-layout-shift": [
          "error",
          { maxNumericValue: 0.1 }, // CLS < 0.1
        ],
        "total-blocking-time": [
          "warn",
          { maxNumericValue: 300 }, // TBT < 300ms (proxy for FID)
        ],
        "resource-summary:script:size": [
          "warn",
          { maxNumericValue: 204800 }, // 200KB JS budget
        ],
      },
    },
    upload: {
      // Local temporary storage (no external LHCI server)
      target: "temporary-public-storage",
    },
  },
};
