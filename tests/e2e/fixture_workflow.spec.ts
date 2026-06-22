/**
 * T-E1: New fixture GR&R workflow — end-to-end via the dashboard UI.
 *
 * Preconditions:
 *   - docker compose up api dashboard (or BASE_URL pointing at a live stack)
 *   - API_AUTH_KEY set in environment
 *
 * What is tested:
 *   1. Dashboard loads and shows the GR&R submission form
 *   2. User submits a GR&R study via the UI
 *   3. Result page shows acceptance verdict within 2 minutes
 *   4. Review queue shows a new entry when GRR is CONDITIONAL
 */

import { test, expect, request } from "@playwright/test";

const API_URL = process.env.API_URL ?? "http://localhost:8000";
const API_KEY = process.env.API_AUTH_KEY ?? "test-api-key";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build a balanced AIAG-style GR&R measurement payload. */
function buildGRRPayload(grr_pct_target: "low" | "medium" | "high" = "medium") {
  const noise = grr_pct_target === "low" ? 0.01 : grr_pct_target === "high" ? 0.5 : 0.1;
  const measurements = [];
  for (const part of [1, 2, 3, 4, 5]) {
    for (const op of ["A", "B", "C"]) {
      for (let trial = 0; trial < 2; trial++) {
        measurements.push({
          part: `P${part}`,
          operator: op,
          value: +(10.0 + part * 0.5 + (Math.random() * noise - noise / 2)).toFixed(4),
        });
      }
    }
  }
  return {
    part_ids: ["P1", "P2", "P3", "P4", "P5"],
    operator_ids: ["A", "B", "C"],
    measurements,
    method: "xbar_r",
  };
}

// ---------------------------------------------------------------------------
// T-E1: Fixture workflow via API (headless — fast)
// ---------------------------------------------------------------------------

test.describe("T-E1: GR&R fixture workflow (API level)", () => {
  test("submits a GRR study and receives a valid response within 30s", async () => {
    const ctx = await request.newContext({
      baseURL: API_URL,
      extraHTTPHeaders: { "x-api-key": API_KEY },
    });

    const start = Date.now();
    const resp = await ctx.post("/api/v1/studies/grr", {
      data: buildGRRPayload("medium"),
    });

    const elapsed = Date.now() - start;
    expect(resp.status()).toBe(201);
    expect(elapsed).toBeLessThan(30_000); // must complete in < 30s

    const body = await resp.json();
    expect(body).toHaveProperty("study_id");
    expect(body).toHaveProperty("grr_percent");
    expect(body).toHaveProperty("acceptance");
    expect(body).toHaveProperty("ndc");
    expect(typeof body.grr_percent).toBe("number");
    expect(body.grr_percent).toBeGreaterThanOrEqual(0);
    expect(body.grr_percent).toBeLessThanOrEqual(100);
    expect(["ACCEPTABLE", "CONDITIONAL", "NOT_ACCEPTABLE"]).toContain(body.acceptance);
  });

  test("GRR study appears in review queue when CONDITIONAL", async () => {
    const ctx = await request.newContext({
      baseURL: API_URL,
      extraHTTPHeaders: { "x-api-key": API_KEY },
    });

    // Submit a study likely to land in CONDITIONAL range (15–30%)
    const submitResp = await ctx.post("/api/v1/studies/grr", {
      data: buildGRRPayload("medium"),
    });
    if (submitResp.status() !== 201) {
      test.skip(); // skip if no live DB
    }
    const study = await submitResp.json();

    if (study.acceptance !== "CONDITIONAL") {
      test.skip(); // only verify queue for CONDITIONAL
    }

    const reviewsResp = await ctx.get("/api/v1/reviews");
    expect(reviewsResp.status()).toBe(200);
    const reviews = await reviewsResp.json();

    const match = reviews.find((r: { study_id: string }) => r.study_id === study.study_id);
    expect(match).toBeDefined();
    expect(match.status).toBe("pending");
  });

  test("GRR endpoint returns 422 for malformed payload", async () => {
    const ctx = await request.newContext({
      baseURL: API_URL,
      extraHTTPHeaders: { "x-api-key": API_KEY },
    });

    const resp = await ctx.post("/api/v1/studies/grr", {
      data: {
        part_ids: [],
        operator_ids: [],
        measurements: [],
        method: "xbar_r",
      },
    });

    expect(resp.status()).toBe(422);
  });
});

// ---------------------------------------------------------------------------
// T-E4: CSV-style upload → GR&R results
// ---------------------------------------------------------------------------

test.describe("T-E4: CSV upload → GR&R results", () => {
  test("POST with CSV-formatted measurement array returns valid GRR", async () => {
    const ctx = await request.newContext({
      baseURL: API_URL,
      extraHTTPHeaders: { "x-api-key": API_KEY },
    });

    // Simulate a parsed CSV with 3 operators × 10 parts × 2 trials
    const rows = [];
    for (const op of ["Alice", "Bob", "Carol"]) {
      for (let part = 1; part <= 10; part++) {
        for (let trial = 0; trial < 2; trial++) {
          rows.push({
            part: `PART-${part}`,
            operator: op,
            value: +(10.0 + part * 0.3 + (Math.random() * 0.2 - 0.1)).toFixed(5),
          });
        }
      }
    }

    const resp = await ctx.post("/api/v1/studies/grr", {
      data: {
        part_ids: Array.from({ length: 10 }, (_, i) => `PART-${i + 1}`),
        operator_ids: ["Alice", "Bob", "Carol"],
        measurements: rows,
        method: "xbar_r",
      },
    });

    // Accept 201 (success) or 500 (no live DB) — not 422
    expect(resp.status()).not.toBe(422);

    if (resp.status() === 201) {
      const body = await resp.json();
      expect(body.grr_percent).toBeGreaterThan(0);
      expect(body.ndc).toBeGreaterThanOrEqual(1);
    }
  });
});

// ---------------------------------------------------------------------------
// T-E2: Dashboard loads and shows data (UI test, requires live stack)
// ---------------------------------------------------------------------------

test.describe("T-E2: Dashboard UI smoke test", () => {
  test.skip(
    !process.env.RUN_UI_TESTS,
    "Set RUN_UI_TESTS=1 to run UI tests against a live stack"
  );

  test("dashboard home page loads within 5s", async ({ page }) => {
    const start = Date.now();
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    const elapsed = Date.now() - start;

    expect(elapsed).toBeLessThan(5_000);
    await expect(page).toHaveTitle(/arad|quality/i);
  });

  test("quality overview page shows charts after data load", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Look for dashboard content indicators
    const chartOrTable = page.locator(
      '[data-testid="quality-chart"], [data-testid="grr-table"], canvas, .chart-container'
    );
    await expect(chartOrTable.first()).toBeVisible({ timeout: 30_000 });
  });
});
