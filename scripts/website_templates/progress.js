/* progress.js - Единый модуль управления прогрессом курса Codex CLI.
   Соответствует требованиям PRG-001, PRG-002, PRG-003, PRG-005.
   Работает полностью офлайн (file://), защищен от XSS, валидирует импорт атомарно.
*/
(function (global) {
  "use strict";

  var STORAGE_KEY = "codex-cli-course-ru.progress.v1";
  var SCHEMA_VERSION = 1;
  var COURSE_ID = "codex-cli-course-ru";
  var MAX_IMPORT_SIZE = 1024 * 1024; // 1 MiB

  var state = {
    schema_version: SCHEMA_VERSION,
    course_id: COURSE_ID,
    course_version: "0.1.0",
    lessons: {},
    unmapped: {}
  };

  var isStorageAvailable = true;

  function initStorage() {
    try {
      var testKey = "__codex_storage_test__";
      window.localStorage.setItem(testKey, "1");
      window.localStorage.removeItem(testKey);
    } catch (e) {
      isStorageAvailable = false;
      console.warn("localStorage недоступен. Прогресс хранится только в оперативной памяти страницы.");
    }
  }

  function loadProgress() {
    if (!isStorageAvailable) return state;
    try {
      var raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return state;
      var data = JSON.parse(raw);
      if (validateProgressData(data)) {
        state = data;
      }
    } catch (e) {
      console.error("Ошибка при чтении прогресса:", e);
    }
    return state;
  }

  function saveProgress() {
    if (!isStorageAvailable) return false;
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      return true;
    } catch (e) {
      console.warn("Не удалось сохранить в localStorage:", e);
      return false;
    }
  }

  function validateProgressData(data) {
    if (!data || typeof data !== "object") return false;
    if (data.schema_version !== SCHEMA_VERSION) return false;
    if (data.course_id !== COURSE_ID) return false;
    if (!data.lessons || typeof data.lessons !== "object") return false;
    return true;
  }

  function markLessonRead(lessonId, revision) {
    if (!state.lessons[lessonId]) {
      state.lessons[lessonId] = {
        revision: revision || 1,
        read: false,
        quiz: null,
        exercise: null,
        codex_run: null,
        needs_review: false
      };
    }
    state.lessons[lessonId].read = true;
    saveProgress();
    return state.lessons[lessonId];
  }

  function recordQuizResult(lessonId, revision, score, passed, details) {
    if (!state.lessons[lessonId]) {
      markLessonRead(lessonId, revision);
    }
    state.lessons[lessonId].quiz = {
      score: score,
      passed: passed,
      completed_at: new Date().toISOString(),
      details: details || {}
    };
    saveProgress();
    return state.lessons[lessonId];
  }

  function recordExerciseResult(lessonId, revision, passed, executionHash) {
    if (!state.lessons[lessonId]) {
      markLessonRead(lessonId, revision);
    }
    state.lessons[lessonId].exercise = {
      passed: passed,
      execution_hash: executionHash || "",
      completed_at: new Date().toISOString()
    };
    saveProgress();
    return state.lessons[lessonId];
  }

  function exportProgressJSON() {
    return JSON.stringify(state, null, 2);
  }

  function importProgressJSON(jsonString) {
    if (jsonString.length > MAX_IMPORT_SIZE) {
      throw new Error("Файл превышает допустимый размер (1 МиБ).");
    }
    var parsed;
    try {
      parsed = JSON.parse(jsonString);
    } catch (e) {
      throw new Error("Некорректный формат JSON.");
    }
    if (!validateProgressData(parsed)) {
      throw new Error("Несовместимая версия схемы или неверный идентификатор курса (требуется codex-cli-course-ru).");
    }
    // Атомарно заменяем текущее состояние
    state = parsed;
    saveProgress();
    return state;
  }

  function resetProgress() {
    state = {
      schema_version: SCHEMA_VERSION,
      course_id: COURSE_ID,
      course_version: "0.1.0",
      lessons: {},
      unmapped: {}
    };
    if (isStorageAvailable) {
      try {
        window.localStorage.removeItem(STORAGE_KEY);
      } catch (e) {}
    }
    return state;
  }

  // Экспорт в глобальный контекст
  initStorage();
  loadProgress();

  global.CodexProgress = {
    getState: function () { return state; },
    isStorageAvailable: function () { return isStorageAvailable; },
    markRead: markLessonRead,
    recordQuiz: recordQuizResult,
    recordExercise: recordExerciseResult,
    exportJSON: exportProgressJSON,
    importJSON: importProgressJSON,
    reset: resetProgress
  };

})(typeof window !== "undefined" ? window : this);
