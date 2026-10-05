(function(){"use strict";
function refresh(){var p=window.CodexProgress,done=0,total=0;document.querySelectorAll('[data-lesson]').forEach(function(el){var status=p.lessonStatus(el.dataset.lesson);var badge=el.querySelector('.lesson-badge');if(badge)badge.textContent=status.label;total++;if(status.complete)done++;});var x=document.getElementById('overall-progress');if(x)x.textContent='Завершено: '+done+' из '+total+'. Чтение, проверка знаний, практика и запуск Codex учитываются отдельно.';}
window.addEventListener('progress-changed',refresh);refresh();
})();
