(() => {
  const section = document.querySelector(".scroll-story");
  if (!section) return;
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  const panels = [...section.querySelectorAll("[data-story-panel]")];
  const headings = [
    "To out of your head.",
    "To something clearer.",
    "To actually getting done.",
  ];
  const descriptions = [
    "Start with the messy version. A voice note is enough.",
    "The important details stay. The ramble becomes a note you can review.",
    "Clear tasks, one by one. The uncertain stuff stays open until you decide.",
  ];
  let queued = false;
  function update() {
    queued = false;
    const rect = section.getBoundingClientRect();
    const progress = Math.min(
      1,
      Math.max(0, -rect.top / Math.max(1, rect.height - innerHeight)),
    );
    const stage = progress < 0.3 ? 0 : progress < 0.6 ? 1 : 2;
    section.dataset.stage = stage;
    document.querySelector("#storyProgress").style.transform =
      `scaleX(${progress})`;
    document.querySelector("#storyHeadline").textContent = headings[stage];
    document.querySelector("#storyDescription").textContent =
      descriptions[stage];
    panels.forEach((panel, i) => {
      panel.setAttribute("aria-hidden", String(i !== stage));
      let visibility;
      if (i === 0)
        visibility = 1 - Math.min(1, Math.max(0, (progress - 0.24) / 0.12));
      if (i === 1)
        visibility =
          Math.min(1, Math.max(0, (progress - 0.24) / 0.12)) *
          (1 - Math.min(1, Math.max(0, (progress - 0.54) / 0.12)));
      if (i === 2)
        visibility = Math.min(1, Math.max(0, (progress - 0.54) / 0.12));
      panel.style.opacity = reduced.matches ? Number(i === stage) : visibility;
      panel.style.transform = reduced.matches
        ? "none"
        : `translateY(${(1 - visibility) * 22}px)`;
      panel.style.visibility = visibility < 0.01 ? "hidden" : "visible";
    });
    section
      .querySelectorAll("[data-story-label]")
      .forEach((label, i) => label.classList.toggle("active", i === stage));
    const done = progress > 0.88 ? 2 : progress > 0.73 ? 1 : 0;
    section.querySelectorAll("[data-story-task]").forEach((task, i) => {
      task.classList.toggle("checked", i < done);
      task.querySelector(".story-box").textContent = i < done ? "✓" : "";
    });
    document.querySelector("#storyDoneCount").textContent = `${done} / 2`;
    document
      .querySelector("#storyFinish")
      .classList.toggle("visible", done === 2);
    document.querySelector("#storyPaper").style.transform = reduced.matches
      ? "none"
      : `rotate(${(-3 + progress * 3).toFixed(2)}deg)`;
  }
  function schedule() {
    if (!queued) {
      queued = true;
      requestAnimationFrame(update);
    }
  }
  addEventListener("scroll", schedule, { passive: true });
  addEventListener("resize", schedule);
  reduced.addEventListener("change", schedule);
  update();
})();
