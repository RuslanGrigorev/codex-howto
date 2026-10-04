/* landing.js - progress tracking, terminal, scroll effects for Codex CLI course.
   Vanilla JS, no runtime external dependencies. Fully usable offline and under file://.
   Tracks progress via CodexProgress (PRG-001 - PRG-005).
*/
(function () {
  "use strict";

  var root = document.documentElement;
  root.classList.remove("no-js");
  root.classList.add("js");

  var lang = root.getAttribute("lang") || "ru";
  var isRu = lang === "ru";

  var STATUS_LABEL = {
    "not-started": isRu ? "Не начато" : "Not started",
    "in-progress": isRu ? "В процессе" : "In progress",
    "done": isRu ? "Завершено" : "Done"
  };

  var reducedMotion = false;
  try {
    reducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;
  } catch (e) {
    /* matchMedia unavailable - treat as no preference */
  }

  /* ================= Theme (shared with the docs pages) ================= */
  var THEME_KEY = "codex-course-theme";
  var themeToggle = document.getElementById("theme-toggle");

  function currentTheme() {
    return root.classList.contains("dark") ? "dark" : "light";
  }

  function paintThemeToggle() {
    if (!themeToggle) return;
    themeToggle.setAttribute(
      "aria-label",
      currentTheme() === "dark"
        ? (isRu ? "Переключить на светлую тему" : "Switch to light theme")
        : (isRu ? "Переключить на тёмную тему" : "Switch to dark theme")
    );
  }

  function savedTheme() {
    try {
      return window.localStorage.getItem(THEME_KEY) || window.localStorage.getItem("claude-howto-theme");
    } catch (e) {
      return null;
    }
  }

  function applyTheme(theme, animate) {
    if (animate && !reducedMotion) {
      root.classList.add("theme-anim");
      window.setTimeout(function () {
        root.classList.remove("theme-anim");
      }, 350);
    }
    root.classList.toggle("dark", theme === "dark");
    paintThemeToggle();
  }

  if (themeToggle) {
    themeToggle.addEventListener("click", function () {
      var next = currentTheme() === "dark" ? "light" : "dark";
      applyTheme(next, true);
      try {
        window.localStorage.setItem(THEME_KEY, next);
      } catch (e) {}
    });
  }
  paintThemeToggle();

  /* Follow prefers-color-scheme changes live if no explicit saved choice */
  try {
    var themeMq = window.matchMedia("(prefers-color-scheme: dark)");
    var followOsTheme = function (e) {
      if (!savedTheme()) applyTheme(e.matches ? "dark" : "light", true);
    };
    if (themeMq.addEventListener) {
      themeMq.addEventListener("change", followOsTheme);
    } else if (themeMq.addListener) {
      themeMq.addListener(followOsTheme);
    }
  } catch (e) {}

  /* ================= Progress Store (via CodexProgress) ================= */

  var lessonEls = Array.prototype.slice.call(
    document.querySelectorAll(".lesson[data-lesson]")
  );
  var stationEls = Array.prototype.slice.call(
    document.querySelectorAll(".station[data-module]")
  );
  var knownIds = {};
  lessonEls.forEach(function (el) {
    knownIds[el.getAttribute("data-lesson")] = true;
  });

  function getLessonRecord(id) {
    if (!window.CodexProgress) return null;
    var state = window.CodexProgress.getState();
    return (state && state.lessons && state.lessons[id]) || null;
  }

  function lessonStatus(id) {
    var rec = getLessonRecord(id);
    if (!rec) return "not-started";
    var isRead = !!rec.read;
    var quizPassed = rec.quiz ? !!rec.quiz.passed : null;
    var exercisePassed = rec.exercise ? !!rec.exercise.passed : null;

    if (quizPassed === false || exercisePassed === false) {
      return "in-progress";
    }
    if (isRead && (quizPassed === null || quizPassed) && (exercisePassed === null || exercisePassed)) {
      return "done";
    }
    if (isRead || quizPassed !== null || exercisePassed !== null) {
      return "in-progress";
    }
    return "not-started";
  }

  function toggleRead(id) {
    if (window.CodexProgress && window.CodexProgress.toggleRead) {
      window.CodexProgress.toggleRead(id);
    }
  }

  function markStarted(lessonEl) {
    if (!lessonEl) return;
    var id = lessonEl.getAttribute("data-lesson");
    var rec = getLessonRecord(id);
    if (!rec && window.CodexProgress) {
      window.CodexProgress.markRead(id);
      paintAll();
    }
  }

  function bindMarkStarted(el, getLessonEl) {
    el.addEventListener("click", function () {
      markStarted(getLessonEl());
    });
    el.addEventListener("auxclick", function (e) {
      if (e.button === 1) markStarted(getLessonEl());
    });
  }

  /* ================= Painting ================= */

  function paintLesson(el) {
    var id = el.getAttribute("data-lesson");
    var status = lessonStatus(id);
    var rec = getLessonRecord(id);
    el.setAttribute("data-status", status);
    var check = el.querySelector(".check");
    if (check) {
      var isRead = rec ? !!rec.read : false;
      check.setAttribute(
        "aria-checked",
        isRead ? "true" : (status === "in-progress" ? "mixed" : "false")
      );
      check.setAttribute("title", isRead
        ? (isRu ? "Отмечено как прочитанное" : "Marked as read")
        : (isRu ? "Отметить как прочитанное" : "Mark as read")
      );
    }
    var label = el.querySelector("[data-lstatus]");
    if (label) {
      var parts = [];
      if (rec) {
        if (rec.read) parts.push(isRu ? "Прочитано" : "Read");
        if (rec.quiz && rec.quiz.passed) parts.push(isRu ? "Тест пройден" : "Quiz passed");
        if (rec.exercise && rec.exercise.passed) parts.push(isRu ? "Практика сдана" : "Exercise passed");
        if (rec.codex_run && rec.codex_run.passed) parts.push("Codex");
      }
      if (parts.length > 0) {
        label.textContent = parts.join(" · ");
      } else {
        label.textContent = STATUS_LABEL[status];
      }
    }
  }

  function paintStation(station) {
    var rows = station.querySelectorAll(".lesson[data-lesson]");
    var total = rows.length;
    var done = 0;
    var started = 0;
    for (var i = 0; i < total; i++) {
      var s = lessonStatus(rows[i].getAttribute("data-lesson"));
      if (s === "done") {
        done++;
        started++;
      } else if (s === "in-progress") {
        started++;
      }
    }
    var status =
      total > 0 && done === total
        ? "done"
        : started > 0
          ? "in-progress"
          : "not-started";
    station.setAttribute("data-status", status);
    var pill = station.querySelector("[data-pill]");
    if (pill) {
      pill.textContent = total === 0 ? (isRu ? "Скоро" : "Coming soon") : STATUS_LABEL[status];
    }
    var count = station.querySelector("[data-count]");
    if (count) count.textContent = done + "/" + total;
    var bar = station.querySelector("[data-bar]");
    if (bar) bar.style.width = total ? (done / total) * 100 + "%" : "0%";
  }

  var RING_R = 52;
  var RING_C = 2 * Math.PI * RING_R;
  var continueTarget = null;

  function paintOverall() {
    var total = lessonEls.length;
    var done = 0;
    var inProgress = 0;
    var continueEl = null;
    var continueTime = -1;
    var firstTodo = null;

    lessonEls.forEach(function (el) {
      var id = el.getAttribute("data-lesson");
      var s = lessonStatus(id);
      var rec = getLessonRecord(id);
      if (s === "done") {
        done++;
      } else if (s === "in-progress") {
        inProgress++;
        var t = 0;
        if (rec && rec.quiz && rec.quiz.completed_at) {
          t = new Date(rec.quiz.completed_at).getTime();
        } else if (rec && rec.exercise && rec.exercise.completed_at) {
          t = new Date(rec.exercise.completed_at).getTime();
        }
        if (t > continueTime) {
          continueTime = t;
          continueEl = el;
        }
      } else if (!firstTodo) {
        firstTodo = el;
      }
    });

    var pct = total ? Math.round((done / total) * 100) : 0;
    var ring = document.getElementById("ring-fg");
    if (ring) {
      ring.style.strokeDashoffset = String(RING_C * (1 - done / (total || 1)));
    }
    var pctEl = document.getElementById("ring-pct");
    if (pctEl) pctEl.textContent = pct + "%";
    var doneEl = document.getElementById("c-done");
    if (doneEl) doneEl.textContent = String(done);
    var progEl = document.getElementById("c-prog");
    if (progEl) progEl.textContent = String(inProgress);
    var todoEl = document.getElementById("c-todo");
    if (todoEl) todoEl.textContent = String(Math.max(0, total - done - inProgress));

    var continueBtn = document.getElementById("continue-btn");
    var allDone = document.getElementById("all-done");
    var target = continueEl || firstTodo;
    continueTarget = target;
    if (continueBtn && allDone) {
      if (target && done < total) {
        var link = target.querySelector(".lesson-link");
        var title = link ? link.textContent.trim() : "";
        var station = target.closest(".station");
        var modTitle = "";
        if (station) {
          var t = station.querySelector(".station-title");
          modTitle = t ? t.textContent.trim() : "";
        }
        var verb = done + inProgress === 0
          ? (isRu ? "Начать" : "Start")
          : (isRu ? "Продолжить" : "Continue");
        continueBtn.hidden = false;
        allDone.hidden = true;
        if (link) continueBtn.setAttribute("href", link.getAttribute("href"));
        continueBtn.textContent =
          verb + ": " + (modTitle ? modTitle + " · " : "") + title;
      } else {
        continueBtn.hidden = true;
        allDone.hidden = false;
      }
    }
    paintTrack();
  }

  function paintTrack() {
    var fill = document.getElementById("track-fill");
    var subway = document.getElementById("subway");
    if (!fill || !subway) return;

    var rect = subway.getBoundingClientRect();
    if (rect.height <= 0) return;

    var statusP = 0;
    stationEls.forEach(function (st) {
      if (st.getAttribute("data-status") === "not-started") return;
      var node = st.querySelector(".node") || st;
      var y = node.getBoundingClientRect().top - rect.top;
      if (y > 0) statusP = Math.max(statusP, Math.min(1, y / rect.height));
    });

    var scrollP = Math.min(
      1,
      Math.max(0, (window.innerHeight * 0.8 - rect.top) / rect.height)
    );

    fill.style.height = Math.max(scrollP, statusP) * 100 + "%";
  }

  function checkStorageHealth() {
    if (window.CodexProgress && !window.CodexProgress.isStorageAvailable()) {
      var sw = document.getElementById("storage-warning");
      if (sw) sw.hidden = false;
    }
  }

  function paintAll() {
    lessonEls.forEach(paintLesson);
    stationEls.forEach(paintStation);
    paintOverall();
    checkStorageHealth();
  }

  /* ================= Events ================= */

  lessonEls.forEach(function (el) {
    var id = el.getAttribute("data-lesson");

    var check = el.querySelector(".check");
    if (check) {
      check.addEventListener("click", function () {
        toggleRead(id);
        paintAll();
      });
    }

    var link = el.querySelector(".lesson-link");
    if (link) {
      bindMarkStarted(link, function () {
        return el;
      });
    }
  });

  function setExpanded(station, expanded) {
    var toggle = station.querySelector(".station-toggle");
    var list = station.querySelector(".lessons");
    if (!toggle || !list) return;
    toggle.setAttribute("aria-expanded", String(expanded));
    list.hidden = !expanded;
  }

  stationEls.forEach(function (station) {
    var toggle = station.querySelector(".station-toggle");
    if (!toggle) return;

    setExpanded(station, false);

    toggle.addEventListener("click", function () {
      var open = toggle.getAttribute("aria-expanded") === "true";
      setExpanded(station, !open);
    });

    var titleLink = station.querySelector(".station-title a");
    if (titleLink) {
      bindMarkStarted(titleLink, function () {
        return station.querySelector(".lesson[data-lesson]");
      });
    }
  });

  var continueBtnEl = document.getElementById("continue-btn");
  if (continueBtnEl) {
    bindMarkStarted(continueBtnEl, function () {
      return continueTarget;
    });
  }

  /* Export progress JSON */
  var exportBtn = document.getElementById("export-btn");
  if (exportBtn) {
    exportBtn.addEventListener("click", function () {
      try {
        var jsonStr = window.CodexProgress ? window.CodexProgress.exportJSON() : "{}";
        var blob = new Blob([jsonStr], { type: "application/json;charset=utf-8" });
        var url = URL.createObjectURL(blob);
        var a = document.createElement("a");
        a.href = url;
        a.download = "codex-cli-course-progress.json";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      } catch (err) {
        alert((isRu ? "Не удалось экспортировать: " : "Export failed: ") + err.message);
      }
    });
  }

  /* Import progress JSON */
  var importBtn = document.getElementById("import-btn");
  var importFile = document.getElementById("import-file");
  if (importBtn && importFile) {
    importBtn.addEventListener("click", function () {
      importFile.value = "";
      importFile.click();
    });
    importFile.addEventListener("change", function (e) {
      var file = e.target.files && e.target.files[0];
      if (!file) return;
      if (file.size > 1024 * 1024) {
        alert(isRu ? "Файл превышает допустимый размер (1 МиБ)." : "File exceeds maximum size (1 MiB).");
        return;
      }
      var reader = new FileReader();
      reader.onload = function (evt) {
        try {
          var content = evt.target.result;
          window.CodexProgress.importJSON(content);
          paintAll();
          alert(isRu ? "Прогресс успешно импортирован!" : "Progress successfully imported!");
        } catch (err) {
          alert((isRu ? "Ошибка импорта: " : "Import error: ") + err.message);
        }
      };
      reader.onerror = function () {
        alert(isRu ? "Ошибка при чтении файла." : "Error reading file.");
      };
      reader.readAsText(file, "UTF-8");
    });
  }

  /* Reset progress */
  var resetBtn = document.getElementById("reset-btn");
  if (resetBtn) {
    resetBtn.addEventListener("click", function () {
      var confirmMsg = isRu
        ? "Сбросить весь сохраненный прогресс по курсу Codex CLI? Это действие невозможно отменить."
        : "Reset all progress for the Codex CLI course? This cannot be undone.";
      if (!window.confirm(confirmMsg)) {
        return;
      }
      if (window.CodexProgress) {
        window.CodexProgress.reset();
      }
      paintAll();
    });
  }

  /* Storage sync */
  window.addEventListener("storage", function (e) {
    if (e.key === THEME_KEY && e.newValue) {
      applyTheme(e.newValue, true);
      return;
    }
    if (e.key === "codex-cli-course-ru.progress.v1") {
      paintAll();
    }
  });

  window.addEventListener("pageshow", function () {
    paintAll();
  });

  var scrollTicking = false;
  window.addEventListener(
    "scroll",
    function () {
      if (scrollTicking) return;
      scrollTicking = true;
      window.requestAnimationFrame(function () {
        paintTrack();
        scrollTicking = false;
      });
    },
    { passive: true }
  );
  window.addEventListener("resize", paintTrack);

  /* ================= Terminal typing animation ================= */
  function runTerminal() {
    var term = document.getElementById("terminal");
    if (!term || reducedMotion) return;

    var lines = Array.prototype.slice.call(term.querySelectorAll(".t-line"));
    var typed = lines.map(function (line) {
      var tt = line.querySelector(".t-tt");
      var text = tt ? tt.textContent : "";
      return { line: line, tt: tt, text: text, isCmd: !!tt };
    });

    function reset() {
      typed.forEach(function (item) {
        item.line.style.visibility = "hidden";
        item.line.classList.remove("t-caret");
        if (item.tt) {
          item.tt.textContent = "";
          item.tt.classList.remove("t-typing");
        }
      });
    }

    var delays = [];
    function later(fn, ms) {
      delays.push(window.setTimeout(fn, ms));
    }

    function play() {
      reset();
      var t = 350;
      typed.forEach(function (item) {
        if (item.isCmd) {
          var text = item.text;
          var start = t;
          for (var i = 0; i <= text.length; i++) {
            (function (it, ch) {
              later(function () {
                it.line.style.visibility = "visible";
                it.tt.textContent = text.slice(0, ch);
                it.tt.classList.add("t-typing");
              }, start + ch * 38);
            })(item, i);
          }
          t += text.length * 38 + 420;
          (function (it) {
            later(function () {
              it.tt.classList.remove("t-typing");
            }, t - 380);
          })(item);
        } else {
          (function (it, at) {
            later(function () {
              it.line.style.visibility = "visible";
            }, at);
          })(item, t);
          t += 260;
        }
      });

      var last = typed[typed.length - 1];
      if (last && last.tt) {
        later(function () {
          last.line.classList.add("t-caret");
        }, t);
      }
      later(play, t + 6500);
    }
    play();
  }

  /* ================= Reveal on scroll ================= */
  var revealEls = Array.prototype.slice.call(
    document.querySelectorAll(".reveal")
  );
  if ("IntersectionObserver" in window && !reducedMotion) {
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("in");
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -6% 0px" }
    );
    revealEls.forEach(function (el) {
      io.observe(el);
    });
  } else {
    revealEls.forEach(function (el) {
      el.classList.add("in");
    });
  }

  /* ================= Mobile nav ================= */
  var navToggle = document.getElementById("nav-toggle");
  var navMenu = document.getElementById("nav-menu");
  if (navToggle && navMenu) {
    navToggle.addEventListener("click", function () {
      var open = navMenu.classList.toggle("open");
      navToggle.setAttribute("aria-expanded", String(open));
    });
    navMenu.addEventListener("click", function (e) {
      if (e.target.closest("a")) {
        navMenu.classList.remove("open");
        navToggle.setAttribute("aria-expanded", "false");
      }
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && navMenu.classList.contains("open")) {
        navMenu.classList.remove("open");
        navToggle.setAttribute("aria-expanded", "false");
        navToggle.focus();
      }
    });
    var topEl = document.getElementById("top");
    if (topEl) topEl.classList.add("nav-enhanced");
  }

  /* ================= Copy buttons ================= */
  var copyStatus = document.getElementById("copy-status");
  var copyAttempt = 0;

  function legacyCopy(text) {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    try {
      ta.select();
      return document.execCommand("copy");
    } catch (e) {
      return false;
    } finally {
      document.body.removeChild(ta);
    }
  }

  Array.prototype.slice
    .call(document.querySelectorAll("[data-copy]"))
    .forEach(function (btn) {
      var label = btn.querySelector(".copy-label");
      var originalLabel = label ? label.textContent : "";
      var feedbackTimer = null;
      btn.addEventListener("click", function () {
        var text = btn.getAttribute("data-copy") || "";
        var attempt = ++copyAttempt;
        if (feedbackTimer !== null) window.clearTimeout(feedbackTimer);
        feedbackTimer = null;
        if (label) label.textContent = originalLabel;
        btn.classList.remove("copied");
        if (copyStatus) copyStatus.textContent = "";
        function feedback(copied) {
          if (attempt !== copyAttempt) return;
          btn.classList.toggle("copied", copied);
          if (copyStatus) {
            copyStatus.textContent = copied
              ? (isRu ? "Скопировано в буфер" : "Copied to clipboard")
              : (isRu ? "Не удалось скопировать" : "Unable to copy to clipboard");
          }
          if (label) {
            label.textContent = copied
              ? (isRu ? "Скопировано" : "Copied")
              : (isRu ? "Ошибка" : "Copy failed");
            feedbackTimer = window.setTimeout(function () {
              label.textContent = originalLabel;
              btn.classList.remove("copied");
              feedbackTimer = null;
            }, 1400);
          }
        }
        if (navigator.clipboard && navigator.clipboard.writeText) {
          try {
            navigator.clipboard.writeText(text).then(
              function () { feedback(true); },
              function () {
                if (attempt === copyAttempt) feedback(legacyCopy(text));
              }
            );
          } catch (e) {
            feedback(legacyCopy(text));
          }
        } else {
          feedback(legacyCopy(text));
        }
      });
    });

  /* ================= Init ================= */
  paintAll();
  stationEls.forEach(function (station) {
    if (station.getAttribute("data-status") === "in-progress") {
      setExpanded(station, true);
    }
  });
  paintTrack();
  runTerminal();
})();
