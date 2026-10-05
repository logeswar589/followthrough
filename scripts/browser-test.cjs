// Uses an isolated test server at :8001 and synthetic microphone input only.
// Install Playwright separately or set NODE_PATH to its existing installation.
const { chromium } = require("playwright");
const assert = require("node:assert/strict");
const path = require("node:path");
const fs = require("node:fs");

(async () => {
  const browser = await chromium.launch({
    channel: "msedge",
    headless: true,
    args: [
      "--use-fake-ui-for-media-stream",
      "--use-fake-device-for-media-stream",
      "--use-file-for-fake-audio-capture=" +
        path.resolve("artifacts/synthetic-demo.wav") +
        "%noloop",
    ],
  });
  try {
    const context = await browser.newContext({
      viewport: { width: 1440, height: 1000 },
      permissions: ["microphone"],
      acceptDownloads: true,
    });
    const page = await context.newPage();
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.goto("http://127.0.0.1:8001");
    await page
      .getByRole("button", { name: /UI test fixture.*next steps/ })
      .click();
    await page
      .getByRole("heading", { name: "Prototype meetup", exact: true })
      .waitFor();
    const downloadPromise = page.waitForEvent("download");
    await page
      .getByRole("button", { name: "Download .ics ↗", exact: true })
      .click();
    const download = await downloadPromise;
    await download.saveAs("artifacts/browser-calendar.ics");
    const ics = fs.readFileSync("artifacts/browser-calendar.ics", "utf8");
    assert(ics.includes("DTSTART:20261006T133000Z"));
    assert(ics.includes("TRIGGER:-PT30M"));
    console.log("Browser calendar download passed.");
    await page
      .getByRole("button", { name: "03   Recap", exact: false })
      .click();
    await page
      .locator("#recap")
      .fill("UI FIXTURE: Reviewed recap, nothing sent.");
    await page.getByRole("button", { name: "Save edits", exact: true }).click();
    await page.getByText("Recap saved.", { exact: true }).waitFor();
    await page.reload();
    await page
      .getByRole("button", { name: /UI test fixture.*next steps/ })
      .click();
    await page
      .getByRole("button", { name: "03   Recap", exact: false })
      .click();
    assert.equal(
      await page.locator("#recap").inputValue(),
      "UI FIXTURE: Reviewed recap, nothing sent.",
    );
    console.log("Browser recap edit and reload persistence passed.");
    await page
      .getByRole("checkbox", {
        name: "Everyone being recorded knows and agrees.",
      })
      .check();
    await page
      .getByRole("button", { name: "Start recording", exact: false })
      .click();
    await page
      .getByRole("button", { name: "Stop recording", exact: false })
      .waitFor();
    console.log("Synthetic microphone recording started.");
    await page.waitForTimeout(31000); // Real audio duration: must capture the full synthetic fixture.
    await page
      .getByRole("button", { name: "Stop recording", exact: false })
      .click();
    await page.waitForFunction(
      () => document.querySelector("#transcript")?.value.includes("800"),
      { timeout: 60000 },
    );
    const transcript = await page.locator("#transcript").inputValue();
    assert(/may\s*be/i.test(transcript));
    assert(/wait/i.test(transcript));
    await page.screenshot({
      path: "artifacts/browser-recording.jpg",
      fullPage: true,
    });
    console.log(
      "Record -> stop -> real Whisper transcription passed:",
      transcript,
    );
    await page.setViewportSize({ width: 390, height: 844 });
    assert(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    );
    await page.screenshot({
      path: "artifacts/browser-mobile.jpg",
      fullPage: true,
    });
    assert.deepEqual(errors, []);
    console.log("Mobile overflow and browser error checks passed.");
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
